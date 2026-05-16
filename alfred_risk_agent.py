#!/usr/bin/env python3
"""
Alfred — Risk Manager Agent (NOT Orchestrator)
Runs independently at 6:30 PM HKT on trading days.
Checks all MT5 accounts, calculates risk limits, posts risk assessment.

Alfred has HARD VETO power:
- If any account DD > 8% → VETO
- If daily loss limit exceeded → VETO
- If prop firm rule violation imminent → VETO
- If account disconnected or API error → VETO (safety first)

The veto is communicated via the shared repo and Discord.
Merlin (orchestrator) MUST respect the veto.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────
REPO_DIR = Path(os.path.expanduser("~/.hermes/trading-war-room"))
SIGNALS_DIR = REPO_DIR / "signals"

# Risk thresholds
MAX_DAILY_LOSS_PCT = 2.0    # FTMO daily limit
MAX_TOTAL_DD_PCT = 10.0     # FTMO max DD
VETO_DD_THRESHOLD = 8.0     # Veto if any account above this
VETO_CONSECUTIVE_LOSSES = 5  # Veto after 5 consecutive losses

# US Market Holidays (2026)
US_HOLIDAYS = [
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
    "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07",
    "2026-11-26", "2026-12-25",
]


def is_trading_day() -> bool:
    now_hk = datetime.now(timezone(timedelta(hours=8)))
    if now_hk.weekday() >= 5:
        return False
    if now_hk.strftime("%Y-%m-%d") in US_HOLIDAYS:
        return False
    return True


def git_pull():
    """Pull latest from shared repo."""
    os.chdir(REPO_DIR)
    subprocess.run(["git", "pull", "--rebase"], capture_output=True)


def git_push(message: str):
    """Commit and push changes."""
    os.chdir(REPO_DIR)
    subprocess.run(["git", "add", "."], capture_output=True)
    subprocess.run(["git", "commit", "-m", message], capture_output=True)
    subprocess.run(["git", "push"], capture_output=True)


def check_mt5_accounts() -> dict:
    """
    Check all MT5 account balances, equity, and drawdown.
    Uses the existing MT5 balance check infrastructure.

    Returns:
        dict of account_name -> {balance, equity, dd_pct, daily_pl, status}
    """
    accounts = {}

    # Try the existing MT5 balance check script
    try:
        result = subprocess.run(
            ["/mnt/c/Python312/python.exe",
             "/home/ychen/.hermes/skills/trading/mt5-balance-check/check_balances.py"],
            capture_output=True, text=True, timeout=120
        )
        if result.stdout:
            accounts = json.loads(result.stdout)
    except Exception as e:
        print(f"  ⚠️ MT5 check failed: {e}")
        # If the check fails, return a veto — safety first
        return {
            "ERROR": {
                "balance": 0,
                "equity": 0,
                "dd_pct": 0,
                "status": "error",
                "error": str(e),
            }
        }

    # If no accounts found, also return error
    if not accounts:
        return {
            "ERROR": {
                "balance": 0,
                "equity": 0,
                "dd_pct": 0,
                "status": "no_accounts",
                "error": "No accounts returned from MT5 check",
            }
        }

    return accounts


def load_trade_log() -> list:
    """Load the trade log to check for consecutive losses."""
    trade_log_file = REPO_DIR / "trade-log.json"
    if trade_log_file.exists():
        with open(trade_log_file) as f:
            return json.load(f)
    return []


def check_consecutive_losses(trade_log: list) -> int:
    """Count consecutive losses from the trade log."""
    consecutive = 0
    for trade in reversed(trade_log):
        if trade.get("result") == "loss":
            consecutive += 1
        else:
            break
    return consecutive


def calculate_risk_assessment(accounts: dict, trade_log: list) -> dict:
    """
    Calculate comprehensive risk assessment.

    Returns dict with:
    - go_no_go: GO / NO_GO / VETO
    - veto: bool
    - veto_reason: str (if vetoed)
    - accounts: dict of account status
    - factors: list of risk factors
    - recommended_lot_size: float
    - max_daily_loss_pct: float
    """
    assessment = {
        "timestamp": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "go_no_go": "GO",
        "veto": False,
        "veto_reason": "",
        "accounts": {},
        "factors": [],
        "recommended_lot_size": 1.0,  # Default multiplier
        "max_daily_loss_pct": MAX_DAILY_LOSS_PCT,
        "consecutive_losses": 0,
    }

    # Check each account
    veto_triggered = False
    veto_reasons = []

    for account_name, data in accounts.items():
        if data.get("status") == "error":
            veto_triggered = True
            veto_reasons.append(f"⛔ {account_name}: MT5 connection error — cannot verify risk")
            assessment["accounts"][account_name] = {
                "status": "error",
                "error": data.get("error", "Unknown error"),
            }
            continue

        balance = data.get("balance", 0)
        equity = data.get("equity", balance)
        dd_pct = ((balance - equity) / balance * 100) if balance > 0 else 0
        daily_pl = data.get("daily_pl", 0)

        account_status = {
            "balance": balance,
            "equity": equity,
            "dd_pct": round(dd_pct, 2),
            "daily_pl": daily_pl,
            "status": "ok",
        }

        # Check DD threshold
        if dd_pct > MAX_TOTAL_DD_PCT:
            veto_triggered = True
            veto_reasons.append(f"⛔ {account_name}: DD {dd_pct:.1f}% EXCEEDS max {MAX_TOTAL_DD_PCT}%")
        elif dd_pct > VETO_DD_THRESHOLD:
            veto_triggered = True
            veto_reasons.append(f"⛔ {account_name}: DD {dd_pct:.1f}% above veto threshold {VETO_DD_THRESHOLD}%")
        elif dd_pct > 5:
            assessment["factors"].append(f"⚠️ {account_name}: DD at {dd_pct:.1f}% — approaching caution zone")
            assessment["recommended_lot_size"] *= 0.5  # Halve size
        else:
            assessment["factors"].append(f"✅ {account_name}: DD {dd_pct:.1f}% — within limits")

        # Check daily loss
        if daily_pl < -(balance * MAX_DAILY_LOSS_PCT / 100):
            veto_triggered = True
            veto_reasons.append(f"⛔ {account_name}: Daily loss exceeds {MAX_DAILY_LOSS_PCT}% limit")

        assessment["accounts"][account_name] = account_status

    # Check consecutive losses
    consecutive = check_consecutive_losses(trade_log)
    assessment["consecutive_losses"] = consecutive

    if consecutive >= VETO_CONSECUTIVE_LOSSES:
        veto_triggered = True
        veto_reasons.append(f"⛔ {consecutive} consecutive losses — cooling off required")
    elif consecutive >= 3:
        assessment["factors"].append(f"⚠️ {consecutive} consecutive losses — reducing size")
        assessment["recommended_lot_size"] *= 0.5

    # Set final status
    if veto_triggered:
        assessment["veto"] = True
        assessment["go_no_go"] = "VETO"
        assessment["veto_reason"] = "; ".join(veto_reasons)
    else:
        assessment["go_no_go"] = "GO"

    return assessment


def save_risk_assessment(assessment: dict, date_str: str):
    """Save risk assessment to shared repo."""
    today_dir = SIGNALS_DIR / date_str
    today_dir.mkdir(parents=True, exist_ok=True)

    risk_file = today_dir / "alfred_risk.json"
    with open(risk_file, "w") as f:
        json.dump(assessment, f, indent=2)


def post_to_discord(message: str):
    """Post to Discord #risk-check channel."""
    # TODO: Implement with discord.py or HTTP API
    # bot_token = os.getenv("DISCORD_BOT_TOKEN")
    # channel_id = "RISK_CHECK_CHANNEL_ID"
    # requests.post(f"https://discord.com/api/channels/{channel_id}/messages",
    #               headers={"Authorization": f"Bot {bot_token}"},
    #               json={"content": message})
    print(f"[DISCORD #risk-check] {message}")


