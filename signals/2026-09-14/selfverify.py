#!/usr/bin/env python3
"""Self-verification fallback (editor timed out). Full re-derivation from raw data.
Also corrects the volume finding: raw files use 'volume' key (non-zero), not tick_volume."""
import json, datetime

DIR = "/Users/ychen/.hermes/trading-war-room/signals/2026-09-14"

def load(key):
    with open(f"{DIR}/raw_{key}.json") as f:
        return json.load(f)

def conv(b, tf):
    dt = datetime.datetime.fromisoformat(b["time_utc"].replace("+00:00", "+00:00"))
    if tf == "D1":
        dt = dt + datetime.timedelta(days=1)
    hkt = dt + datetime.timedelta(hours=8)
    return {"utc": dt.replace(tzinfo=None), "hkt": (dt + datetime.timedelta(hours=8)).replace(tzinfo=None),
            "o": b["open"], "h": b["high"], "l": b["low"],
            "c": b["close"], "v": b.get("volume", b.get("tick_volume", 0))}

def series(key, tf):
    return [conv(b, tf) for b in load(key)]

print("### CHECK A: VOLUME CORRECTION ###")
d1 = series("NAS100_D1", "D1")
m15 = series("NAS100_M15", "M15")
print("Last 6 D1 bars with volume:")
for b in d1[-6:]:
    print(f"  {b['utc'].strftime('%Y-%m-%d')} O={b['o']:.1f} C={b['c']:.1f} vol={b['v']}")
mon = d1[-1]
# comparable partial-day volumes: for each of last 5 days, cumulative volume up to 10:30 UTC
print("\nComparable cumulative volume by 10:30 UTC (18:30 HKT) for prior 5 sessions:")
def cum_vol_at(bars, day_offset, cutoff_hour=10):
    # D1 bars don't have intraday; use M15 only for recent days (200 bars = 50 hrs = ~2 days)
    return None
# M15 has 200 bars ~= 50 hours. Use M15 for Monday and Friday partial/full:
mon_m15 = [b for b in m15 if b["utc"] >= datetime.datetime(2026, 9, 13, 21, 0)]
mon_cum = sum(b["v"] for b in mon_m15)
print(f"Monday M15 cumulative volume to 18:30 HKT: {mon_cum}")
fri_start = datetime.datetime(2026, 9, 10, 21, 0)
fri_end = datetime.datetime(2026, 9, 13, 21, 0)
fri_m15 = [b for b in m15 if fri_start <= b["utc"] < fri_end]
fri_cum_full = sum(b["v"] for b in fri_m15)
fri_partial = sum(b["v"] for b in fri_m15 if b["utc"] < fri_start + datetime.timedelta(hours=13.5))
print(f"Friday M15 volume (full session): {fri_cum_full} | Friday same-clock-time (first 13.5h): {fri_partial}")
if fri_partial > 0:
    print(f"Monday vs Friday same-time RVOL: {mon_cum/fri_partial:.2f}")
# volume during the selloff vs bounce
sell = [b for b in mon_m15 if b["utc"] < datetime.datetime(2026, 9, 14, 9, 15)]
bounce = [b for b in mon_m15 if b["utc"] >= datetime.datetime(2026, 9, 14, 9, 15)]
print(f"Volume into low (05:00-17:15 HKT): {sum(b['v'] for b in sell)} ({len(sell)} bars, avg {sum(b['v'] for b in sell)/max(1,len(sell)):.0f}/bar)")
print(f"Volume after low (17:15-18:30 HKT): {sum(b['v'] for b in bounce)} ({len(bounce)} bars, avg {sum(b['v'] for b in bounce)/max(1,len(bounce)):.0f}/bar)")

print("\n### CHECK B: D1 DATES & KEY BARS ###")
for b in d1[-12:]:
    print(f"  {b['utc'].strftime('%Y-%m-%d')} O={b['o']:.1f} H={b['h']:.1f} L={b['l']:.1f} C={b['c']:.1f}")

print("\n### CHECK C: SWINGS (5-bar symmetric lookback) ###")
def swings(s, lb=5):
    hs, ls = [], []
    for i in range(lb, len(s) - lb):
        wh = [x["h"] for x in s[i-lb:i+lb+1]]
        wl = [x["l"] for x in s[i-lb:i+lb+1]]
        if s[i]["h"] == max(wh) and wh.count(s[i]["h"]) == 1:
            hs.append((s[i]["utc"].strftime("%Y-%m-%d"), s[i]["h"]))
        if s[i]["l"] == min(wl) and wl.count(s[i]["l"]) == 1:
            ls.append((s[i]["utc"].strftime("%Y-%m-%d"), s[i]["l"]))
    return hs, ls
