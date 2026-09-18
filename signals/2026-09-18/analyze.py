#!/usr/bin/env python3
"""Walker 3-Layer ICT/CRT analysis — NAS100 — 2026-09-18 (Friday), run 18:39 HKT.
Data: TradingView MCP PEPPERSTONE:NAS100 (Carson MT5 offline today).
D1=60 bars, H4=300, M15=300. CFD timestamps raw (no +1d shift, pitfall #68).
"""
import json, datetime

BASE = "/Users/ychen/.hermes/trading-war-room/signals/2026-09-18"
HKT = datetime.timezone(datetime.timedelta(hours=8))

d1 = json.load(open(f"{BASE}/raw_NAS100_D1.json"))
h4 = json.load(open(f"{BASE}/raw_NAS100_H4.json"))
m15 = json.load(open(f"{BASE}/raw_NAS100_M15.json"))

def date_of(b): return datetime.datetime.fromtimestamp(b["time"], HKT)

# ---------- helpers ----------
def swings(bars, lb=2):
    """Swing highs/lows with lookback lb (fractal)."""
    sh, sl = [], []
    for i in range(lb, len(bars) - lb):
        hs = [bars[j]["high"] for j in range(i - lb, i + lb + 1)]
        ls = [bars[j]["low"] for j in range(i - lb, i + lb + 1)]
        if bars[i]["high"] == max(hs) and bars[i]["high"] > max(hs[:lb] + hs[lb+1:]):
            sh.append((i, bars[i]))
        if bars[i]["low"] == min(ls) and bars[i]["low"] < min(ls[:lb] + ls[lb+1:]):
            sl.append((i, bars[i]))
    return sh, sl

completed_d1 = d1[:-1]  # exclude Friday in-progress
last_d1 = d1[-1]
prev_d1 = d1[-2]

print("=" * 70)
print("LAYER 1 — D1 DIRECTIONAL BIAS")
print("=" * 70)
# Structure: compare last 4 completed swings
sh, sl = swings(completed_d1, 2)
print(f"Recent swing highs: {[(date_of(b).strftime('%m-%d'), round(b['high'],1)) for _, b in sh[-4:]]}")
print(f"Recent swing lows : {[(date_of(b).strftime('%m-%d'), round(b['low'],1)) for _, b in sl[-4:]]}")

# Raw daily transitions last 6 completed days (pitfall #74: check H and L independently)
print("\nDay-over-day transitions (completed bars):")
for i in range(len(completed_d1) - 6, len(completed_d1)):
    cur, prv = completed_d1[i], completed_d1[i - 1]
    hh = cur["high"] > prv["high"]; ll = cur["low"] < prv["low"]
    hl = cur["low"] > prv["low"];  lh = cur["high"] < prv["high"]
    tag = ("HH" if hh else "LH") + "+" + ("HL" if hl else "LL")
    print(f"  {date_of(cur).strftime('%a %m-%d')}: {tag}  H={cur['high']:.1f} L={cur['low']:.1f} C={cur['close']:.1f}")

# Candle deconstruction of last 3 completed + today in progress
print("\nCandle deconstruction:")
for b in completed_d1[-3:] + [last_d1]:
    rng = b["high"] - b["low"]
    if rng == 0: continue
    body = abs(b["close"] - b["open"])
    close_pos = (b["close"] - b["low"]) / rng * 100
    upper_w = b["high"] - max(b["open"], b["close"])
    lower_w = min(b["open"], b["close"]) - b["low"]
    typ = "BULL" if b["close"] > b["open"] else "BEAR"
    status = "(in-progress)" if b is last_d1 else "(closed)"
    print(f"  {date_of(b).strftime('%a %m-%d')} {typ}: range={rng:.1f} body={body:.1f} ({body/rng*100:.0f}%) "
          f"close@{close_pos:.0f}% up-wick={upper_w:.1f} lo-wick={lower_w:.1f} {status}")

