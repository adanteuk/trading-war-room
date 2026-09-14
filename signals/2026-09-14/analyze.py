#!/usr/bin/env python3
"""Walker 3-layer ICT/CRT analysis for NAS100 — 2026-09-14 (Monday, HKT)."""
import json, os, datetime, math

DIR = "/Users/ychen/.hermes/trading-war-room/signals/2026-09-14"

def load(key):
    with open(f"{DIR}/raw_{key}.json") as f:
        return json.load(f)

def fmt(bar, tf):
    """Return (date_str, o,h,l,c) — D1 bars carry session-open stamps (21:00/22:00 UTC) so +1 day; H4/M15 raw."""
    tu = bar.get("time_utc") or datetime.datetime.utcfromtimestamp(bar["time_epoch"]).isoformat()
    dt = datetime.datetime.fromisoformat(tu.replace("Z", "+00:00"))
    if tf == "D1":
        dt = dt + datetime.timedelta(days=1)  # pitfall #49: CFD D1 session-open stamp -> session calendar day
    return dt.strftime("%Y-%m-%d"), float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])

def series(key, tf):
    bars = load(key)
    out = []
    for b in bars:
        d, o, h, l, c = fmt(b, tf)
        out.append({"date": d, "o": o, "h": h, "l": l, "c": c})
    return out

nas_d1 = series("NAS100_D1", "D1")
nas_h4 = series("NAS100_H4", "H4")
nas_m15 = series("NAS100_M15", "M15")
us_d1 = series("US500_D1", "D1")

print("=" * 70)
print(f"NAS100 D1: {len(nas_d1)} bars. Last 12 bars (date corrected):")
for b in nas_d1[-12:]:
    body = b['c'] - b['o']
    print(f"  {b['date']} O={b['o']:.1f} H={b['h']:.1f} L={b['l']:.1f} C={b['c']:.1f} body={body:+.1f}")

# --- dedupe by date (in-progress Monday bar may duplicate) ---
seen = {}
for b in nas_d1:
    seen[b["date"]] = b
uniq_d1 = list(seen.values())

# --- swing points D1 (5-bar lookback) ---
def swings(s, lb=3):
    highs, lows = [], []
    for i in range(lb, len(s) - lb):
        win_h = [x["h"] for x in s[i-lb:i+lb+1]]
        win_l = [x["l"] for x in s[i-lb:i+lb+1]]
        if s[i]["h"] == max(win_h) and win_h.count(s[i]["h"]) == 1:
            highs.append((s[i]["date"], s[i]["h"]))
        if s[i]["l"] == min(win_l) and win_l.count(s[i]["l"]) == 1:
            lows.append((s[i]["date"], s[i]["l"]))
    return highs, lows

sh, sl = swings(uniq_d1, 3)
print("\nD1 swing highs (last 8):", [(d, round(v,1)) for d, v in sh[-8:]])
print("D1 swing lows (last 8):", [(d, round(v,1)) for d, v in sl[-8:]])

# --- dealing range: most recent expansion swing ---
last = uniq_d1[-1]
print(f"\nCurrent (Monday in-progress) bar: {last['date']} O={last['o']} H={last['h']} L={last['l']} C={last['c']}")
completed = uniq_d1[:-1]
fri = completed[-1]
print(f"Last completed D1 (Friday): {fri['date']} O={fri['o']} H={fri['h']} L={fri['l']} C={fri['c']}")

# find most recent major swing high and swing low from swing lists
recent_sh = sh[-6:]
recent_sl = sl[-6:]
dr_high_date, dr_high = recent_sh[-1]
dr_low_date, dr_low = recent_sl[-1]
print(f"\nRecent swing high: {dr_high_date} {dr_high:.1f}")
print(f"Recent swing low: {dr_low_date} {dr_low:.1f}")

# --- Fib levels on dealing range ---
rng = dr_high - dr_low
fr = {0: dr_low, 100: dr_high}
for p in [25, 50, 62, 70.5, 79]:
    fr[p] = dr_high - (p / 100) * rng
print(f"\nDealing Range: {dr_low:.1f} ({dr_low_date}) -> {dr_high:.1f} ({dr_high_date}) = {rng:.1f} pts")
print("Fib levels (retracement from high):")
for p in [0, 25, 50, 62, 70.5, 79, 100]:
    print(f"  {p}%: {fr[p]:.1f}")

px = last["c"]
eq = (dr_high + dr_low) / 2
pos = (px - dr_low) / rng * 100
print(f"\nCurrent price {px:.1f} — range position {pos:.1f}% ({'PREMIUM' if pos > 50 else 'DISCOUNT'}), EQ={eq:.1f}")

