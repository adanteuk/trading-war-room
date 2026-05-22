#!/usr/bin/env python3
"""
Trading War Room — Alfred Risk Agent (SINGLE ACCOUNT)
Runs at 6:30 PM HKT on trading days.
ONLY checks FTMO (My manual) account 510047082 — the war room strategy account.

Alfred has HARD VETO power:
- DD > 8% → VETO
- Daily loss > 2% → VETO
- MT5 connection error → VETO (safety first)
- 5+ consecutive losses → VETO

The veto is communicated via the shared repo and Discord.
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

# WAR ROOM TARGET ACCOUNT ONLY
TARGET_ACCOUNT = {
    "name": "FTMO (My manual)",
    "account_number": "510047082",
    "password": "88jV*N*E$J4**N",
    "server": "FTMO-Server",
    "notes": "Manual trading account — war room strategy",
}

# Windows Python for MT5 API
WINDOWS_PYTHON = "/mnt/c/Python312/python.exe"

# Risk thresholds
MAX_DAILY_LOSS_PCT = 2.0     # FTMO daily limit
MAX_TOTAL_DD_PCT = 10.0      # FTMO max DD
VETO_DD_THRESHOLD = 8.0      # Veto if above this
VETO_CONSECUTIVE_LOSSES = 5  # Veto after N consecutive losses

# US Market Holidays (2026)
US_HOLIDAYS = [
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
    "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07",
    "2026-11-26", "2026-12-25",
]

ACCOUNT_TIMEOUT_S = 12
ACCOUNT_TIMEOUT_MS = 12000

# Discord
DISCORD_BOT_TOKEN_ENV = "DISCORD_BOT_TOKEN"
DISCORD_RISK_CHECK_CHANNEL = "1505601652470583506"


def is_trading_day() -> bool:
    now_hk = datetime.now(timezone(timedelta(hours=8)))
    if now_hk.weekday() >= 5:  # Sat=5, Sun=6
        return False
    if now_hk.strftime("%Y-%m-%d") in US_HOLIDAYS:
        return False
    return True


def git_pull():
    os.chdir(REPO_DIR)
    subprocess.run(["git", "pull", "--rebase"], capture_output=True)

def git_push(message: str) -> bool:
    """Commit and push changes. Returns True on success, False on failure."""
    os.chdir(REPO_DIR)
    subprocess.run(["git", "add", "."], capture_output=True)
    result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ⚠️ git commit failed: {result.stderr.strip()[:200]}")
        return False
    push_result = subprocess.run(["git", "push"], capture_output=True, text=True)
    if push_result.returncode != 0:
        print(f"  🚨 git push FAILED: {push_result.stderr.strip()[:500]}")
        return False
    return True


def check_single_account() -> dict:
    """Check ONLY the war room target account via Windows MT5."""
    acc = TARGET_ACCOUNT
    mt5_script = f"""
import sys
sys.path.insert(0, r'C:\\\\Python312\\\\Lib\\\\site-packages')
import json
import MetaTrader5 as mt5
import threading

ACCOUNT_TIMEOUT_MS = {ACCOUNT_TIMEOUT_MS}
ACCOUNT_TIMEOUT_S = {ACCOUNT_TIMEOUT_S}

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

login = {acc['account_number']}
password = '{acc['password']}'
server = '{acc['server']}'

for attempt in range(2):
    mt5.shutdown()
    ok, error = try_login(login, password, server, ACCOUNT_TIMEOUT_MS)
    if ok:
        acc_info = mt5.account_info()
        if acc_info:
            balance = acc_info.balance
            equity = acc_info.equity
            dd_pct = ((balance - equity) / balance * 100) if balance > 0 else 0
            result = {{
                "name": "{acc['name']}",
                "account_number": "{acc['account_number']}",
                "balance": balance,
                "equity": equity,
                "dd_pct": round(dd_pct, 2),
                "daily_pl": equity - balance,
                "status": "ok",
            }}
            mt5.shutdown()
            print(json.dumps(result))
            sys.exit(0)
        else:
            error = 'no_account_info'
    if attempt == 0:
        import time; time.sleep(1)

mt5.shutdown()
result = {{
    "name": "{acc['name']}",
    "account_number": "{acc['account_number']}",
    "balance": 0, "equity": 0, "dd_pct": 0,
    "daily_pl": 0,
    "status": "error",
    "error": "Timeout" if 'timeout' in str(error).lower() else "Login failed",
}}
print(json.dumps(result))
"""
    import random
    import string
    script_name = f"wr_{''.join(random.choices(string.ascii_lowercase, k=8))}.py"
    win_temp_path = f"C:/Users/angus/AppData/Local/Temp/{script_name}"

    ps_cmd = f"""
