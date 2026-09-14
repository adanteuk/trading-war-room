#!/usr/bin/env python3
"""Supplementary: volumes, M15 KZ timing, US500 SMT detail, weekly profile context."""
import json, datetime

DIR = "/Users/ychen/.hermes/trading-war-room/signals/2026-09-14"

def load(key):
    with open(f"{DIR}/raw_{key}.json") as f:
        return json.load(f)

def bars_with_time(key):
    out = []
    for b in load(key):
        tu = b.get("time_utc") or datetime.datetime.utcfromtimestamp(b["time_epoch"]).isoformat()
        dt = datetime.datetime.fromisoformat(tu.replace("Z", "+00:00"))
        out.append({"utc": dt, "hkt": dt + datetime.timedelta(hours=8),
                    "o": float(b["open"]), "h": float(b["high"]), "l": float(b["low"]),
                    "c": float(b["close"]), "v": b.get("tick_volume", 0)})
    return out

m15 = bars_with_time("NAS100_M15")
h4 = bars_with_time("NAS100_H4")
us_h4 = bars_with_time("US500_H4")

# --- M15 bars of Monday Sep 14 (session opened 21:00 UTC Sep 13 = 05:00 HKT Sep 14) ---
mon_m15 = [b for b in m15 if b["utc"] >= datetime.datetime.fromisoformat("2026-09-13T21:00:00+00:00")]
low_bar = min(mon_m15, key=lambda b: b["l"])
high_bar = max(mon_m15, key=lambda b: b["h"])
print(f"Monday M15 bars: {len(mon_m15)}")
print(f"Session HIGH {high_bar['h']:.1f} at {high_bar['hkt'].strftime('%H:%M')} HKT ({high_bar['utc'].strftime('%H:%M')} UTC)")
print(f"Session LOW  {low_bar['l']:.1f} at {low_bar['hkt'].strftime('%H:%M')} HKT ({low_bar['utc'].strftime('%H:%M')} UTC)")
# Kill zones HKT: London KZ 14:00-17:00, NY AM KZ 20:30-23:00
lb_hkt = low_bar["hkt"].hour * 60 + low_bar["hkt"].minute
in_lonkz = 14*60 <= lb_hkt <= 17*60
print(f"Low made in London KZ (14:00-17:00 HKT)? {in_lonkz}")

# last 8 M15 bars w/ times (bounce context)
print("\nLast 8 M15 bars (HKT):")
for b in mon_m15[-8:]:
    print(f"  {b['hkt'].strftime('%H:%M')} O={b['o']:.1f} H={b['h']:.1f} L={b['l']:.1f} C={b['c']:.1f} v={b['v']}")

# --- Volume: Monday cumulative tick volume so far vs recent days ---
d1 = bars_with_time("NAS100_D1")
fri = [b for b in d1 if b["utc"].date() == datetime.date(2026, 9, 10)]  # D1 stamp 21:00/22:00 UTC Sep 10 = Friday session
print("\nD1 last bars w/ volume (session stamp UTC):")
for b in d1[-5:]:
    print(f"  stamp {b['utc'].strftime('%m-%d %H:%M')} UTC  O={b['o']:.1f} C={b['c']:.1f} tickvol={b['v']}")
mon_d1 = d1[-1]
fri_d1 = d1[-2]
print(f"Monday tick_volume so far: {mon_d1['v']}, Friday full-day: {fri_d1['v']}, ratio={mon_d1['v']/fri_d1['v']:.2f} (Monday session ~55% complete at 18:30 HKT)")

# --- US500 Monday: did it sweep its Sep 2 low (7610.2)? ---
us_mon = [b for b in us_h4 if b["utc"] >= datetime.datetime.fromisoformat("2026-09-13T21:00:00+00:00")]
if us_mon:
    us_low = min(b["l"] for b in us_mon)
    us_high = max(b["h"] for b in us_mon)
    us_last = us_h4[-1]
    print(f"\nUS500 Monday: H={us_high:.1f} L={us_low:.1f} last close={us_last['c']:.1f}")
    print(f"US500 Sep 2 swing low: 7610.2 | Aug 20 swing low: 7639.7")
    print(f"US500 swept Sep 2 low? {us_low < 7610.2} | NAS100 swept its Sep 2 low (28882.4)? True (low 28804.5)")
# US500 Friday close for gap
us_fri = [b for b in us_h4 if datetime.datetime.fromisoformat("2026-09-10T21:00:00+00:00") <= b["utc"] < datetime.datetime.fromisoformat("2026-09-13T21:00:00+00:00")]
if us_fri:
    us_fri_close = us_fri[-1]["c"]
    print(f"US500 Friday close (last H4): {us_fri_close:.1f} | Monday open: {us_mon[0]['o']:.1f} | gap {us_mon[0]['o']-us_fri_close:+.1f}")

# --- NAS100 Monday H4 timestamps (HKT) for session narrative ---
print("\nNAS100 Monday H4 bars (HKT session times):")
mon_h4 = [b for b in h4 if b["utc"] >= datetime.datetime.fromisoformat("2026-09-13T21:00:00+00:00")]
for b in mon_h4:
    print(f"  {b['hkt'].strftime('%a %H:%M')} HKT  O={b['o']:.1f} H={b['h']:.1f} L={b['l']:.1f} C={b['c']:.1f} v={b['v']}")

# --- overnight/Asia vs London range breakdown ---
asia = [b for b in mon_m15 if b["hkt"].hour < 14]
london = [b for b in mon_m15 if 14 <= b["hkt"].hour < 17]
after = [b for b in mon_m15 if b["hkt"].hour >= 17]
for name, seg in [("Asia (05:00-14:00)", asia), ("London (14:00-17:00)", london), ("Post-London (17:00+)", after)]:
    if seg:
        print(f"{name}: H={max(b['h'] for b in seg):.1f} L={min(b['l'] for b in seg):.1f} n={len(seg)}")

# --- Fib recheck with exact numbers ---
low_dr, high_dr = 28882.4, 29734.2
rng = high_dr - low_dr
for p in [25, 50, 62, 70.5, 79]:
    print(f"Fib {p}% = {high_dr - p/100*rng:.1f}")
print(f"EQ = {(low_dr+high_dr)/2:.1f}")
# Monday low vs 79% ext below range low: 100% ext below = low - rng
print(f"Range extension 125% (below low) = {low_dr - 0.25*rng:.1f}")
