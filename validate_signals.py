#!/usr/bin/env python3
"""
validate_signals.py — v3 Phase 2: signal contract schema checker

Validates the three signal JSONs against the v3 contracts BEFORE the gates
and orchestrator consume them. Catches contract drift at the source (e.g.
orb_breakdown missing, regime fields absent, null numerics, non-float levels).

Usage:
  python3 validate_signals.py --date YYYY-MM-DD [--signals-dir PATH] [--strict]

Output: signals/<date>/validation_report.json + human-readable summary.
Exit codes: 0 = all pass (warnings allowed), 3 = failures found (--strict: exit 3 on warnings too)

Field policy (v3 contracts, Walker followup 2026-09-13):
  - walker_ta.json: bias, confidence, orb_score+orb_breakdown (6 cats),
    ml_regime/regime_confidence/regime_probs, conditional_triggers,
    entry/sl/tp as exact floats when present
  - alfred_risk.json: timestamp, go_no_go, veto, recommended_lot_size always;
    factors/accounts may be absent (null-safe downstream)
  - merlin_research.json: summary (≤200 chars for Discord), bias, confidence,
    risks, recommendation
  - Universal: NO explicit nulls on numeric fields (omit instead — the
    orchestrator's `or default` defense treats null as 0/placeholder)
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ORB_CATEGORIES = {
    "pre_market_htf_bias": 25, "vwap_alignment": 15, "volume_confirmation": 20,
    "candle_close_timing": 15, "ict_crt_confluence": 15, "range_width_volatility": 10,
}
REGIMES = {"TREND", "RANGE", "HIGH_VOL"}
TRIGGER_CONDITIONS = {"close_below", "close_above", "reclaim_above", "reclaim_below",
                      "break_above", "break_below"}
TRIGGER_ACTIONS = {"bullish_active", "bearish_active", "bullish_invalidated",
                   "bearish_invalidated"}
DISCORD_MAX_SUMMARY = 200


def is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_file(path: Path) -> tuple[dict | None, str]:
    if not path.exists():
        return None, "MISSING"
    try:
        with open(path) as f:
            return json.load(f), "ok"
    except json.JSONDecodeError as e:
        return None, f"INVALID_JSON: {e}"


def find_null_numerics(obj, prefix="") -> list:
    """Any explicit null on a field that looks numeric-ish (score, level, price, pct...)."""
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else k
            if v is None:
                hits.append(key)
            elif isinstance(v, (dict, list)):
                hits += find_null_numerics(v, key)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits += find_null_numerics(v, f"{prefix}[{i}]")
    return hits


def validate_walker(d: dict) -> tuple[list, list, list]:
    fails, warns, oks = [], [], []

    for f in ("bias", "confidence"):
        if f not in d:
            fails.append(f"walker: missing required field '{f}'")
    if "bias" in d and d["bias"] not in ("bullish", "bearish", "neutral",
                                         "Bullish", "Bearish", "Neutral"):
        fails.append(f"walker: bias='{d['bias']}' not in bullish/bearish/neutral")
    if "confidence" in d and not (is_num(d["confidence"]) and 0 <= d["confidence"] <= 100):
        fails.append(f"walker: confidence={d['confidence']} not numeric 0-100")

    # entry/sl/tp: when present must be exact floats (Walker contract)
    for f in ("entry", "sl", "tp"):
        v = d.get(f)
        if v is not None and v != "TBD" and not is_num(v):
            fails.append(f"walker: {f}={v!r} must be exact float or 'TBD'/omitted")

    # ORB + breakdown
    orb = d.get("orb_score")
    orb_ok = is_num(orb)
    if orb_ok:
        orb_ok = 0 <= orb <= 100  # type: ignore[operator]
    if orb is not None and not orb_ok:
        fails.append(f"walker: orb_score={orb} not numeric 0-100")
    bd = d.get("orb_breakdown")
    if bd is None:
        if is_num(orb) and orb > 0:
            warns.append("walker: orb_breakdown missing while orb_score>0 "
                         "(warning 1 of 3 before quant-gate veto)")
        else:
            oks.append("walker: orb_breakdown omitted with no score (pre-open) — ok")
    elif isinstance(bd, dict):
        total, bad = 0, []
        for cat, mx in ORB_CATEGORIES.items():
            v = bd.get(cat)
            if not is_num(v) or not (0 <= v <= mx):
                bad.append(f"{cat}={v}")
            else:
                total += v
        if bad:
            warns.append(f"walker: orb_breakdown invalid categories: {', '.join(bad)}")
        elif total != 100:
            warns.append(f"walker: orb_breakdown sums to {total}, expected 100")
        elif orb_ok and total != orb:
            warns.append(f"walker: orb_breakdown total {total} != orb_score {orb}")
        else:
            oks.append(f"walker: orb_breakdown valid (sum={total})")
    else:
        fails.append("walker: orb_breakdown present but not an object")

    # Regime fields (mandatory from Phase 2)
    regime = d.get("ml_regime")
    if regime is None:
        warns.append("walker: ml_regime missing (contract-mandatory from Phase 2)")
    elif regime not in REGIMES:
        fails.append(f"walker: ml_regime='{regime}' not in {sorted(REGIMES)}")
    else:
        regime_problems = []
        rc = d.get("regime_confidence")
        rp = d.get("regime_probs")
        if not is_num(rc) or not (0 <= rc <= 1):
            regime_problems.append(f"regime_confidence={rc} missing/invalid (0-1)")
        probs_ok = isinstance(rp, dict) and set(rp) == REGIMES and \
            all(is_num(v) and 0 <= v <= 1 for v in rp.values())
        if not probs_ok:
            regime_problems.append("regime_probs missing/invalid (need all 3 classes, 0-1)")
        elif abs(sum(rp.values()) - 1.0) > 0.02:
            regime_problems.append(f"regime_probs sum {sum(rp.values()):.3f} != 1.0")
        if probs_ok and is_num(rc):
            probs = rp if isinstance(rp, dict) else {}
            if abs(rc - probs[regime]) > 0.02:
                regime_problems.append(
                    f"regime_confidence {rc} != regime_probs['{regime}'] {probs[regime]}")
        if regime_problems:
            warns.extend(f"walker: {p}" for p in regime_problems)
        else:
            oks.append(f"walker: regime fields valid ({regime})")

    # Conditional triggers
    ct = d.get("conditional_triggers")
    if ct is None:
        warns.append("walker: conditional_triggers missing (contract-mandatory)")
    elif not isinstance(ct, list) or not (1 <= len(ct) <= 6):
        fails.append("walker: conditional_triggers must be a list of 1-6 objects")
    else:
        for i, t in enumerate(ct):
            if not isinstance(t, dict):
                fails.append(f"walker: conditional_triggers[{i}] not an object")
                continue
            for f in ("condition", "timeframe", "level", "action"):
                if f not in t:
                    fails.append(f"walker: conditional_triggers[{i}] missing '{f}'")
            if t.get("condition") not in TRIGGER_CONDITIONS:
                fails.append(f"walker: trigger[{i}].condition='{t.get('condition')}' "
                             f"not in {sorted(TRIGGER_CONDITIONS)}")
            if t.get("action") not in TRIGGER_ACTIONS:
                fails.append(f"walker: trigger[{i}].action='{t.get('action')}' "
                             f"not in {sorted(TRIGGER_ACTIONS)}")
            if not is_num(t.get("level")):
                fails.append(f"walker: trigger[{i}].level must be exact float "
                             f"(got {t.get('level')!r})")
            tg = t.get("targets")
            if tg is not None and (not isinstance(tg, list) or
                                   not all(is_num(x) for x in tg)):
                fails.append(f"walker: trigger[{i}].targets must be list of floats")
        if not any(f.startswith("walker: trigger[") or f.startswith("walker: conditional") 
                   for f in fails):
            oks.append(f"walker: {len(ct)} conditional_triggers valid")

    # Null-numeric hygiene (universal rule)
    nulls = find_null_numerics({k: v for k, v in d.items()})
    if nulls:
        warns.append(f"walker: explicit nulls found — omit instead: {', '.join(nulls[:6])}")

    return fails, warns, oks


def validate_alfred(d: dict) -> tuple[list, list, list]:
    fails, warns, oks = [], [], []
    for f in ("go_no_go", "veto"):
        if f not in d:
            fails.append(f"alfred: missing required field '{f}'")
    if d.get("go_no_go") not in ("GO", "WAIT", "NO_GO", None):
        fails.append(f"alfred: go_no_go='{d.get('go_no_go')}' not GO/WAIT/NO_GO")
    if not isinstance(d.get("veto"), bool):
        fails.append(f"alfred: veto={d.get('veto')!r} must be boolean")
    if d.get("veto") is True and not d.get("veto_reason"):
        warns.append("alfred: veto=true but veto_reason empty (orchestrator needs it "
                     "for Discord #risk-check)")
    rls = d.get("recommended_lot_size")
    if rls is not None and not is_num(rls):
        warns.append(f"alfred: recommended_lot_size={rls!r} non-numeric "
                     "(ignored — sizing is scripted now)")
    accounts = d.get("accounts")
    if accounts:
        for name, acct in accounts.items():
            if isinstance(acct, dict) and acct.get("status") == "error":
                warns.append(f"alfred: account '{name}' status=error "
                             "(cannot-verify → expect NO_GO default)")
    oks.append("alfred: core contract ok" if not fails else "")
    return fails, warns, [o for o in oks if o]


def validate_merlin(d: dict) -> tuple[list, list, list]:
    fails, warns, oks = [], [], []
    for f in ("summary", "bias", "recommendation"):
        if f not in d:
            fails.append(f"merlin: missing required field '{f}'")
    s = d.get("summary", "")
    if isinstance(s, str) and len(s) > DISCORD_MAX_SUMMARY:
        warns.append(f"merlin: summary {len(s)} chars > {DISCORD_MAX_SUMMARY} "
                     "(Discord 2000-char risk — v2.4 lesson)")
    rec = d.get("recommendation", "")
    if rec and not any(k in str(rec).upper() for k in ("GO", "NO_GO", "WAIT")):
        warns.append(f"merlin: recommendation='{str(rec)[:40]}' lacks GO/NO_GO/WAIT")
    risks = d.get("risks")
    if risks is not None and isinstance(risks, list) and len(risks) > 3:
        warns.append(f"merlin: {len(risks)} risks (keep ≤3 short items for Discord)")
    return fails, warns, ["merlin: contract ok"] if not fails else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--signals-dir",
                    default=str(Path.home() / ".hermes/trading-war-room/signals"))
    ap.add_argument("--strict", action="store_true",
                    help="exit 3 on warnings too (for cron hard-fail mode)")
    args = ap.parse_args()

    day = Path(args.signals_dir) / args.date
    report = {"date": args.date,
              "timestamp": datetime.now(timezone.utc).isoformat(),
              "files": {}, "totals": {"fails": 0, "warns": 0}}

    validators = {
        "merlin_research.json": validate_merlin,
        "walker_ta.json": validate_walker,
        "alfred_risk.json": validate_alfred,
    }
    for fname, fn in validators.items():
        d, status = check_file(day / fname)
        if d is None:
            entry = {"exists": False, "status": status, "fails": [status] if status != "MISSING" else [],
                     "warns": [], "oks": []}
            if status != "MISSING":
                report["totals"]["fails"] += 1
            # Missing file is NOT a validation failure here — the gates already
            # veto on it. Validation reports on what exists.
            entry["fails"] = []
        else:
            f, w, o = fn(d)
            entry = {"exists": True, "status": "ok", "fails": f, "warns": w, "oks": o}
            report["totals"]["fails"] += len(f)
            report["totals"]["warns"] += len(w)
        report["files"][fname] = entry

    out = day / "validation_report.json"
    with open(out, "w") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    # Human summary
    print(f"=== Signal Validation — {args.date} ===")
    for fname, e in report["files"].items():
        icon = "✅" if e["exists"] and not e["fails"] and not e["warns"] else \
               "⚠️ " if e["exists"] and not e["fails"] else \
               "❌" if e["exists"] else "—"
        print(f"{icon} {fname}: {e['status']}"
              + (f" | {len(e['fails'])} fail, {len(e['warns'])} warn" if e["exists"] else ""))
        for x in e["fails"]:
            print(f"     FAIL: {x}")
        for x in e["warns"]:
            print(f"     WARN: {x}")
        for x in e.get("oks", []):
            print(f"     ok: {x}")
    print(f"\nTotals: {report['totals']['fails']} fails, {report['totals']['warns']} warns")
    print(f"Report: {out}")

    if report["totals"]["fails"]:
        sys.exit(3)
    if args.strict and report["totals"]["warns"]:
        sys.exit(3)
    sys.exit(0)


if __name__ == "__main__":
    main()
