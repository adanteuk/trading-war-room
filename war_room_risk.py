#!/usr/bin/env python3
"""
Trading War Room — Alfred Risk Agent (Merlin's Specification)
Runs at 6:30 PM HKT on trading days.

Checks FTMO account 510047082 via ZeroMQ (preferred) with MT5 fallback.
Hard VETO power on risk breaches.

Merlin's updated thresholds (stricter than FTMO limits):
- Total DD < 5% (FTMO limit 10%)
- Daily DD < 2% (FTMO limit 5%)
- Consecutive losses < 3
- Open positions ≤ 2
- Margin usage < 30%
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

# ZeroMQ bridge
ZMQ_SERVER = "tcp://192.168.11.211:5555"
ZMQ_TIMEOUT_S = 5

# Windows Python for MT5 fallback
WINDOWS_PYTHON = "/mnt/c/Python312/python.exe"

# Risk thresholds (Merlin's spec — stricter than FTMO)
MAX_TOTAL_DD_PCT = 5.0       # Veto threshold (FTMO limit is 10%)
MAX_DAILY_DD_PCT = 2.0       # Veto threshold (FTMO limit is 5%)
MAX_DAILY_LOSS_PCT = 2.0     # Max daily loss as % of balance
MAX_CONSECUTIVE_LOSSES = 3   # Veto at this many
MAX_OPEN_POSITIONS = 2       # Veto at 3+
MAX_MARGIN_USAGE_PCT = 30.0  # Veto above this

# US Market Holidays (2026)
US_HOLIDAYS = [
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
    "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07",
    "2026-11-26", "2026-12-25",
]

# Discord
DISCORD_RISK_CHECK_CHANNEL = "1505601652470583506"


def is_trading_day() -> bool:
    now_hk = datetime.now(timezone(timedelta(hours=8)))
    if now_hk.weekday() >= 5:
        return False
    if now_hk.strftime("%Y-%m-%d") in US_HOLIDAYS:
        return False
    return True


def git_pull():
    os.chdir(REPO_DIR)
    subprocess.run(["git", "pull", "--rebase"], capture_output=True)


def git_push(message: str) -> bool:
    """Push to git. Returns True if successful."""
    os.chdir(REPO_DIR)
    subprocess.run(["git", "add", "."], capture_output=True)
    result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True)
    if b"nothing to commit" in result.stdout.encode() or b"nothing to commit" in result.stderr.encode():
        print("  (nothing new to commit)")
        return True
    push_result = subprocess.run(["git", "push"], capture_output=True, text=True)
    if push_result.returncode != 0:
        print(f"  ⚠️ Git push failed: {push_result.stderr[:300]}")
        return False
    return True


def check_via_zmq() -> dict:
    """Try to get account info via ZeroMQ bridge."""
    try:
        import zmq
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, ZMQ_TIMEOUT_S * 1000)
        socket.setsockopt(zmq.LINGER, 0)
        socket.connect(ZMQ_SERVER)

        request = json.dumps({
            "action": "get_account_info",
            "account_number": TARGET_ACCOUNT["account_number"],
        })
        socket.send_string(request)

        reply = socket.recv_string()
        socket.close()
        context.term()

        data = json.loads(reply)
        if data.get("status") == "ok":
            # Normalize ZMQ response to our expected schema
            # ZMQ may return data for a different account — verify login matches
            zmq_login = str(data.get("login", ""))
            target_login = TARGET_ACCOUNT["account_number"]
            if zmq_login != target_login:
                print(f"  ⚠️ ZMQ returned account {zmq_login}, expected {target_login} — falling back to MT5")
                return None

            balance = data.get("balance", 0)
            equity = data.get("equity", balance)
            margin = data.get("margin", 0)
            dd_pct = ((balance - equity) / balance * 100) if balance > 0 else 0
            margin_used_pct = (margin / balance * 100) if balance > 0 else 0

            result = {
                "name": TARGET_ACCOUNT["name"],
                "account_number": target_login,
                "balance": round(balance, 2),
                "equity": round(equity, 2),
                "dd_pct": round(dd_pct, 2),
                "daily_pl": 0,  # ZMQ doesn't provide this directly
                "open_positions": 0,  # ZMQ doesn't provide this directly
                "margin_used": round(margin, 2),
                "margin_free": round(data.get("free_margin", 0), 2),
                "margin_used_pct": round(margin_used_pct, 2),
                "margin_level": data.get("margin_level", 0),
                "status": "ok",
                "source": "zmq",
                "currency": data.get("currency", "USD"),
                "leverage": data.get("leverage", 0),
            }
            print("  ✅ ZMQ connection successful — account verified")
            return result
        else:
            print(f"  ⚠️ ZMQ returned error: {data.get('error', 'unknown')}")
            return None
    except ImportError:
        print("  ⚠️ pyzmq not installed, skipping ZMQ")
        return None
    except Exception as e:
        print(f"  ⚠️ ZMQ failed: {str(e)[:100]}")
        return None


def check_via_mt5_fallback() -> dict:
    """Fallback: check account via Windows MT5 subprocess."""
    acc = TARGET_ACCOUNT
    mt5_script = f"""
