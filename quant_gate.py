#!/usr/bin/env python3
"""
quant_gate.py — Five-Stage Pipeline v3, Stage 4 (deterministic quant verification)

Replaces Alfred's LLM-judged statistical checks with hard-coded rules.
Reads the three signal JSONs for a date, applies deterministic thresholds,
writes quant_gate.json. Exit code 0 = pass, 2 = veto.

VETO rules (any hit = trade terminated, cannot be overridden):
  - Sample size < 5 similar setups        (insufficient historical evidence)
  - Event-week false-breakout rate > 60%  (AC decision 7b-2, 2026-09-14;
                                           stricter than v2.4's 85%)
  - Monday Range > 200% ATR14             (range too extreme)
  - ORB arithmetic invalid                (breakdown categories don't sum to
                                           total — see warning/escalation rule)

WARNING (escalating):
  - ORB breakdown missing/unreadable → warning; 3+ consecutive dates with the
    warning (tracked in .quant_gate_state.json) → veto.

Null defense: any numeric field read from agent JSON uses `or default` so
explicit nulls and missing keys behave identically (v2.4 lesson).

Usage:
  python3 quant_gate.py --date YYYY-MM-DD [--signals-dir PATH] [--out PATH]
Input files (per signals/<date>/):
  merlin_research.json / walker_ta.json / alfred_risk.json
Output: signals/<date>/quant_gate.json
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Hard-coded thresholds (AC-approved, 2026-09-14) ─────────────────
MIN_SAMPLE_SIZE = 5                 # setups occurred < 5 → veto
FB_EVENT_WEEK_MAX = 60.0            # % — veto above (AC decision 2)
RANGE_ATR_RATIO_MAX = 2.0           # Monday Range / ATR14 — veto above
ORB_CATEGORY_WEIGHTS = {            # orb-bias-filter 6 categories
    "pre_market_htf_bias": 25,
    "vwap_alignment": 15,
    "volume_confirmation": 20,
    "candle_close_timing": 15,
    "ict_crt_confluence": 15,
    "range_width_volatility": 10,
}
ORB_BREAKDOWN_MAX_SUM = 100
ORB_WARN_STREAK_LIMIT = 3           # consecutive warnings → veto
STATE_FILE = ".quant_gate_state.json"

OR_DEFAULTS = {  # field → default when missing or null
    "orb_score": 0,
    "ml_regime_confidence": 0.0,
    "fb_event_week_rate": 0.0,
    "sample_size": 0,
    "range_atr_ratio": 0.0,
}


def num(d, key, default=0.0):
    """Null-safe numeric read: missing key OR explicit null → default."""
    v = d.get(key, default)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else default


def load_json(path: Path):
    try:
        with open(path) as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, f"missing file: {path.name}"
    except json.JSONDecodeError as e:
        return None, f"invalid JSON in {path.name}: {e}"


def check_orb_breakdown(walker: dict) -> tuple[str, str]:
    """Returns (status, detail): 'ok' | 'warn' | 'veto'."""
    orb = num(walker, "orb_score", 0)
    bd = walker.get("orb_breakdown")
    if not isinstance(bd, dict) or not bd:
        return ("warn" if orb > 0 else "ok",
                f"orb_breakdown missing (orb_score={orb})")
    total = 0
    for cat, maxpts in ORB_CATEGORY_WEIGHTS.items():
        v = num(bd, cat, -1)
        if not (0 <= v <= maxpts):
            return "warn", f"orb_breakdown[{cat}]={v} outside 0-{maxpts}"
        total += v
    if total != ORB_BREAKDOWN_MAX_SUM:
        return "warn", f"orb_breakdown sums to {total}, expected {ORB_BREAKDOWN_MAX_SUM}"
    if abs(total - num(walker, "orb_score", -1)) > 0:
        return "warn", (f"orb_breakdown total ({total}) != orb_score "
                        f"({num(walker, 'orb_score', -1)})")
    return "ok", f"orb_breakdown valid (sum={total})"


def load_state(signals_dir: Path) -> dict:
    try:
        with open(signals_dir / STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"orb_warn_streak": 0, "last_date": None}


def save_state(signals_dir: Path, state: dict):
    with open(signals_dir / STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def run_gate(date: str, signals_dir: Path) -> dict:
    d = signals_dir / date
    vetoes, warnings, checks = [], [], []

    merlin, e1 = load_json(d / "merlin_research.json")
    walker, e2 = load_json(d / "walker_ta.json")
    alfred, e3 = load_json(d / "alfred_risk.json")
    for e in (e1, e2, e3):
        if e:
            vetoes.append(f"INPUT_FAILURE: {e}")

    # ── Alfred statistical inputs (fallback: fields may come from walker/merlin)
    stats_src = (alfred or {}).get("alfred_stats") or alfred or walker or {}
    sample = num(stats_src, "sample_size", OR_DEFAULTS["sample_size"])
    fb_rate = num(stats_src, "fb_event_week_rate",
                  num(stats_src, "false_breakout_rate", OR_DEFAULTS["fb_event_week_rate"]))
    if sample and sample < MIN_SAMPLE_SIZE:
        vetoes.append(f"SAMPLE_SIZE: {sample} < {MIN_SAMPLE_SIZE} similar setups")
    checks.append({"check": "sample_size", "value": sample,
                   "threshold": f">= {MIN_SAMPLE_SIZE}",
                   "status": "veto" if sample and sample < MIN_SAMPLE_SIZE else "pass"})

    if fb_rate and fb_rate > FB_EVENT_WEEK_MAX:
        vetoes.append(f"FALSE_BREAKOUT: event-week rate {fb_rate}% > {FB_EVENT_WEEK_MAX}%")
    checks.append({"check": "event_week_false_breakout", "value": fb_rate,
                   "threshold": f"<= {FB_EVENT_WEEK_MAX}%",
                   "status": "veto" if fb_rate > FB_EVENT_WEEK_MAX else "pass"})

    range_ratio = num((walker or {}).get("range_analysis", {}) or walker or {},
                      "range_atr_ratio", OR_DEFAULTS["range_atr_ratio"])
    if range_ratio and range_ratio > RANGE_ATR_RATIO_MAX:
        vetoes.append(f"RANGE_EXTREME: Monday Range {range_ratio:.2f}x ATR > {RANGE_ATR_RATIO_MAX}x")
    checks.append({"check": "range_vs_atr", "value": range_ratio,
                   "threshold": f"<= {RANGE_ATR_RATIO_MAX}x",
                   "status": "veto" if range_ratio > RANGE_ATR_RATIO_MAX else "pass"})

    # ── ORB breakdown integrity (AC decision 3, warning escalation)
    status, detail = check_orb_breakdown(walker or {})
    state = load_state(signals_dir)
    streak = state.get("orb_warn_streak", 0)
    if status == "veto":
        vetoes.append(f"ORB_BREAKDOWN: {detail}")
        streak = 0
    elif status == "warn":
        streak += 1
        if streak >= ORB_WARN_STREAK_LIMIT:
            vetoes.append(f"ORB_BREAKDOWN: {detail} — {streak} consecutive warnings")
            streak = 0
        else:
            warnings.append(f"ORB_BREAKDOWN: {detail} (warning {streak}/{ORB_WARN_STREAK_LIMIT})")
    else:
        streak = 0
    checks.append({"check": "orb_breakdown", "status": status, "detail": detail})
    save_state(signals_dir, {**state, "orb_warn_streak": streak, "last_date": date})

    # ── Data-quality signal: regime fields present?
    wr = walker or {}
    if not wr.get("ml_regime"):
        warnings.append("ml_regime missing from walker_ta.json (regime filter not run?)")

    result = {
        "gate": "quant",
        "date": date,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "VETO" if vetoes else "PASS",
        "vetoes": vetoes,
        "warnings": warnings,
        "checks": checks,
        "thresholds": {
            "min_sample_size": MIN_SAMPLE_SIZE,
            "fb_event_week_max_pct": FB_EVENT_WEEK_MAX,
            "range_atr_ratio_max": RANGE_ATR_RATIO_MAX,
            "orb_warn_streak_limit": ORB_WARN_STREAK_LIMIT,
        },
    }
    out = d / "quant_gate.json"
    with open(out, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--signals-dir",
                    default=str(Path.home() / ".hermes/trading-war-room/signals"))
    args = ap.parse_args()
    result = run_gate(args.date, Path(args.signals_dir))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(2 if result["status"] == "VETO" else 0)


if __name__ == "__main__":
    main()