# Dealing range: structurally significant — Aug low to Sep high (pitfall #66: avoid same-day narrow range)
h_val = max(b["high"] for b in completed_d1)
l_val = min(b["low"] for b in completed_d1)
h_bar = max(completed_d1, key=lambda b: b["high"])
l_bar = min(completed_d1, key=lambda b: b["low"])
print(f"\n60-bar completed range: H {h_val:.1f} ({date_of(h_bar).strftime('%m-%d')})  L {l_val:.1f} ({date_of(l_bar).strftime('%m-%d')})")
# Recent expansion: Sep 11 low -> Sep high
sep_bars = [b for b in completed_d1 if date_of(b) >= datetime.datetime(2026, 9, 1, tzinfo=HKT)]
sep_h = max(b["high"] for b in sep_bars); sep_h_bar = max(sep_bars, key=lambda b: b["high"])
sep_l = min(b["low"] for b in sep_bars); sep_l_bar = min(sep_bars, key=lambda b: b["low"])
print(f"September range: H {sep_h:.1f} ({date_of(sep_h_bar).strftime('%m-%d')})  L {sep_l:.1f} ({date_of(sep_l_bar).strftime('%m-%d')})")

# Fibonacci of September expansion (low->high)
rng = sep_h - sep_l
fib = {p: sep_l + rng * p / 100 for p in [0, 25, 50, 62, 70.5, 79, 100]}
print(f"Fib (Sep expansion L->H, range {rng:.0f}):")
for p, v in fib.items():
    zone = "PREMIUM" if v > fib[50] else ("EQ" if p == 50 else "DISCOUNT")
    print(f"  {p}%: {v:.1f} [{zone}]")

cur = last_d1["close"]
pos = (cur - sep_l) / rng * 100
print(f"\nCurrent {cur:.1f} = {pos:.1f}% of September range (premium/discount eq 50%)")
daily_open = last_d1["open"]
print(f"Daily open {daily_open:.1f} -> price {'ABOVE' if cur > daily_open else 'BELOW'} open")

# SMT: NAS100 vs US500 (US500 D1 fetched earlier — rebuild from H4 if needed; use known closes)
print("\nSMT NAS100 vs US500 (D1 closes, same-day):")
print("  Sep 15: NAS100 C 28,983.5 (LL below Sep 12 low 28,910? no — new low below 28,909.9 -> sweep) | US500 C 7,595.1")
print("  Sep 16: NAS100 L 28,757.0 (sweeps Sep 15 low) | US500 L 7,507.2 (sweeps)")
print("  Sep 17: NAS100 C 29,430.5 reclaim | US500 C 7,635.6 reclaim")

print()
print("=" * 70)
print("LAYER 2 — H4 CONTEXT")
print("=" * 70)
completed_h4 = h4[:]  # last bar 06:00 HKT Fri = in-progress NY session 18:00
last_h4 = h4[-1]
print(f"H4 last bar: {date_of(last_h4).strftime('%a %m-%d %H:%M')} HKT O={last_h4['open']} H={last_h4['high']} L={last_h4['low']} C={last_h4['close']} (in-progress)")
h4_sh, h4_sl = swings(h4, 2)
print(f"H4 swing highs (last 5): {[(date_of(b).strftime('%m-%d %H:%M'), round(b['high'],1)) for _, b in h4_sh[-5:]]}")
print(f"H4 swing lows  (last 5): {[(date_of(b).strftime('%m-%d %H:%M'), round(b['low'],1)) for _, b in h4_sl[-5:]]}")

# H4 dealing range: Sep 11 low -> Sep 17-18 high
h4_sep = [b for b in h4 if date_of(b) >= datetime.datetime(2026, 9, 11, tzinfo=HKT)]
h4_h = max(b["high"] for b in h4_sep); h4_h_bar = max(h4_sep, key=lambda b: b["high"])
h4_l = min(b["low"] for b in h4_sep); h4_l_bar = min(h4_sep, key=lambda b: b["low"])
print(f"\nH4 Sep range: H {h4_h:.1f} ({date_of(h4_h_bar).strftime('%m-%d %H:%M')})  L {h4_l:.1f} ({date_of(h4_l_bar).strftime('%m-%d %H:%M')})")
h4_rng = h4_h - h4_l
h4_fib = {p: h4_l + h4_rng * p / 100 for p in [0, 25, 50, 62, 70.5, 79, 100]}
for p, v in h4_fib.items():
    print(f"  {p}%: {v:.1f}")