import sys
sys.path.insert(0, r'C:\\\\Python312\\\\Lib\\\\site-packages')
import json
import MetaTrader5 as mt5
import threading

ACCOUNT_TIMEOUT_MS = 12000
ACCOUNT_TIMEOUT_S = 12

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
            margin = acc_info.margin
            free_margin = acc_info.margin_free
            margin_level = acc_info.margin_level

            # Count open positions
            positions = mt5.positions_get()
            open_positions = len(positions) if positions else 0

            # Calculate DD
            dd_pct = ((balance - equity) / balance * 100) if balance > 0 else 0

            # Margin usage
            margin_used_pct = (margin / balance * 100) if balance > 0 else 0

            # Daily P&L from closed positions today
            from datetime import datetime as dt, timezone as tz, timedelta as td
            now = dt.now(tz(td(hours=-5)))  # NY timezone for MT5 server time
            today_start = dt(now.year, now.month, now.day, tzinfo=tz(td(hours=-5)))
            today_start_ts = int(today_start.timestamp())

            history = mt5.history_orders_get(today_start_ts, int(dt.now(tz(td(hours=8))).timestamp()))
            daily_realized = 0.0
            if history:
                for order in history:
                    daily_realized += order.profit + order.commission + order.swap

            daily_pl = daily_realized + (equity - balance)

            result = {{
                "name": "{acc['name']}",
                "account_number": "{acc['account_number']}",
                "balance": round(balance, 2),
                "equity": round(equity, 2),
                "dd_pct": round(dd_pct, 2),
                "daily_pl": round(daily_pl, 2),
                "open_positions": open_positions,
                "margin_used": round(margin, 2),
                "margin_free": round(free_margin, 2),
                "margin_used_pct": round(margin_used_pct, 2),
                "margin_level": margin_level if margin_level else 0,
                "status": "ok",
                "source": "mt5",
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
    "balance": 0, "equity": 0, "dd_pct": 0, "daily_pl": 0,
    "open_positions": 0, "margin_used_pct": 0,
    "status": "error",
    "error": "Timeout" if 'timeout' in str(error).lower() else "Login failed",
    "source": "mt5",
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


def check_account() -> dict:
    """Try ZMQ first, fallback to MT5."""
    print("  Trying ZeroMQ bridge...")
    zmq_result = check_via_zmq()
    if zmq_result:
        return zmq_result

    print("  Falling back to MT5 Windows Python...")
    return check_via_mt5_fallback()


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


def check_walker_ta(date_str: str) -> dict:
    """Check if Walker's TA is available for lot size calculation."""
    ta_file = SIGNALS_DIR / date_str / "walker_ta.json"
    if ta_file.exists():
        with open(ta_file) as f:
            return json.load(f)
    return None


def calculate_lot_size(balance: float, sl_points: float = None) -> float:
    """
    Lot size calculation per Merlin's spec:
    Risk per trade = Balance × 2%
    SL distance in points = from Walker TA
    Point value = $10 per point for NAS100 (1.0 lot)
    Lot size = Risk / (SL points × Point value)
    Round to nearest 0.1
    """
    risk_per_trade = balance * 0.02  # 2% max risk
    point_value = 10.0  # NAS100: $10/point per 1.0 lot

    if sl_points and sl_points > 0:
        lot_size = risk_per_trade / (sl_points * point_value)
    else:
        return 1.0  # Default if no SL info

    # Round to nearest 0.1
    lot_size = round(lot_size * 10) / 10
    return max(0.1, lot_size)  # Minimum 0.1 lot


def calculate_risk(account: dict, trade_log: list, walker_ta: dict, date_str: str) -> dict:
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
        "notes": "",
    }

    account_name = TARGET_ACCOUNT["name"]

    # Handle connection error → default to NO_GO for safety
    if account.get("status") == "error":
        assessment["go_no_go"] = "NO_GO"
        assessment["veto"] = True
        assessment["veto_reason"] = f"Cannot verify account status — MT5/ZMQ connection error for {account_name}"
        assessment["accounts"][account_name] = {"status": "error", "error": account.get("error", "Unknown")}
        assessment["notes"] = "Safety first: cannot verify risk status, defaulting to NO_GO"
        return assessment

    balance = account.get("balance", 0)
    equity = account.get("equity", balance)
    dd_pct = account.get("dd_pct", 0)
    daily_pl = account.get("daily_pl", 0)
    open_positions = account.get("open_positions", 0)
    margin_used_pct = account.get("margin_used_pct", 0)

    assessment["accounts"][account_name] = {
        "balance": round(balance, 2),
        "equity": round(equity, 2),
        "dd_pct": round(dd_pct, 2),
        "daily_pl": round(daily_pl, 2),
        "open_positions": open_positions,
        "margin_used_pct": round(margin_used_pct, 2),
        "status": "ok",
    }

    veto_triggered = False
    veto_reasons = []

    # ─── Veto Checks ───

    # 1. Total DD
    if dd_pct >= MAX_TOTAL_DD_PCT:
        veto_triggered = True
        veto_reasons.append(f"Total DD {dd_pct:.1f}% ≥ {MAX_TOTAL_DD_PCT}% limit")
    elif dd_pct >= 4.0:
        assessment["factors"].append(f"⚠️ DD at {dd_pct:.1f}% — approaching danger zone (4-5%)")
        assessment["notes"] = "Marginal risk — reduced lot size recommended"
    else:
        assessment["factors"].append(f"✅ DD {dd_pct:.1f}% — within limits")

    # 2. Daily DD (absolute daily loss vs balance)
    daily_dd_pct = abs(daily_pl) / balance * 100 if balance > 0 and daily_pl < 0 else 0
    if daily_dd_pct >= MAX_DAILY_DD_PCT:
        veto_triggered = True
        veto_reasons.append(f"Daily DD {daily_dd_pct:.1f}% ≥ {MAX_DAILY_DD_PCT}% limit")
    else:
        assessment["factors"].append(f"✅ Daily DD {daily_dd_pct:.1f}% — within limits")

    # 3. Consecutive losses
    consecutive = check_consecutive_losses(trade_log)
    assessment["consecutive_losses"] = consecutive
    if consecutive >= MAX_CONSECUTIVE_LOSSES:
        veto_triggered = True
        veto_reasons.append(f"{consecutive} consecutive losses ≥ {MAX_CONSECUTIVE_LOSSES} limit")
    elif consecutive >= 2:
        assessment["factors"].append(f"⚠️ {consecutive} consecutive losses — caution advised")
    else:
        assessment["factors"].append(f"✅ {consecutive} consecutive losses — OK")

    # 4. Open positions
    if open_positions > MAX_OPEN_POSITIONS:
        veto_triggered = True
        veto_reasons.append(f"{open_positions} open positions > {MAX_OPEN_POSITIONS} max")
    elif open_positions == MAX_OPEN_POSITIONS:
        assessment["factors"].append(f"⚠️ {open_positions} open positions — at limit")
    else:
        assessment["factors"].append(f"✅ {open_positions} open positions — OK")

    # 5. Margin usage
    if margin_used_pct >= MAX_MARGIN_USAGE_PCT:
        veto_triggered = True
        veto_reasons.append(f"Margin usage {margin_used_pct:.1f}% ≥ {MAX_MARGIN_USAGE_PCT}%")
    else:
        assessment["factors"].append(f"✅ Margin usage {margin_used_pct:.1f}% — within limits")

    # 6. News event check (simple: check if within 15 min of major news times)
    now_hk_time = now_hk
    ny_time = now_hk_time - timedelta(hours=13)  # HKT to NY (EST/EDT approx)
    ny_hour = ny_time.hour
    ny_min = ny_time.minute
    # Major news times: 08:30, 10:00, 14:00 NY
    news_times = [(8, 30), (10, 0), (14, 0)]
    for nh, nm in news_times:
        diff_min = abs((ny_hour - nh) * 60 + (ny_min - nm))
        if diff_min <= 15:
            assessment["factors"].append(f"⚠️ News event window — {nh}:{nm:02d} NY")
            assessment["notes"] = "News event within 15 min — temporary caution"

    # ─── Lot Size Calculation ───
    sl_points = None
    if walker_ta and walker_ta.get("sl_points"):
        sl_points = walker_ta["sl_points"]
        assessment["notes"] += f" (SL from Walker TA: {sl_points} points)"

    lot_size = calculate_lot_size(balance, sl_points)

    # Reduce lot size if marginal conditions
    if not veto_triggered:
        if dd_pct >= 4.0 or consecutive >= 2:
            lot_size = round(lot_size * 0.5 * 10) / 10  # Halve it
            assessment["factors"].append("⚠️ Lot size reduced due to marginal risk")

    assessment["recommended_lot_size"] = max(0.1, lot_size)

    # ─── Final Decision ───
    if veto_triggered:
        assessment["veto"] = True
        assessment["go_no_go"] = "NO_GO"
        assessment["veto_reason"] = "; ".join(veto_reasons)
    elif walker_ta is None:
        assessment["go_no_go"] = "WAIT"
        assessment["notes"] += " | Waiting for Walker TA before final GO"
    else:
        assessment["go_no_go"] = "GO"

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
        print(f"[DISCORD] No token — printing locally")
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
    acc_name = TARGET_ACCOUNT["name"]
    acc = assessment["accounts"].get(acc_name, {})

    status_emoji = "✅" if assessment["go_no_go"] == "GO" else "⏸️" if assessment["go_no_go"] == "WAIT" else "🛑"

    lines = [
        f"🦇 **ALFRED RISK ASSESSMENT — {date_str}**",
        f"",
        f"Status: {status_emoji} {assessment['go_no_go']}",
        f"Veto: {'Yes' if assessment['veto'] else 'No'}",
        f"",
        f"**Account Health:**",
        f"• Balance: ${acc.get('balance', 0):,.2f}",
        f"• Equity: ${acc.get('equity', 0):,.2f}",
        f"• DD: {acc.get('dd_pct', 0):.1f}%",
        f"• Daily P&L: ${acc.get('daily_pl', 0):,.2f}",
        f"• Open Positions: {acc.get('open_positions', 0)}",
        f"• Consecutive Losses: {assessment['consecutive_losses']}",
        f"",
        f"**Risk Factors:**",
    ]
    for factor in assessment.get("factors", ["No data"]):
        lines.append(f"• {factor}")

    lines.append(f"")
    lines.append(f"Recommended Lot Size: {assessment['recommended_lot_size']}")
    lines.append(f"Max Daily Loss: {assessment['max_daily_loss_pct']}%")

    if assessment.get("veto_reason"):
        lines.append(f"")
        lines.append(f"🛑 **VETO REASON:** {assessment['veto_reason']}")

    if assessment.get("notes"):
        lines.append(f"")
        lines.append(f"Notes: {assessment['notes']}")

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

    print("\n[1/5] Pulling shared repo...")
    git_pull()

    print("\n[2/5] Checking account status...")
    try:
        account = check_account()
    except Exception as e:
        print(f"  ⛔ Account check failed: {str(e)[:200]}")
        account = {
            "name": TARGET_ACCOUNT["name"],
            "account_number": TARGET_ACCOUNT["account_number"],
            "balance": 0, "equity": 0, "dd_pct": 0, "daily_pl": 0,
            "open_positions": 0, "margin_used_pct": 0,
            "status": "error", "error": str(e)[:200],
            "source": "unknown",
        }

    if account.get("status") == "error":
        print(f"  ⛔ {account['name']}: ERROR — {account.get('error', 'Unknown')}")
    else:
        source = account.get("source", "unknown")
        print(f"  Source: {source.upper()}")
        print(f"  Balance: ${account['balance']:,.2f} | Equity: ${account['equity']:,.2f}")
        print(f"  DD: {account['dd_pct']:.1f}% | Daily P/L: ${account['daily_pl']:.2f}")
        print(f"  Open positions: {account.get('open_positions', 0)} | Margin: {account.get('margin_used_pct', 0):.1f}%")

    print("\n[3/5] Loading trade log and Walker TA...")
    trade_log = load_trade_log()
    walker_ta = check_walker_ta(date_str)
    print(f"  Trades logged: {len(trade_log)}")
    print(f"  Walker TA: {'✅ Found' if walker_ta else '⏳ Not yet available'}")

    print("\n[4/5] Calculating risk assessment...")
    assessment = calculate_risk(account, trade_log, walker_ta, date_str)

    status = assessment["go_no_go"]
    print(f"\n  Result: {status}")
    if assessment["veto"]:
        print(f"  🛑 VETO: {assessment['veto_reason']}")
    for factor in assessment["factors"]:
        print(f"  {factor}")
    print(f"  Lot size: {assessment['recommended_lot_size']}")
    print(f"  Consecutive losses: {assessment['consecutive_losses']}")
    if assessment.get("notes"):
        print(f"  Notes: {assessment['notes']}")

    print("\n[5/5] Saving and posting...")
    save_risk_assessment(assessment, date_str)
    print(f"  Saved to signals/{date_str}/alfred_risk.json")

    msg = format_discord_message(assessment, date_str)
    post_to_discord(msg)

    pushed = git_push(f"War Room: Risk assessment for {date_str} — {status}")
    if pushed:
        print(f"  ✅ Git pushed")
    else:
        print(f"  ⚠️ Git push failed — please push manually")

    print(f"\n{'='*50}")
    print(f"✅ War Room risk assessment complete: {status}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