def main():
    now_hk = datetime.now(timezone(timedelta(hours=8)))
    date_str = now_hk.strftime("%Y-%m-%d")

    print(f"=== Alfred Risk Assessment — {date_str} ===")
    print(f"Time: {now_hk.strftime('%H:%M')} HKT")

    # Check if trading day
    if not is_trading_day():
        print("Not a trading day. Skipping.")
        return

    # Pull latest
    print("\n[1/4] Pulling shared repo...")
    git_pull()

    # Check MT5 accounts
    print("\n[2/4] Checking MT5 accounts...")
    accounts = check_mt5_accounts()
    for name, data in accounts.items():
        if data.get("status") == "error":
            print(f"  ⛔ {name}: ERROR — {data.get('error', 'Unknown')}")
        else:
            equity = data.get("equity", 0)
            balance = data.get("balance", 0)
            dd = data.get("dd_pct", 0)
            print(f"  {name}: Balance ${balance:,.2f} | Equity ${equity:,.2f} | DD {dd:.1f}%")

    # Load trade log
    print("\n[3/4] Loading trade log...")
    trade_log = load_trade_log()
    print(f"  Total trades logged: {len(trade_log)}")

    # Calculate risk assessment
    print("\n[4/4] Calculating risk assessment...")
    assessment = calculate_risk_assessment(accounts, trade_log)

    print(f"\n  Result: {assessment['go_no_go']}")
    if assessment["veto"]:
        print(f"  🛑 VETO: {assessment['veto_reason']}")
    for factor in assessment["factors"]:
        print(f"  {factor}")
    print(f"  Lot size multiplier: {assessment['recommended_lot_size']}")
    print(f"  Consecutive losses: {assessment['consecutive_losses']}")

    # Save to repo
    save_risk_assessment(assessment, date_str)
    print(f"\n  Risk assessment saved to signals/{date_str}/alfred_risk.json")

    # Post to Discord
    if assessment["veto"]:
        post_to_discord(
            f"🛑 **ALFRED RISK VETO**\n"
            f"Reason: {assessment['veto_reason']}\n"
            f"Date: {date_str}"
        )
    else:
        account_summary = []
        for name, data in assessment["accounts"].items():
            if data.get("status") == "ok":
                account_summary.append(f"{name}: DD {data['dd_pct']:.1f}%")
        post_to_discord(
            f"✅ **Alfred Risk Check — {date_str}**\n"
            f"Status: {assessment['go_no_go']}\n"
            f"Accounts: {', '.join(account_summary)}\n"
            f"Lot multiplier: {assessment['recommended_lot_size']}\n"
            f"Consecutive losses: {assessment['consecutive_losses']}"
        )

    # Commit and push
    git_push(f"Alfred: Risk assessment for {date_str} — {assessment['go_no_go']}")

    print(f"\n✅ Risk assessment complete.")


if __name__ == "__main__":
    main()