# FVG detection on H4 (3-candle gap)
print("\nH4 FVGs (last 40 bars):")
fvgs = []
for i in range(len(h4) - 42, len(h4) - 2):
    a, c = h4[i], h4[i + 2]
    if c["low"] > a["high"]:
        fvgs.append(("BULL", a["high"], c["low"], h4[i + 1]))
    if c["high"] < a["low"]:
        fvgs.append(("BEAR", c["high"], a["low"], h4[i + 1]))
for typ, lo, hi, mid in fvgs[-6:]:
    filled = "FILLED" if any(b["low"] <= lo and b["high"] >= hi for b in h4[h4.index(mid)+2:]) else ("PARTIAL/OPEN" if any(b["low"] < hi for b in h4[h4.index(mid)+2:]) else "OPEN")
    print(f"  {typ} FVG {lo:.1f}-{hi:.1f} (created {date_of(mid).strftime('%m-%d %H:%M')}) [{filled}]")

# price position in H4 range
h4_pos = (cur - h4_l) / h4_rng * 100
print(f"\nPrice {cur:.1f} = {h4_pos:.1f}% of H4 Sep range")

print()
print("=" * 70)
print("LAYER 3 — M15 ENTRY MODEL")
print("=" * 70)
# Today's session bars (Sep 18)
today = [b for b in m15 if date_of(b).date() == datetime.date(2026, 9, 18)]
yest = [b for b in m15 if date_of(b).date() == datetime.date(2026, 9, 17)]
print(f"Today M15 bars: {len(today)}, from {date_of(today[0]).strftime('%H:%M')} to {date_of(today[-1]).strftime('%H:%M')} HKT")
t_open = today[0]["open"]
t_hi = max(b["high"] for b in today); t_lo = min(b["low"] for b in today)
y_hi = max(b["high"] for b in yest); y_lo = min(b["low"] for b in yest)
print(f"Today: open={t_open:.1f} H={t_hi:.1f} L={t_lo:.1f} (session ext: {'H' if t_hi > y_hi else '-'}{'L' if t_lo < y_lo else '-'})")
print(f"Yesterday: H={y_hi:.1f} L={y_lo:.1f}")

# London & NY ranges
lon = [b for b in today if 15 <= date_of(b).hour < 22]  # 15:00-22:00 HKT = 07:00-14:00 UTC ≈ London
ny_am = [b for b in today if 21 <= date_of(b).hour < 24 or date_of(b).hour == 0]  # 21:00-01:00 HKT ≈ NY AM
print(f"London window (15-22 HKT): H={max((b['high'] for b in lon), default=0):.1f} L={min((b['low'] for b in lon), default=0):.1f}")
print(f"NY window bars so far (21-01 HKT): n={len(ny_am)}")

# M15 structure today
print("\nM15 transitions today (every 6th bar):")
for i in range(1, len(today), 6):
    cur_b, prv_b = today[i], today[i - 1]
    tag = ("HH" if cur_b["high"] > prv_b["high"] else "LH") + "+" + ("HL" if cur_b["low"] > prv_b["low"] else "LL")
    print(f"  {date_of(cur_b).strftime('%H:%M')}: {tag} C={cur_b['close']:.1f}")

# M15 FVG near price
print("\nM15 FVGs (last 50 bars, within 60pts of price):")
m15_fvgs = []
for i in range(len(m15) - 52, len(m15) - 2):
    a, c = m15[i], m15[i + 2]
    if c["low"] > a["high"]:
        m15_fvgs.append(("BULL", a["high"], c["low"], m15[i + 1]))
    if c["high"] < a["low"]:
        m15_fvgs.append(("BEAR", c["high"], a["low"], m15[i + 1]))
for typ, lo, hi, mid in m15_fvgs:
    if hi >= cur - 60 and lo <= cur + 60:
        print(f"  {typ} FVG {lo:.1f}-{hi:.1f} (created {date_of(mid).strftime('%m-%d %H:%M')})")

# Kill zone check
now_ny = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-4)))
print(f"\nNow NY time: {now_ny.strftime('%H:%M')} — NY AM KZ (07:00-10:00): {'ACTIVE' if 7 <= now_ny.hour < 10 else 'not yet/pre'}")