# --- market structure last 6 completed bars: HH/HL vs LH/LL ---
print("\nStructure transitions (last 8 completed bars vs prior):")
for i in range(len(completed) - 8, len(completed)):
    cur, prev = completed[i], completed[i-1]
    hh = cur["h"] > prev["h"]; ll = cur["l"] < prev["l"]
    hl = cur["l"] > prev["l"]; lh = cur["h"] < prev["h"]
    tags = []
    if hh: tags.append("HH")
    if lh: tags.append("LH")
    if hl: tags.append("HL")
    if ll: tags.append("LL")
    print(f"  {cur['date']}: {'+'.join(tags) if tags else 'outside'}  H={cur['h']:.1f} L={cur['l']:.1f}")

# --- Friday candle deconstruction ---
o, h, l, c = fri["o"], fri["h"], fri["l"], fri["c"]
body = c - o; upper = h - max(o, c); lower = min(o, c) - l
rngf = h - l
print(f"\nFriday candle: body={body:+.1f} ({body/rngf*100:.0f}% of range), upper wick={upper:.1f}, lower wick={lower:.1f}, close pos={(c-l)/rngf*100:.0f}% of range")

# --- SMT: NAS100 vs US500 recent swing highs/lows ---
us_uniq = {}
for b in us_d1:
    us_uniq[b["date"]] = b
us = list(us_uniq.values())
ush, usl = swings(us, 3)
print("\nUS500 D1 swing highs (last 5):", [(d, round(v,1)) for d, v in ush[-5:]])
print("US500 D1 swing lows (last 5):", [(d, round(v,1)) for d, v in usl[-5:]])

# --- H4 analysis ---
print("\n" + "=" * 70)
print(f"NAS100 H4: {len(nas_h4)} bars. Last 14 bars:")
for b in nas_h4[-14:]:
    print(f"  {b['date']} O={b['o']:.1f} H={b['h']:.1f} L={b['l']:.1f} C={b['c']:.1f}")

h4h, h4l = swings(nas_h4[:-1], 4)  # swings on completed H4 bars
print("\nH4 swing highs (last 6):", [(d, round(v,1)) for d, v in h4h[-6:]])
print("H4 swing lows (last 6):", [(d, round(v,1)) for d, v in h4l[-6:]])

# --- H4 FVG detection (3-candle imbalance) ---
def fvgs(s, lookback=40):
    out = []
    for i in range(2, len(s)):
        c1, c3 = s[i-2], s[i]
        if c3["l"] > c1["h"]:  # bullish FVG
            out.append({"type": "bull", "from_date": s[i-2]["date"], "top": c3["l"], "bot": c1["h"], "mid": (c3["l"]+c1["h"])/2})
        if c3["h"] < c1["l"]:  # bearish FVG
            out.append({"type": "bear", "from_date": s[i-2]["date"], "top": c1["l"], "bot": c3["h"], "mid": (c3["h"]+c1["l"])/2})
    return out

h4_fvgs = fvgs(nas_h4)
print("\nH4 FVGs (all, chronological):")
for f in h4_fvgs:
    filled = "FILLED" if (f["type"] == "bull" and nas_h4[-1]["l"] <= f["bot"]) or (f["type"] == "bear" and nas_h4[-1]["h"] >= f["top"]) else ("PARTIAL" if (f["type"]=="bull" and nas_h4[-1]["l"] <= f["mid"]) or (f["type"]=="bear" and nas_h4[-1]["h"] >= f["mid"]) else "OPEN")
    print(f"  {f['type'].upper()} {f['from_date']} zone {f['bot']:.1f}-{f['top']:.1f} mid={f['mid']:.1f} [{filled}]")

# --- H4 dealing range ---
print("\nH4 recent expansion: swing high", h4h[-1] if h4h else None, "swing low", h4l[-1] if h4l else None)

# --- M15 recent action ---
print("\n" + "=" * 70)
print(f"NAS100 M15: {len(nas_m15)} bars. Last 20 bars:")
for b in nas_m15[-20:]:
    print(f"  {b['date']} O={b['o']:.1f} H={b['h']:.1f} L={b['l']:.1f} C={b['c']:.1f}")

# session high/low for Monday so far (all M15 bars of today)
todays = [b for b in nas_m15 if b["date"] == "2026-09-14"]
if todays:
    print(f"\nMonday Sep 14 so far (M15): H={max(b['h'] for b in todays):.1f} L={min(b['l'] for b in todays):.1f}, first open={todays[0]['o']:.1f}, n={len(todays)}")

# overnight H/L from H4 bars of today
todays_h4 = [b for b in nas_h4 if b["date"] == "2026-09-14"]
if todays_h4:
    print(f"Monday Sep 14 H4 bars: {len(todays_h4)}, H={max(b['h'] for b in todays_h4):.1f} L={min(b['l'] for b in todays_h4):.1f}")

# Friday H4 for CRT frame
fri_h4 = [b for b in nas_h4 if b["date"] == "2026-09-11"]
print(f"Friday H4 bars: {len(fri_h4)}")
for b in fri_h4:
    print(f"  {b['date']} O={b['o']:.1f} H={b['h']:.1f} L={b['l']:.1f} C={b['c']:.1f}")
