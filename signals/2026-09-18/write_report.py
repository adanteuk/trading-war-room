#!/usr/bin/env python3
"""Final scoring + walker_ta.json — NAS100 2026-09-18, run ~18:40 HKT (06:40 NY).
CFD session = D1 bar starting 06:00 HKT (=22:00 UTC prev day). VWAP/RVOL on that anchor."""
import json, datetime

BASE = "/Users/ychen/.hermes/trading-war-room/signals/2026-09-18"
HKT = datetime.timezone(datetime.timedelta(hours=8))
m15 = json.load(open(f"{BASE}/raw_NAS100_M15.json"))
d1 = json.load(open(f"{BASE}/raw_NAS100_D1.json"))

SESSION_START = 1789682400  # 06:00 HKT Fri 2026-09-18 (CFD session open)
sess = [b for b in m15 if b["time"] >= SESSION_START]
print(f"Session bars (>=06:00 HKT): {len(sess)}")
s_open = sess[0]["open"]
s_hi = max(b["high"] for b in sess); s_lo = min(b["low"] for b in sess)
last_px = m15[-1]["close"]
print(f"Session O={s_open} H={s_hi} L={s_lo} last={last_px}")

# ---- Session VWAP ----
tpv = sum(((b["high"] + b["low"] + b["close"]) / 3) * b["volume"] for b in sess)
vv = sum(b["volume"] for b in sess)
vwap = tpv / vv
print(f"Session VWAP: {vwap:.1f} -> price {'ABOVE' if last_px > vwap else 'BELOW'} ({(last_px/vwap-1)*100:+.2f}%)")

# ---- RVOL: cumulative at same elapsed offset vs yesterday's session ----
Y_START = 1789596000  # 06:00 HKT Thu 2026-09-17
ysess = [b for b in m15 if Y_START <= b["time"] < SESSION_START]
elapsed = sess[-1]["time"] - sess[0]["time"] + 900
y_anchor = ysess[0]["time"]
ycum = sum(b["volume"] for b in ysess if b["time"] <= y_anchor + elapsed - 900)
scum = sum(b["volume"] for b in sess)
rvol = scum / ycum if ycum else 0
print(f"RVOL: today {scum} vs yesterday same-elapsed {ycum} = {rvol:.2f}")

# ---- Scoring ----
score = {}
score["pre_market_htf"] = 18  # D1 bullish displacement (82% body, close@87%), price above daily open, +0.74% session; BUT deep premium 87% of range
score["vwap"] = 12 if last_px > vwap else 4  # above rising session VWAP after displacement
score["volume"] = 15 if rvol >= 0.9 else (10 if rvol >= 0.75 else 5)
score["close_timing"] = 6  # no ORB close yet (cash opens 21:30 HKT); NY AM KZ starts 07:00 NY; no confirmed close outside range
score["ict_confluence"] = 8  # clear path + FVG support below; NO SMT divergence (both indices swept+reclaimed together); deep premium
score["range_vol"] = 7  # session range (s_hi-s_lo)/last_px
orb = sum(score.values())
print(f"ORB breakdown: {score} -> total {orb}")
print(f"Session range %: {(s_hi-s_lo)/last_px*100:.2f}%")

# Fib re-verification (independent recomputation)
sep_h, sep_l = 29734.1, 28757.0
rng = sep_h - sep_l
fib = {p: round(sep_l + rng * p / 100, 1) for p in [0, 25, 50, 62, 70.5, 79, 100]}
pos = (last_px - sep_l) / rng * 100
print(f"Fibs: {fib} | price at {pos:.1f}% of Sep range")

