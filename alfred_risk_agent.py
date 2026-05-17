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
ACCOUNTS_FILE = Path(os.path.expanduser("~/.hermes/hermes-agent/workspace/mt5_accounts.yaml"))

# Windows Python for MT5 API (MT5 package has native Windows extensions)
WINDOWS_PYTHON = "/mnt/c/Python312/python.exe"

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


def try_mt5_login(login, password, server, timeout_ms):
    """Threaded MT5 login attempt with hard timeout."""
    result = [None, None]  # [success, error]
    def _login():
        try:
            ok = mt5.initialize(login=login, password=password, server=server, timeout=timeout_ms)
            result[0] = ok
        except Exception as e:
            result[1] = str(e)
    t = threading.Thread(target=_login, daemon=True)
    t.start()
    t.join(timeout=ACCOUNT_TIMEOUT_S + 2)  # 2s buffer
    if t.is_alive():
        return False, 'thread_timeout'
    if result[1]:
        return False, result[1]
    return result[0], None


def check_mt5_accounts() -> dict:
    """
    Check all MT5 account balances, equity, and drawdown.
    Spawns Windows Python subprocess to use the MT5 Python API
    (which has native Windows extensions that won't work in WSL).

    Returns:
        dict of account_name -> {balance, equity, dd_pct, daily_pl, status}
    """
    # Create a temporary Windows Python script that does the MT5 checks
    mt5_script = """
import sys
sys.path.insert(0, r'C:\\Python312\\Lib\\site-packages')
import yaml
import json
import MetaTrader5 as mt5
import threading
import time

ACCOUNTS_FILE = r'/home/ychen/.hermes/hermes-agent/workspace/mt5_accounts.yaml'
ACCOUNT_TIMEOUT_MS = 12000
ACCOUNT_TIMEOUT_S = 12
GLOBAL_DEADLINE_S = 80

def try_login(login, password, server, timeout_ms):
    result = [None, None]
    def _login():
        try:
            ok = mt5.initialize(login=login, password=password, server=server, timeout=timeout_ms)
            result[0] = ok
        except Exception as e:
            result[1] = str(e)
    t = threading.Thread(target=_login, daemon=True)
    t.start()
    t.join(timeout=ACCOUNT_TIMEOUT_S + 2)
    if t.is_alive():
        return False, 'thread_timeout'
    if result[1]:
        return False, result[1]
    return result[0], None

# Convert WSL path to Windows path for yaml loading
import subprocess
result = subprocess.run(['wslpath', '-w', ACCOUNTS_FILE], capture_output=True, text=True)
win_path = result.stdout.strip() if result.returncode == 0 else ACCOUNTS_FILE

with open(win_path, 'r') as f:
    data = yaml.safe_load(f)
accounts_config = data.get('accounts', [])

accounts = {}
global_start = time.time()

for acc in accounts_config:
    elapsed = time.time() - global_start
    remaining = GLOBAL_DEADLINE_S - elapsed
    if remaining < 5:
        accounts[acc['name']] = {
            "balance": 0, "equity": 0, "dd_pct": 0,
            "status": "error", "error": "[Time limit reached]"
        }
        continue

    name = acc['name']
    login = int(acc['account_number'])
    password = acc['password']
    server = acc['server']

    if not password:
        accounts[name] = {
            "balance": 0, "equity": 0, "dd_pct": 0,
            "status": "error", "error": "[No password]"
        }
        continue

    success = False
    for attempt in range(2):
        mt5.shutdown()
        ok, error = try_login(login, password, server, ACCOUNT_TIMEOUT_MS)
        if ok:
            acc_info = mt5.account_info()
            if acc_info:
                balance = acc_info.balance
                equity = acc_info.equity
                dd_pct = ((balance - equity) / balance * 100) if balance > 0 else 0
                accounts[name] = {
                    "balance": balance,
                    "equity": equity,
                    "dd_pct": round(dd_pct, 2),
                    "daily_pl": equity - balance,
                    "status": "ok",
                }
                success = True
            else:
                error = 'no_account_info'
            break
        else:
            if attempt == 0:
                time.sleep(1)

    if not success:
        accounts[name] = {
            "balance": 0, "equity": 0, "dd_pct": 0,
            "status": "error",
            "error": "[Timeout]" if 'timeout' in str(error).lower() else "[Login failed]"
        }

mt5.shutdown()
print(json.dumps(accounts))
"""

    try:
        # Write temp script to Windows temp directory
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False,
            dir='/mnt/c/Users/angus/AppData/Local/Temp/',
            prefix='mt5_check_'
        ) as f:
            f.write(mt5_script)
            temp_script = f.name

        # Run via Windows Python
        result = subprocess.run(
            [WINDOWS_PYTHON, temp_script],
            capture_output=True, text=True, timeout=120
        )

        # Clean up temp file
        try:
            os.unlink(temp_script)
        except:
            pass

        if result.returncode == 0 and result.stdout.strip():
            accounts = json.loads(result.stdout.strip())
            return accounts
        else:
            stderr_preview = result.stderr[:300] if result.stderr else 'no stderr'
            stdout_preview = result.stdout[:300] if result.stdout else 'no stdout'
            print(f"  ⚠️ MT5 subprocess failed: {result.returncode}")
            print(f"  stdout: {stdout_preview}")
            print(f"  stderr: {stderr_preview}")
            return {
                "ERROR": {
                    "balance": 0, "equity": 0, "dd_pct": 0,
                    "status": "error",
                    "error": f"MT5 subprocess failed: {stderr_preview}",
                }
            }

    except subprocess.TimeoutExpired:
        return {
            "ERROR": {
                "balance": 0, "equity": 0, "dd_pct": 0,
                "status": "error",
                "error": "MT5 check timed out after 120s",
            }
        }
    except Exception as e:
        return {
            "ERROR": {
                "balance": 0, "equity": 0, "dd_pct": 0,
                "status": "error",
                "error": str(e),
            }
        }


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


def post_to_discord(message: str, channel_id: str = None):
    """Post to Discord channel via HTTP API."""
    token = ""
    env_path = Path(os.path.expanduser("~/.hermes/.env"))
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith("DISCORD_BOT_TOKEN="):
                    token = line.strip().split("=", 1)[1]
                    break

    if not token:
        print(f"[DISCORD] No token found — printing locally")
        print(f"[DISCORD] {message}")
        return

    # Default to #risk-check channel if not specified
    if not channel_id:
        channel_id = os.getenv("WAR_ROOM_RISK_CHANNEL", "1505566436775694366")

    import requests
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {token}"}
    try:
        resp = requests.post(url, headers=headers, json={"content": message}, timeout=10)
        if resp.status_code == 200:
            print(f"  ✅ Posted to Discord channel {channel_id}")
        else:
            print(f"  ⚠️ Discord API error {resp.status_code}: {resp.text[:200]}")
            print(f"[DISCORD] {message}")
    except Exception as e:
        print(f"  ⚠️ Discord post failed: {e}")
        print(f"[DISCORD] {message}")


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
