#!/usr/bin/env python3
"""Arithmetic checks for weekly bias accuracy report + US500 SMT cross-check (Tue claim)."""
import json, os, datetime

OUT = "/Users/ychen/.hermes/trading-war-room/signals/weekly_review_2026-09-28"
d1 = json.load(open(os.path.join(OUT, "raw_NAS100_D1.json")))

def sess_date(bar):
    t = datetime.datetime.fromisoformat(bar["time_utc"])
    return (t + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

by_day = {sess_date(b): b for b in d1}
days = ["2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02"]

print("=== Issue-price -> close (as-issued basis) ===")
issues = {"2026-09-28": 30338.3, "2026-09-29": 30360.2, "2026-09-30": 30340.7,
          "2026-10-01": 30647.0, "2026-10-02": 30728.0}
for day in days[1:]:
    c = by_day[day]["close"]
    ip = issues[day]
    print(f"{day}: issue {ip} -> close {c} = {c-ip:+.1f} pts ({(c/ip-1)*100:+.3f}%)")

print("\n=== Close-to-close ===")
for i in range(1, len(days)):
    prev_c = by_day[days[i-1]]["close"]; c = by_day[days[i]]["close"]
    print(f"{days[i]}: {prev_c:.1f} -> {c:.1f} = {c-prev_c:+.1f} ({(c/prev_c-1)*100:+.3f}%)")

print("\n=== Week aggregate ===")
wk = (by_day["2026-10-02"]["close"]/by_day["2026-09-25"]["close"]-1)*100
print(f"Week c2c (Fri 9/25 -> Fri 10/2 provisional): {by_day['2026-09-25']['close']} -> {by_day['2026-10-02']['close']} = {wk:+.2f}%")

print("\n=== Confidence ===")
dir_conf = [55, 55, 58, 52]
print(f"Directional avg: {sum(dir_conf)/len(dir_conf):.1f}%  (n=4)")
all_conf = [55, 55, 40, 58, 52]
print(f"Incl neutral avg: {sum(all_conf)/len(all_conf):.1f}%  (n=5)")

print("\n=== Thu 10-01 close position % of range ===")
b = by_day["2026-10-01"]
pos = (b["close"]-b["low"])/(b["high"]-b["low"])*100
print(f"close {b['close']} between L {b['low']} and H {b['high']} -> {pos:.1f}% of range")

print("\n=== TP1 hit checks ===")
mon = by_day["2026-09-28"]
print(f"Mon TP1 30100.9 vs Mon session low {mon['low']} -> {'HIT (swept ' + str(round(mon['low']-30100.9,1)) + 'pt through)' if mon['low'] <= 30100.9 else 'miss'}")
tue = by_day["2026-09-29"]
print(f"Tue TP1 30449.1 vs Tue session high {tue['high']} -> {'HIT' if tue['high'] >= 30449.1 else 'miss'}")
print(f"Thu 30262 support vs Thu low {by_day['2026-10-01']['low']} -> miss by {by_day['2026-10-01']['low']-30262:.1f} pts" if by_day['2026-10-01']['low'] > 30262 else "Thu 30262 hit")
fri = by_day["2026-10-02"]
print(f"Fri BSL 30903.8 vs Fri high {fri['high']} -> {'SWEPT (+' + str(round(fri['high']-30903.8,1)) + 'pt beyond)' if fri['high'] > 30903.8 else 'not swept'}")

print("\n=== US500 SMT cross-check (Tue 9/29 claim: US500 swept Mon low, held Sep-24 SSL 7650.3) ===")
u = json.load(open(os.path.join(OUT, "raw_US500_D1.json")))
u_by_day = {sess_date(b): b for b in u}
for day in ["2026-09-24", "2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02"]:
    b = u_by_day.get(day)
    if b:
        print(f"{day}: O={b['open']:.1f} H={b['high']:.1f} L={b['low']:.1f} C={b['close']:.1f}")
print("Claim check: Mon low vs Tue low:", u_by_day['2026-09-28']['low'], "vs", u_by_day['2026-09-29']['low'],
      "-> Tue swept Mon low:", u_by_day['2026-09-29']['low'] < u_by_day['2026-09-28']['low'])