now = datetime.datetime.now(HKT)
report = {
    "timestamp": now.isoformat(),
    "data_source": "TradingView MCP PEPPERSTONE:NAS100 (Carson MT5 offline 2026-09-18); US500 D1 via MCP for SMT check",
    "bias": "bullish",
    "confidence": 55,
    "orb_score": orb,
    "ict_profile": "Wednesday Low Reversal -> Friday Continuation",
    "entry": "TBD — wait for NY AM KZ (07:00-10:00 NY); no confirmed entry, do not anticipate",
    "key_levels": {
        "support": ["29588 (M15 FVG)", "29529 (79% Fib)", "29436-29446 (daily open + 70.5% Fib)", "29359-29363 (H4 bull FVG top + 62% Fib)", "29245 (50% Fib)"],
        "resistance": ["29670 (H4 bear FVG floor, Aug 18)", "29734 (Sep 8 swing high)", "29749 (Aug 28 high, EQH pool)", "29962 (bear FVG upper)"]
    },
    "three_layer_analysis": {
        "l1_daily": "D1 structure transitioning bullish: Sep 10-15 LH+LL sequence broke when Sep 16 swept sell-side (low 28,757 under Sep 2 swing 28,882 and Sep 15 low 28,910), followed by Sep 17 displacement (545pt range, 82% body, close@87%) with HH+HL. Today extends: +0.47% session, price above daily open (29,435.6), 86% of September dealing range (28,757->29,734) = deep premium. Draw on liquidity: EQH pool 29,734-29,749 (Sep 8 + Aug 28 highs). Sep 17 close reclaimed 50%/62% Fibs.",
        "l2_h4_context": "H4 range 28,757.0 (Sep 16) <-> 29,734.1 (Sep 8), price at ~91% = premium. Open H4 bull FVG 29,252-29,359 (Sep 17 displacement, unfilled, mid-range). Overhead: bear FVG 29,670-29,962 (Aug 15->18 selloff) — today's high 29,677.7 just entered its floor; the EQH BSL sits inside it = 29,670-29,750 supply/liquidity confluence. CRT: last night's H4 candles purged the Thu range high; current 06:00 HKT H4 bar (O 29,435.6) expanding, upper wick probing the FVG.",
        "l3_m15_entry": "M15 bullish today: HH+HL sequence 10:15-14:45 to day high 29,677.7, shallow LH+LL pullback to 29,548 held above the FVG stack, reclaim gap 29,570.5-29,587.2 (18:00-18:15 candles) and reclaim to ~29,575-29,600. Support cluster below 29,547-29,612 (M15 gaps + London low 29,546.6). NY AM Kill Zone starts 07:00 NY (in ~10 min) — WAITING FOR KILL ZONE; no entry modeled, do not anticipate."
    },
    "reasoning": "Wednesday marked the weekly low (28,757) with a sell-side sweep; Thursday delivered bullish displacement and Friday continues into premium. SMT note: on Sep 15 NAS100 HELD its low (HL) while US500 swept (LL) — mild bullish SMT; Sep 16 both indices swept lows in sync and reclaimed together, so the divergence faded before the recovery. Bias bullish targeting the EQH buy-side pool 29,734-29,749, which sits inside the Aug 15->18 bear FVG (floor 29,670) — the natural draw and first area where a CRT-style rejection could form. Caveats that cap confidence at 55/100: (1) price already at ~86-87% of the September range = chasing premium, (2) SMT divergence was mild and pre-dated the move, not fresh at current price, (3) NY AM Kill Zone not yet active and no ORB close, (4) Friday PM liquidity often thins after the morning drive. Plan: wait for NY AM KZ; bullish continuation needs acceptance above 29,670; a sweep of 29,734-29,749 with rejection is the alternate short scenario back into the range — confirm on price action only. Not financial advice — analysis only.",
    "orb_breakdown": {
        "pre_market_htf_bias_25": score["pre_market_htf"],
        "vwap_15": score["vwap"],
        "volume_20": score["volume"],
        "close_timing_15": score["close_timing"],
        "ict_confluence_15": score["ict_confluence"],
        "range_volatility_10": score["range_vol"],
        "vwap_value": round(vwap, 1),
        "rvol_same_elapsed": round(rvol, 2)
    },
    "fib_levels_sep_range": fib,
    "price_position_pct": round(pos, 1),
    "session_stats": {"open": s_open, "high": s_hi, "low": s_lo, "last": last_px, "daily_open": s_open}
}
with open(f"{BASE}/walker_ta.json", "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print("walker_ta.json written")
