#!/usr/bin/env python3
"""Score the 2026-09-28 week's NAS100 daily bias predictions against actual CFD price action.

Bias semantics from walker_ta.json: bias is issued ~18:30-19:00 HKT (before NY session)
for the REMAINDER of that trading day (CFD trading day). Scoring: the bias is correct
if the NY-session move from bias-issuance price toward the stated draw (TP1) realized,
i.e. direction of post-issuance price action (close vs issue price) matches the bias.
"""
import json, os, datetime

OUT = "/Users/ychen/.hermes/trading-war-room/signals/weekly_review_2026-09-28"
d1 = json.load(open(os.path.join(OUT, "raw_NAS100_D1.json")))
h4 = json.load(open(os.path.join(OUT, "raw_NAS100_H4.json")))

def sess_date(bar):
    """CFD trading-day label: D1 bars are stamped 21:00 UTC (session open 5pm NY).
    A bar stamped 2026-09-28T21:00Z = trading day Tuesday 2026-09-29 (NY time).
    """
    t = datetime.datetime.fromisoformat(bar["time_utc"])
    return (t + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

# D1 by session day
d1_by_day = {}
for b in d1:
    d1_by_day[sess_date(b)] = b

print("=== NAS100 CFD D1 bars (session-day labels, NY) ===")
for day in ["2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02"]:
    b = d1_by_day.get(day)
    if b is None:
        print(f"{day}: NO BAR")
        continue
    rng = b["high"] - b["low"]
    body = b["close"] - b["open"]
    print(f"{day}: O={b['open']:.1f} H={b['high']:.1f} L={b['low']:.1f} C={b['close']:.1f} "
          f"range={rng:.1f} body={body:+.1f} c2c={b['close'] - d1_by_day.get(_pd, {'close': b['close']})['close']:+.1f}"
          if False else
          f"{day}: O={b['open']:.1f} H={b['high']:.1f} L={b['low']:.1f} C={b['close']:.1f} "
          f"range={rng:.1f} body={body:+.1f}")

# close-to-close changes
days = ["2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02"]
print("\n=== Close-to-close ===")
prev = None
for day in days:
    b = d1_by_day.get(day)
    if b is None:
        continue
    if prev is not None:
        print(f"{day}: c2c {b['close'] - prev:+.1f} ({(b['close']/prev-1)*100:+.2f}%)")
    prev = b["close"]

# H4 within each session day (NY time), to see NY session action
print("\n=== H4 bars grouped by session day (NY time) ===")
h4_by_day = {}
for b in h4:
    t_ny = datetime.datetime.fromisoformat(b["time_ny"])
    # session day: if NY hour >= 17, belongs to NEXT calendar day's session
    d = t_ny.date()
    if t_ny.hour >= 17:
        d = d + datetime.timedelta(days=1)
    h4_by_day.setdefault(d.isoformat(), []).append(b)

for day in days[1:]:
    bars = h4_by_day.get(day, [])
    print(f"\n--- {day} (session) ---")
    for b in bars:
        t = datetime.datetime.fromisoformat(b["time_ny"])
        print(f"  {t.strftime('%a %H:%M')} NY: O={b['open']:.1f} H={b['high']:.1f} L={b['low']:.1f} C={b['close']:.1f}")

# Current live price
last_h4 = h4[-1]
print(f"\nLIVE: last H4 bar {last_h4['time_utc']} close={last_h4['close']}")
last_d1 = d1[-1]
print(f"LAST D1 bar: {last_d1['time_utc']} C={last_d1['close']}")