sh, sl = swings(d1, 5)
print("D1 swing highs (last 6):", [(d, round(v,1)) for d,v in sh[-6:]])
print("D1 swing lows (last 6):", [(d, round(v,1)) for d,v in sl[-6:]])
print("Aug 17 high present?", any(d == "2026-08-17" for d, _ in sh))
print("May 19 low ~28596 present?", any(d.startswith("2026-05") for d, _ in sl))
print("Jul 17 low ~28209 present?", any(d == "2026-07-17" for d, _ in sl))

print("\n### CHECK D: FIB MATH ###")
lo, hi, malo, mahi = 28882.4, 29734.2, 28882.4, 30246.2
r1, r2 = hi - lo, mahi - malo
for p in [25, 50, 62, 70.5, 79]:
    print(f"  micro {p}%: {hi - p/100*r1:.1f}")
print(f"  macro 50%: {mahi - 0.5*r2:.1f}, 62%: {mahi - 0.62*r2:.1f}")
print(f"  Fri high retrace of macro: {(mahi - 29476.1)/r2*100:.1f}%")

print("\n### CHECK E: STRUCTURE TRANSITIONS ###")
for i in range(len(d1)-9, len(d1)):
    cur, prev = d1[i], d1[i-1]
    tags = []
    tags.append("HH" if cur["h"] > prev["h"] else "LH")
    tags.append("HL" if cur["l"] > prev["l"] else "LL")
    print(f"  {cur['utc'].strftime('%Y-%m-%d')}: {'+'.join(tags)}  H={cur['h']:.1f} (vs {prev['h']:.1f})  L={cur['l']:.1f} (vs {prev['l']:.1f})")

print("\n### CHECK F: M15 MONDAY TIMING ###")
mon_m15b = [b for b in m15 if b["utc"] >= datetime.datetime(2026, 9, 13, 21, 0)]
hb = max(mon_m15b, key=lambda b: b["h"]); lb_ = min(mon_m15b, key=lambda b: b["l"])
print(f"  High {hb['h']:.1f} at {hb['hkt'].strftime('%H:%M')} HKT | Low {lb_['l']:.1f} at {lb_['hkt'].strftime('%H:%M')} HKT")
print(f"  First bar open: {mon_m15b[0]['o']:.1f} at {mon_m15b[0]['hkt'].strftime('%H:%M')} HKT")
print(f"  Low in London KZ (14:00-17:00 HKT)? {14 <= lb_['hkt'].hour <= 17}")
print(f"  Last M15 bar: {mon_m15b[-1]['hkt'].strftime('%H:%M')} C={mon_m15b[-1]['c']:.1f}")

print("\n### CHECK G: US500 ###")
usd1 = series("US500_D1", "D1")
ush4 = series("US500_H4", "H4")
for b in usd1[-7:]:
    print(f"  {b['utc'].strftime('%Y-%m-%d')} O={b['o']:.1f} H={b['h']:.1f} L={b['l']:.1f} C={b['c']:.1f}")
us_mon = [b for b in ush4 if b["utc"] >= datetime.datetime(2026, 9, 13, 21, 0)]
us_fri = [b for b in ush4 if datetime.datetime(2026, 9, 10, 21, 0) <= b["utc"] < datetime.datetime(2026, 9, 13, 21, 0)]
print(f"  Monday: H={max(b['h'] for b in us_mon):.1f} L={min(b['l'] for b in us_mon):.1f} lastC={ush4[-1]['c']:.1f}")
print(f"  Fri close (last H4): {us_fri[-1]['c']:.1f} | Mon open {us_mon[0]['o']:.1f} | gap {us_mon[0]['o']-us_fri[-1]['c']:+.1f}")
print(f"  Sep 2 D1 low: {[b['l'] for b in usd1 if b['utc'].strftime('%Y-%m-%d')=='2026-09-02']}")
print(f"  C2C Mon: {(ush4[-1]['c']/us_fri[-1]['c']-1)*100:.2f}% | NAS C2C: {(28896.0/29370.2-1)*100:.2f}%")

print("\n### CHECK H: H4 FVGs NEAR PRICE ###")
h4 = series("NAS100_H4", "H4")
for i in range(len(h4)-6, len(h4)):
    c1, c3 = h4[i-2], h4[i]
    if c3["l"] > c1["h"]:
        print(f"  BULL FVG end {c3['utc'].strftime('%m-%d %H:%M')}UTC zone {c1['h']:.1f}-{c3['l']:.1f}")
    if c3["h"] < c1["l"]:
        print(f"  BEAR FVG end {c3['utc'].strftime('%m-%d %H:%M')}UTC zone {c3['h']:.1f}-{c1['l']:.1f}")
