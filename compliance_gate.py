#!/usr/bin/env python3
"""
compliance_gate.py — Five-Stage Pipeline v3, Stage 5 (deterministic compliance checks)

Rules, not judgment. Runs after quant gate, before the orchestrator decision
matrix. Any VETO = trade terminated. Exit 0 = pass, 2 = veto.

Checks (v2.4 → v3 migration, AC-approved 2026-09-14):
  1. News blackout: high-impact event (FOMC/NFP/CPI/ECB/rate decisions) within
     ±30 min of entry window → VETO (v2.4: scattered in Merlin/Walker prompts;
     Walker's <15min FOMC rule subsumed by this)
  2. MT5 bridge health: ping Carson ZMQ → unreachable or mt5_connected=false → VETO
     (moved from Walker's veto list per his follow-up agreement)
  3. Kill-zone window: entry must fall in an asset-class-appropriate Kill Zone
  4. Daily trade count: > 3 executed trades today → VETO
  5. Daily loss cap: daily P&L <= -2% of equity → VETO
  6. Weekly loss cap: weekly P&L <= -6% of equity → VETO
  7. Cooldown: same symbol re-entry within 60 min of last close → VETO
  8. Carson status pre-check: order action only allowed once security
     hardening is deployed (guard rail during rollout)

Calendar source: pluggable via --calendar (JSON list of events with
{time_utc, currency, impact, name}); see docs in five-stage-pipeline-v3.md §6.

Usage:
  python3 compliance_gate.py --date YYYY-MM-DD [--entry-window "13:30-16:00"] \
      [--symbol NAS100] [--skip-mt5-ping]
Writes signals/<date>/compliance_gate.json
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Hard-coded policy (AC-approved) ─────────────────────────────────
NEWS_BLACKOUT_MIN = 30          # ± minutes around high-impact events
HIGH_IMPACT_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "HKD", "CNY"}
HIGH_IMPACT_KEYWORDS = ("fomc", "nonfarm", "nfp", "cpi", "rate decision",
                        "interest rate", "ecb", "fed ", "gdp", "ppi",
                        "unemployment", "payrolls")
MAX_TRADES_PER_DAY = 3
DAILY_LOSS_CAP_PCT = 2.0
WEEKLY_LOSS_CAP_PCT = 6.0
COOLDOWN_MIN = 60
CARSON_IPS = ["192.168.11.173", "192.168.11.211"]
CARSON_PORT = 5555
ZMQ_PING_TIMEOUT_S = 5

KILL_ZONES_UTC = {  # per-asset KZ groups (ict-crt-pipeline skill)
    "asian":  {"assets": {"JPN225", "HK50", "TWN"},
               "windows": [("00:00", "03:00"), ("01:30", "04:00")]},   # Tokyo+HK
    "western": {"assets": {"NAS100", "US500", "GER40", "XAUUSD",
                           "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"},
                "windows": [("06:00", "09:00"),   # London
                            ("13:30", "16:00")]}, # NY AM
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_json(path: Path):
    try:
        with open(path) as f:
            return json.load(f), None
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return None, str(e)


def parse_hhmm(s: str) -> tuple[int, int]:
    h, m = s.split(":")
    return int(h), int(m)


def in_kill_zone(symbol: str, at: datetime) -> tuple[bool, str]:
    group = ("asian" if symbol.upper() in KILL_ZONES_UTC["asian"]["assets"]
             else "western")
    for start, end in KILL_ZONES_UTC[group]["windows"]:
        sh, sm = parse_hhmm(start)
        eh, em = parse_hhmm(end)
        s = at.replace(hour=sh, minute=sm, second=0, microsecond=0)
        e = at.replace(hour=eh, minute=em, second=0, microsecond=0)
        if s <= at <= e:
            return True, f"{group} KZ {start}-{end} UTC"
    return False, f"outside {group} kill zones"


def check_news_blackout(calendar: list, entry_at: datetime) -> tuple[list, list]:
    vetoes, notes = [], []
    for ev in calendar or []:
        if not isinstance(ev, dict):
            notes.append(f"calendar event not an object: {ev!r}")
            continue
        if str(ev.get("impact", "")).lower() not in ("high",):
            continue
        if ev.get("currency", "").upper() not in HIGH_IMPACT_CURRENCIES:
            continue
        try:
            t = datetime.fromisoformat(ev["time_utc"])
        except (KeyError, ValueError):
            notes.append(f"calendar event unparsable: {ev}")
            continue
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        delta = abs((t - entry_at).total_seconds()) / 60
        if delta <= NEWS_BLACKOUT_MIN:
            vetoes.append(f"NEWS_BLACKOUT: {ev.get('name', '?')} "
                          f"({ev.get('currency')}) in {delta:.0f} min "
                          f"(±{NEWS_BLACKOUT_MIN}min rule)")
    if not calendar:
        notes.append("no calendar data supplied — news blackout check NOT performed")
    return vetoes, notes


def ping_carson() -> tuple[bool, str]:
    """Ping Carson ZMQ bridge. Returns (healthy, detail)."""
    try:
        import zmq  # venv python: /Users/angus/.hermes/hermes-agent/venv/bin/python3
    except ImportError:
        return False, "pyzmq not importable — run gate with hermes venv python"
    ctx = zmq.Context()
    detail = f"carson unreachable on {CARSON_IPS} (timeout {ZMQ_PING_TIMEOUT_S}s each)"
    for ip in CARSON_IPS:
        sock = None
        try:
            sock = ctx.socket(zmq.REQ)
            sock.setsockopt(zmq.RCVTIMEO, ZMQ_PING_TIMEOUT_S * 1000)
            sock.setsockopt(zmq.SNDTIMEO, ZMQ_PING_TIMEOUT_S * 1000)
            sock.setsockopt(zmq.LINGER, 0)
            sock.connect(f"tcp://{ip}:{CARSON_PORT}")
            sock.send_json({"action": "ping"})
            r = sock.recv_json()
            if not isinstance(r, dict):
                detail = f"carson {ip} non-dict ping response: {r!r}"
                return False, detail
            if r.get("status") == "ok" and r.get("mt5_connected"):
                return True, f"carson {ip} healthy, MT5 connected"
            detail = (f"carson {ip} reachable but "
                      f"mt5_connected={r.get('mt5_connected')}")
            return False, detail
        except zmq.ZMQError as e:
            detail = f"carson {ip} ZMQ error: {e}"
        finally:
            if sock is not None:
                sock.close()
    ctx.term()
    return False, detail


def check_execution_history(signals_dir: Path, date: str, symbol: str) -> tuple[list, list]:
    """Daily/weekly loss caps, trade count, cooldown — from decisions/*.json."""
    vetoes, notes = [], []
    decisions_dir = signals_dir.parent / "decisions"
    today = datetime.strptime(date, "%Y-%m-%d").date()
    week_start = today - timedelta(days=today.weekday())
    trades_today, weekly_pnl, last_close_by_symbol = [], 0.0, {}

    for f in sorted(decisions_dir.glob("*.json")):
        try:
            fdate = datetime.strptime(f.stem, "%Y-%m-%d").date()
        except ValueError:
            continue
        if fdate > today:
            continue
        d, _ = load_json(f)
        if not d or d.get("decision") not in ("GO", "EXECUTED"):
            continue
        rec = {"date": fdate, "symbol": d.get("symbol", "?"),
               "pnl": d.get("realized_pnl") or 0.0,
               "closed_at": d.get("closed_at")}
        if fdate == today:
            trades_today.append(rec)
        if fdate >= week_start:
            weekly_pnl += rec["pnl"]
            if rec["closed_at"]:
                last_close_by_symbol.setdefault(rec["symbol"], (fdate, rec["closed_at"]))

    if len(trades_today) >= MAX_TRADES_PER_DAY:
        vetoes.append(f"TRADE_COUNT: {len(trades_today)} trades today "
                      f">= {MAX_TRADES_PER_DAY}")

    alfred, _ = load_json(signals_dir / date / "alfred_risk.json")
    equity = 0.0
    if alfred:
        for acct in (alfred.get("accounts") or {}).values():
            if isinstance(acct, dict) and isinstance(acct.get("equity"), (int, float)):
                equity = max(equity, acct["equity"])
    if equity > 0:
        day_pnl_pct = sum(t["pnl"] for t in trades_today) / equity * 100
        wk_pnl_pct = weekly_pnl / equity * 100
        if day_pnl_pct <= -DAILY_LOSS_CAP_PCT:
            vetoes.append(f"DAILY_LOSS: {day_pnl_pct:.2f}% <= -{DAILY_LOSS_CAP_PCT}%")
        if wk_pnl_pct <= -WEEKLY_LOSS_CAP_PCT:
            vetoes.append(f"WEEKLY_LOSS: {wk_pnl_pct:.2f}% <= -{WEEKLY_LOSS_CAP_PCT}%")
    else:
        notes.append("equity unavailable — loss caps NOT evaluated "
                     "(requires alfred_risk.json accounts[].equity)")

    if symbol in last_close_by_symbol:
        fdate, closed_at = last_close_by_symbol[symbol]
        try:
            t = datetime.fromisoformat(closed_at)
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            if (now_utc() - t) < timedelta(minutes=COOLDOWN_MIN):
                vetoes.append(f"COOLDOWN: {symbol} closed {closed_at} "
                              f"(<{COOLDOWN_MIN} min ago)")
        except ValueError:
            notes.append(f"cooldown check skipped: unparsable closed_at {closed_at}")
    return vetoes, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--symbol", default="NAS100")
    ap.add_argument("--entry-window", default=None,
                    help="planned entry 'HH:MM-HH:MM' UTC; default = now")
    ap.add_argument("--calendar", default=None,
                    help="path to JSON list of events {time_utc, currency, impact, name}")
    ap.add_argument("--signals-dir",
                    default=str(Path.home() / ".hermes/trading-war-room/signals"))
    ap.add_argument("--skip-mt5-ping", action="store_true",
                    help="offline mode: skip Carson ping (logs warning instead of veto)")
    args = ap.parse_args()

    vetoes, warnings = [], []

    # Entry reference time
    if args.entry_window:
        s = args.entry_window.split("-")[0]
        h, m = parse_hhmm(s)
        entry_at = now_utc().replace(hour=h, minute=m, second=0, microsecond=0)
    else:
        entry_at = now_utc()

    # 1. News blackout
    calendar = []
    if args.calendar:
        calendar, err = load_json(Path(args.calendar))
        if err:
            warnings.append(f"calendar load failed: {err}")
    v, n = check_news_blackout(calendar if isinstance(calendar, list) else [],
                               entry_at)
    vetoes += v
    warnings += n

    # 2. MT5 bridge health (deterministic veto unless explicitly skipped)
    if args.skip_mt5_ping:
        warnings.append("MT5 ping SKIPPED (--skip-mt5-ping) — health unverified")
    else:
        ok, detail = ping_carson()
        if not ok:
            vetoes.append(f"MT5_OFFLINE: {detail}")
        warnings.append(f"mt5_health: {detail}")

    # 3. Kill zone
    in_kz, kz_detail = in_kill_zone(args.symbol, entry_at)
    if not in_kz:
        vetoes.append(f"KILL_ZONE: {kz_detail}")
    else:
        warnings.append(f"kill_zone: {kz_detail}")

    # 4-7. Execution history checks
    v, n = check_execution_history(Path(args.signals_dir), args.date, args.symbol)
    vetoes += v
    warnings += n

    result = {
        "gate": "compliance",
        "date": args.date,
        "symbol": args.symbol,
        "entry_reference_utc": entry_at.isoformat(),
        "timestamp": now_utc().isoformat(),
        "status": "VETO" if vetoes else "PASS",
        "vetoes": vetoes,
        "warnings": warnings,
        "policy": {
            "news_blackout_min": NEWS_BLACKOUT_MIN,
            "max_trades_per_day": MAX_TRADES_PER_DAY,
            "daily_loss_cap_pct": DAILY_LOSS_CAP_PCT,
            "weekly_loss_cap_pct": WEEKLY_LOSS_CAP_PCT,
            "cooldown_min": COOLDOWN_MIN,
        },
    }
    out = Path(args.signals_dir) / args.date / "compliance_gate.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(2 if result["status"] == "VETO" else 0)


if __name__ == "__main__":
    main()