$script = @'
{mt5_script}
'@
Set-Content -Path "{win_temp_path}" -Value $script -Encoding UTF8
"""
    ps = subprocess.run(
        ["/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe", "-Command", ps_cmd],
        capture_output=True, text=True, timeout=10
    )
    if ps.returncode != 0:
        raise Exception(f"PowerShell write failed: {ps.stderr[:200]}")

    result = subprocess.run(
        [WINDOWS_PYTHON, win_temp_path],
        capture_output=True, text=True, timeout=30
    )

    try:
        subprocess.run(["cmd.exe", "/c", "del", win_temp_path.replace("/", "\\")],
                       capture_output=True)
    except:
        pass

    if result.returncode == 0 and result.stdout.strip():
        return json.loads(result.stdout.strip())
    else:
        stderr_preview = result.stderr[:300] if result.stderr else 'no stderr'
        raise Exception(f"MT5 check failed: {stderr_preview}")


def load_trade_log() -> list:
    trade_log_file = REPO_DIR / "trade-log.json"
    if trade_log_file.exists():
        with open(trade_log_file) as f:
            return json.load(f)
    return []


def check_consecutive_losses(trade_log: list) -> int:
    consecutive = 0
    for trade in reversed(trade_log):
        if trade.get("result") == "loss":
            consecutive += 1
        else:
            break
    return consecutive


def calculate_risk(account: dict, trade_log: list) -> dict:
    now_hk = datetime.now(timezone(timedelta(hours=8)))
    assessment = {
        "timestamp": now_hk.isoformat(),
        "go_no_go": "GO",
        "veto": False,
        "veto_reason": "",
        "accounts": {},
        "factors": [],
        "recommended_lot_size": 1.0,
        "max_daily_loss_pct": MAX_DAILY_LOSS_PCT,
        "consecutive_losses": 0,
    }

    if account.get("status") == "error":
        assessment["veto"] = True
        assessment["go_no_go"] = "VETO"
        assessment["veto_reason"] = f"MT5 connection error — cannot verify risk for {account['name']}"
        assessment["accounts"][account["name"]] = {"status": "error", "error": account.get("error", "Unknown")}
        return assessment

    balance = account.get("balance", 0)
    equity = account.get("equity", balance)
    dd_pct = account.get("dd_pct", 0)
    daily_pl = account.get("daily_pl", 0)

    assessment["accounts"][account["name"]] = {
        "balance": balance, "equity": equity,
        "dd_pct": dd_pct, "daily_pl": daily_pl, "status": "ok",
    }

    # DD checks
    if dd_pct > MAX_TOTAL_DD_PCT:
        assessment["veto"] = True
        assessment["veto_reason"] = f"DD {dd_pct:.1f}% EXCEEDS max {MAX_TOTAL_DD_PCT}%"
    elif dd_pct > VETO_DD_THRESHOLD:
        assessment["veto"] = True
        assessment["veto_reason"] = f"DD {dd_pct:.1f}% above veto threshold {VETO_DD_THRESHOLD}%"
    elif dd_pct > 5:
        assessment["factors"].append(f"DD at {dd_pct:.1f}% — approaching caution zone")
        assessment["recommended_lot_size"] *= 0.5
    else:
        assessment["factors"].append(f"DD {dd_pct:.1f}% — within limits")

    # Daily loss check
    if daily_pl < -(balance * MAX_DAILY_LOSS_PCT / 100):
        assessment["veto"] = True
        assessment["veto_reason"] = f"Daily loss ${abs(daily_pl):.2f} exceeds {MAX_DAILY_LOSS_PCT}% limit (${balance * MAX_DAILY_LOSS_PCT / 100:.2f})"

    # Consecutive losses
    consecutive = check_consecutive_losses(trade_log)
    assessment["consecutive_losses"] = consecutive
    if consecutive >= VETO_CONSECUTIVE_LOSSES:
        assessment["veto"] = True
        assessment["veto_reason"] = f"{consecutive} consecutive losses — cooling off required"
    elif consecutive >= 3:
        assessment["factors"].append(f"{consecutive} consecutive losses — reducing size")
        assessment["recommended_lot_size"] *= 0.5

    if assessment["veto"]:
        assessment["go_no_go"] = "VETO"

    return assessment


def save_risk_assessment(assessment: dict, date_str: str):
    today_dir = SIGNALS_DIR / date_str
    today_dir.mkdir(parents=True, exist_ok=True)
    risk_file = today_dir / "alfred_risk.json"
    with open(risk_file, "w") as f:
        json.dump(assessment, f, indent=2)


def get_discord_token() -> str:
    env_path = Path(os.path.expanduser("~/.hermes/.env"))
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith("DISCORD_BOT_TOKEN="):
                    return line.strip().split("=", 1)[1]
    return ""


def post_to_discord(message: str):
    token = get_discord_token()
    if not token:
        print(f"[DISCORD] No token — printing locally: {message}")
        return

    import requests
    url = f"https://discord.com/api/v10/channels/{DISCORD_RISK_CHECK_CHANNEL}/messages"
    headers = {"Authorization": f"Bot {token}"}
    try:
        resp = requests.post(url, headers=headers, json={"content": message}, timeout=10)
        if resp.status_code == 200:
            print(f"  ✅ Posted to Discord #risk-check")
        else:
            print(f"  ⚠️ Discord API {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  ⚠️ Discord post failed: {e}")


def format_discord_message(assessment: dict, date_str: str) -> str:
    acc = assessment["accounts"].get(TARGET_ACCOUNT["name"], {})
    name = TARGET_ACCOUNT["name"]

    if assessment["veto"]:
        return (
            f"🛑 **WAR ROOM RISK VETO**\n"
            f"**{name}** — {date_str}\n"
            f"Reason: {assessment['veto_reason']}\n"
            f"Balance: ${acc.get('balance', 0):,.2f} | Equity: ${acc.get('equity', 0):,.2f} | DD: {acc.get('dd_pct', 0):.1f}%"
        )
    else:
        lines = [
            f"✅ **War Room Risk Check — {date_str}**",
            f"**{name}**",
            f"Balance: ${acc.get('balance', 0):,.2f}",
            f"Equity: ${acc.get('equity', 0):,.2f}",
            f"DD: {acc.get('dd_pct', 0):.1f}%",
            f"Daily P/L: ${acc.get('daily_pl', 0):,.2f}",
            f"Lot multiplier: {assessment['recommended_lot_size']}",
            f"Consecutive losses: {assessment['consecutive_losses']}",
        ]
        if assessment["factors"]:
            lines.append("---")
            lines.extend(assessment["factors"])
        lines.append(f"Status: **{assessment['go_no_go']}**")
        return "\n".join(lines)


def main():
    now_hk = datetime.now(timezone(timedelta(hours=8)))
    date_str = now_hk.strftime("%Y-%m-%d")

    print(f"=== War Room Risk Assessment — {date_str} ===")
    print(f"Time: {now_hk.strftime('%H:%M')} HKT")
    print(f"Target: {TARGET_ACCOUNT['name']} ({TARGET_ACCOUNT['account_number']})")

    if not is_trading_day():
        print("Not a trading day. Skipping.")
        return

    print("\n[1/4] Pulling shared repo...")
    git_pull()

    print("\n[2/4] Checking MT5 account...")
    try:
        account = check_single_account()
    except Exception as e:
        account = {
            "name": TARGET_ACCOUNT["name"],
            "account_number": TARGET_ACCOUNT["account_number"],
            "balance": 0, "equity": 0, "dd_pct": 0, "daily_pl": 0,
            "status": "error", "error": str(e)[:200],
        }

    if account.get("status") == "error":
        print(f"  ⛔ {account['name']}: ERROR — {account.get('error', 'Unknown')}")
    else:
        print(f"  Balance: ${account['balance']:,.2f} | Equity: ${account['equity']:,.2f} | DD: {account['dd_pct']:.1f}% | Daily P/L: ${account['daily_pl']:.2f}")

    print("\n[3/4] Loading trade log...")
    trade_log = load_trade_log()
    print(f"  Total trades logged: {len(trade_log)}")

    print("\n[4/4] Calculating risk assessment...")
    assessment = calculate_risk(account, trade_log)

    print(f"\n  Result: {assessment['go_no_go']}")
    if assessment["veto"]:
        print(f"  🛑 VETO: {assessment['veto_reason']}")
    for factor in assessment["factors"]:
        print(f"  {factor}")
    print(f"  Lot multiplier: {assessment['recommended_lot_size']}")
    print(f"  Consecutive losses: {assessment['consecutive_losses']}")

    save_risk_assessment(assessment, date_str)
    print(f"\n  Saved to signals/{date_str}/alfred_risk.json")

    msg = format_discord_message(assessment, date_str)
    post_to_discord(msg)

    if git_push(f"War Room: Risk assessment for {date_str} — {assessment['go_no_go']}"):
        print(f"\n✅ War Room risk assessment complete: {assessment['go_no_go']}")
    else:
        print(f"\n⚠️ Risk assessment saved locally but GIT PUSH FAILED — Merlin may not see it!")
        print(f"   Manual fix: cd {REPO_DIR} && git push")


if __name__ == "__main__":
    main()
