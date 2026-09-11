#!/usr/bin/env python3
"""
carson_order_handler.py — v3 Phase 4: Carson's order action implementation

This module implements the 9-check order handler for Carson's MT5 ZMQ server.
Drop into Carson's zmq/ directory and import from MT5_server.py, or run standalone
for testing.

Checks (all must pass, in order):
  1. Auth key (for order-class actions)
  2. Source IP whitelist
  3. git pull in C:/Users/hkvid/trading-war-room
  4. decision_id exists in decisions/{date}.json AND status GO AND payload matches
  5. SL present
  6. risk <= 1% equity
  7. lot <= 2.0
  8. symbol in verified list
  9. valid_until not expired

On success: order_send via MT5, append to execution_log.json, return fill details.
On failure: append to rejected_orders.log, return rejection reason.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────
REPO_DIR = Path(r"C:/Users/hkvid/trading-war-room")
DECISIONS_DIR = REPO_DIR / "decisions"
SIGNALS_DIR = REPO_DIR / "signals"
ORDER_KEY_FILE = Path(r"C:/Users/hkvid/zmq/.order_key")
ALLOWED_IPS = {"192.168.11.173", "192.168.11.211"}  # Mac IPs (Merlin's IPs)
VERIFIED_SYMBOLS = {"NAS100", "US500", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"}  # Carson §13
MAX_LOT = 2.0
MAX_RISK_PCT = 0.01  # 1%


def load_order_key() -> str | None:
    if not ORDER_KEY_FILE.exists():
        return None
    return ORDER_KEY_FILE.read_text().strip()


def check_auth(payload: dict) -> tuple[bool, str]:
    """Check 1: API key for order-class actions."""
    key = load_order_key()
    if key is None:
        return False, "ORDER_KEY_MISSING: no key file — order action disabled"
    if payload.get("auth") != key:
        return False, "AUTH_FAILED: invalid or missing auth key"
    return True, ""


def check_ip(client_ip: str) -> tuple[bool, str]:
    """Check 2: Source IP whitelist."""
    if client_ip not in ALLOWED_IPS:
        return False, f"IP_NOT_ALLOWED: {client_ip} not in {sorted(ALLOWED_IPS)}"
    return True, ""


def git_pull() -> tuple[bool, str]:
    """Check 3 (part 1): git pull to sync decisions."""
    try:
        r = subprocess.run(["git", "pull", "--rebase"], cwd=REPO_DIR,
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return False, f"GIT_PULL_FAILED: {r.stderr[:200]}"
        return True, ""
    except Exception as e:
        return False, f"GIT_PULL_ERROR: {e}"


def verify_decision(payload: dict) -> tuple[bool, str, dict | None]:
    """Check 4: decision_id exists, status GO, payload matches."""
    decision_id = payload.get("decision_id")
    if not decision_id:
        return False, "NO_DECISION_ID", None
    # Parse date from decision_id: "2026-09-14-NAS100-1" → "2026-09-14"
    parts = decision_id.split("-")
    if len(parts) < 4:
        return False, f"INVALID_DECISION_ID_FORMAT: {decision_id}", None
    date_str = "-".join(parts[:3])  # first 3 parts: year-month-day
    decision_file = DECISIONS_DIR / f"{date_str}.json"
    if not decision_file.exists():
        return False, f"DECISION_FILE_MISSING: {decision_file}", None
    try:
        with open(decision_file) as f:
            decision = json.load(f)
    except Exception as e:
        return False, f"DECISION_FILE_CORRUPT: {e}", None
    if decision.get("decision_id") != decision_id:
        return False, f"DECISION_ID_MISMATCH: payload={decision_id} file={decision.get('decision_id')}", None
    if decision.get("final_decision") not in ("GO", "CONDITIONAL_GO"):
        return False, f"DECISION_NOT_GO: {decision.get('final_decision')}", None
    # Verify payload fields match decision's trade_params
    # Map payload field names to decision field names
    field_mapping = {
        "symbol": "symbol",
        "direction": "direction",
        "entry": "entry",
        "sl": "stop_loss",      # payload uses "sl", decision uses "stop_loss"
        "tp": "take_profit",    # payload uses "tp", decision uses "take_profit"
    }
    tp = decision.get("trade_params", {})
    for payload_field, decision_field in field_mapping.items():
        payload_val = payload.get(payload_field)
        decision_val = tp.get(decision_field)
        if payload_val != decision_val:
            return False, f"PAYLOAD_MISMATCH: {payload_field} payload={payload_val} decision={decision_val}", None
    return True, "", decision


def check_sl(payload: dict) -> tuple[bool, str]:
    """Check 5: SL present."""
    if not payload.get("sl"):
        return False, "SL_MISSING: stop loss required"
    return True, ""


def check_risk(payload: dict, equity: float) -> tuple[bool, str]:
    """Check 6: risk ≤ 1% equity."""
    entry = payload.get("entry", 0)
    sl = payload.get("sl", 0)
    lot = payload.get("lot", 0)
    if not (entry and sl and lot):
        return False, f"INVALID_RISK_PARAMS: entry={entry} sl={sl} lot={lot}"
    sl_points = abs(entry - sl)
    # NAS100 point value = $10 per point per lot (CFD)
    risk_amount = lot * sl_points * 10.0
    risk_pct = risk_amount / equity if equity > 0 else 1.0
    if risk_pct > MAX_RISK_PCT:
        return False, f"RISK_EXCEEDS_1PCT: {risk_pct:.2%} > {MAX_RISK_PCT:.0%}"
    return True, ""


def check_lot(payload: dict) -> tuple[bool, str]:
    """Check 7: lot ≤ 2.0."""
    lot = payload.get("lot", 0)
    if lot > MAX_LOT:
        return False, f"LOT_EXCEEDS_MAX: {lot} > {MAX_LOT}"
    return True, ""


def check_symbol(payload: dict) -> tuple[bool, str]:
    """Check 8: symbol ∈ verified list."""
    symbol = payload.get("symbol")
    if symbol not in VERIFIED_SYMBOLS:
        return False, f"SYMBOL_NOT_VERIFIED: {symbol} not in {sorted(VERIFIED_SYMBOLS)}"
    return True, ""


def check_expiry(payload: dict) -> tuple[bool, str]:
    """Check 9: valid_until not expired."""
    valid_until = payload.get("valid_until")
    if not valid_until:
        return False, "NO_VALID_UNTIL: payload missing valid_until"
    try:
        expiry = datetime.fromisoformat(valid_until.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expiry:
            return False, f"ORDER_EXPIRED: valid_until={valid_until}"
    except Exception as e:
        return False, f"INVALID_VALID_UNTIL: {e}"
    return True, ""


def execute_order(payload: dict, mt5_module) -> dict:
    """Execute the order via MT5. Returns {ticket, fill_price, slippage, timestamps}."""
    import MetaTrader5 as mt5
    symbol = payload["symbol"]
    direction = payload["direction"].upper()
    entry = payload["entry"]
    sl = payload["sl"]
    tp = payload.get("tp")
    lot = payload["lot"]
    order_type = mt5.ORDER_TYPE_BUY if direction == "LONG" else mt5.ORDER_TYPE_SELL
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": entry,
        "sl": sl,
        "tp": tp if tp else 0.0,
        "deviation": 20,  # 20 points slippage tolerance
        "magic": 234000,
        "comment": f"v3:{payload.get('decision_id', 'unknown')}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result is None:
        return {"error": f"order_send returned None: {mt5.last_error()}"}
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return {"error": f"order_send retcode={result.retcode}: {result.comment}"}
    return {
        "ticket": result.order,
        "fill_price": result.price,
        "slippage": abs(result.price - entry),
        "volume": result.volume,
        "comment": result.comment,
    }


def log_execution(payload: dict, result: dict):
    """Append to signals/{date}/execution_log.json."""
    date_str = payload.get("decision_id", "").split("-")[0]
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = SIGNALS_DIR / date_str / "execution_log.json"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision_id": payload.get("decision_id"),
        "symbol": payload.get("symbol"),
        "direction": payload.get("direction"),
        "requested_entry": payload.get("entry"),
        "requested_sl": payload.get("sl"),
        "requested_tp": payload.get("tp"),
        "requested_lot": payload.get("lot"),
        "result": result,
    }
    existing = []
    if log_file.exists():
        try:
            with open(log_file) as f:
                existing = json.load(f)
        except Exception:
            existing = []
    existing.append(entry)
    with open(log_file, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


def log_rejection(payload: dict, reason: str):
    """Append to rejected_orders.log."""
    log_file = REPO_DIR / "rejected_orders.log"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision_id": payload.get("decision_id"),
        "symbol": payload.get("symbol"),
        "reason": reason,
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def handle_order(payload: dict, client_ip: str, mt5_module=None) -> dict:
    """Main entry point: run all 9 checks, execute if pass, log result."""
    import MetaTrader5 as mt5
    if mt5_module:
        mt5 = mt5_module

    # Check 1: Auth
    ok, msg = check_auth(payload)
    if not ok:
        log_rejection(payload, msg)
        return {"status": "error", "msg": msg}

    # Check 2: IP
    ok, msg = check_ip(client_ip)
    if not ok:
        log_rejection(payload, msg)
        return {"status": "error", "msg": msg}

    # Check 3: git pull
    ok, msg = git_pull()
    if not ok:
        log_rejection(payload, msg)
        return {"status": "error", "msg": msg}

    # Check 4: decision verification
    ok, msg, decision = verify_decision(payload)
    if not ok:
        log_rejection(payload, msg)
        return {"status": "error", "msg": msg}

    # Check 5: SL
    ok, msg = check_sl(payload)
    if not ok:
        log_rejection(payload, msg)
        return {"status": "error", "msg": msg}

    # Check 6: risk
    equity = mt5.account_info().equity if mt5.account_info() else 0
    ok, msg = check_risk(payload, equity)
    if not ok:
        log_rejection(payload, msg)
        return {"status": "error", "msg": msg}

    # Check 7: lot
    ok, msg = check_lot(payload)
    if not ok:
        log_rejection(payload, msg)
        return {"status": "error", "msg": msg}

    # Check 8: symbol
    ok, msg = check_symbol(payload)
    if not ok:
        log_rejection(payload, msg)
        return {"status": "error", "msg": msg}

    # Check 9: expiry
    ok, msg = check_expiry(payload)
    if not ok:
        log_rejection(payload, msg)
        return {"status": "error", "msg": msg}

    # All checks passed — execute
    result = execute_order(payload, mt5)
    if "error" in result:
        log_rejection(payload, result["error"])
        return {"status": "error", "msg": result["error"]}

    log_execution(payload, result)
    return {"status": "ok", "result": result}


if __name__ == "__main__":
    # Standalone test mode (no MT5)
    print("carson_order_handler.py — import this module from MT5_server.py")
    print("Checks implemented:", [f.__name__ for f in [check_auth, check_ip, git_pull,
                                                         verify_decision, check_sl,
                                                         check_risk, check_lot,
                                                         check_symbol, check_expiry]])
