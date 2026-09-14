#!/usr/bin/env python3
"""Pre-editor self-correction calcs: macro range frame, gap, % below EQ, ORB breakdown."""
low_m, high_m = 28882.4, 29734.2   # Sep 2 low / Sep 8 high (micro range)
low_a, high_a = 28882.4, 30246.2   # Sep 2 low / Aug 17 high (macro range)
px, fri_h, fri_c, mon_o = 28896.0, 29476.1, 29370.2, 29053.8

rng_a = high_a - low_a
print(f"Macro range Aug17->Sep2: {rng_a:.1f} pts")
for p in [25, 50, 62, 70.5, 79]:
    print(f"  macro Fib {p}% = {high_a - p/100*rng_a:.2f}")
ret = (high_a - fri_h) / rng_a * 100
print(f"Friday high {fri_h} retraced {ret:.1f}% of macro leg (between 50% {high_a-0.5*rng_a:.1f} and 62% {high_a-0.62*rng_a:.1f})")
pos_px = (px - low_a) / rng_a * 100
print(f"Current px {px} at {pos_px:.1f}% of macro range (from low)")

print(f"\nGap: {mon_o} - {fri_c} = {mon_o - fri_c:+.1f} pts (open INSIDE micro range {low_m}? {mon_o > low_m})")
print(f"px vs micro EQ {(low_m+high_m)/2:.1f}: {px - (low_m+high_m)/2:+.1f} pts = {(px/((low_m+high_m)/2)-1)*100:.2f}% below EQ")
print(f"Micro range position: {(px-low_m)/(high_m-low_m)*100:.1f}%")

mon_h, mon_l = 29097.7, 28804.5
w = mon_h - mon_l
print(f"\nMonday range so far: {w:.1f} pts = {w/px*100:.2f}% of price (band 0.3-1.5%: {'YES' if 0.3 <= w/px*100 <= 1.5 else 'NO'})")
print(f"NAS100 C2C Monday: {(px/fri_c-1)*100:.2f}%")
print(f"US500 C2C Monday: {(7602.5/7657.4-1)*100:.2f}%")

print("\nORB breakdown: HTF 20/25 (D1 bearish + gap-down aligned + SSL sweep), VWAP 0/15 (no tick data), "
      "Vol 0/20 (tick_volume=0 feed), Close&Timing 3/15 (no KZ low, no confirmation close), "
      "ICT 4/15 (no SMT, no Judas; FVG path defined), Range 5/10 (1.02% in band) => TOTAL 32/100")
