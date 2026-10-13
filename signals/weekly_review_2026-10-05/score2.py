#!/usr/bin/env python3
"""Corrected scoring pass for week 2026-10-05: proper H4 session grouping (NO +1day on H4,
pitfall #68), missing-bar sections (Oct 9 / Oct 12 stamps), issue-time checks, aggregates."""
import json, os, datetime

OUT = "/Users/ychen/.hermes/trading-war-room/signals/weekly_review_2026-10-05"
d1 = json.load(open(os.path.join(OUT, "raw_NAS100_D1.json")))
h4 = json.load(open(os.path.join(OUT, "raw_NAS100_H4.json")))

def sess_date_d1(bar):
    t = datetime.datetime.fromisoformat(bar["time_utc"])
    return (t + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

def sess_day_h4(bar):
    """H4 bar -> NY session day. Uses time_ny; NY hour >= 17 belongs to next day's session."""
    t_ny = datetime.datetime.fromisoformat(bar["time_ny"])
    d = t_ny.date()
    if t_ny.hour >= 17:
        d = d + datetime.timedelta(days=1)
    return d.isoformat()

d1_by_day = {sess_date_d1(b): b for b in d1}
h4_by_day = {}
for b in h4:
    h4_by_day.setdefault(sess_day_h4(b), []).append(b)

print("=== H4 by SESSION day (correct grouping) ===")
for day in ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09", "2026-10-12"]:
    bars = sorted(h4_by_day.get(day, []), key=lambda b: b["time_utc"])
    if not bars:
        print(f"--- {day}: none")
        continue
    hi = max(b["high"] for b in bars); lo = min(b["low"] for b in bars)
    print(f"--- {day} ({datetime.date.fromisoformat(day).strftime('%a')}): H={hi:.1f} L={lo:.1f}")
    for b in bars:
        t = datetime.datetime.fromisoformat(b["time_utc"])
        print(f"  {t.strftime('%m-%d %H:%M')}Z: O={b['open']:.1f} H={b['high']:.1f} L={b['low']:.1f} C={b['close']:.1f}")

print("\n=== Issue-time checks ===")
# Walker 10-12: 'session low 30828.8 in the 10:30 UTC bar' at issue 10:46Z Mon
mon_pre = [b for b in h4_by_day.get("2026-10-12", []) if b["time_utc"] <= "2026-10-12T13:00:00+00:00"]
print("Mon 10-12 bars at/after issue (stamp<=13:00Z):")
for b in mon_pre:
    print(f"  {b['time_utc']}: O={b['open']:.1f} H={b['high']:.1f} L={b['low']:.1f} C={b['close']:.1f}")
pre_lows = [b["low"] for b in mon_pre if b["time_utc"] < "2026-10-12T13:00:00+00:00"]
print(f"  min low before 13:00Z (issue was 10:46Z): {min(pre_lows) if pre_lows else None} (claimed 30828.8)")
# where did 30647.7 print?
for b in h4_by_day.get("2026-10-12", []):
    if b["low"] <= 30648:
        print(f"  30647.7 printed in bar {b['time_utc']} (L={b['low']:.1f})")

# Merlin 10-09 bullish @ 11:00Z Fri: H4 proxy = close of 08:00-12:00Z bar (stamp 2026-10-09T08:00Z? H4 stamps are 4h: 00,04,08,12,16,20)
fri = h4_by_day.get("2026-10-09", [])
for b in fri:
    if b["time_utc"].startswith("2026-10-09T08"):
        print(f"\nMerlin 10-09 issue proxy: 08:00Z-12:00Z bar C={b['close']:.1f} (11:00Z issue)")
        iss = b["close"]
        cl = d1_by_day["2026-10-09"]["close"]
        print(f"  post-issue: {cl:.1f} vs {iss:.1f} = {cl-iss:+.1f} ({(cl/iss-1)*100:+.2f}%)")
        dr_lo, dr_hi = 30568.2, 31386.3
        print(f"  merlin claim 'PREMIUM 69.1% of DR': price {iss:.1f} -> actual pos {(iss-dr_lo)/(dr_hi-dr_lo)*100:.1f}%")
# Merlin 10-07 '31036' and Merlin 10-08 '30920.1' — scan week H4 lows/closes near those
print("\n=== scan: any H4 close/low near 31036 (Wed 03:00Z context) or 30920 (Thu 03:00Z context) ===")
wed_pre = [b for b in h4_by_day.get("2026-10-07", []) if b["time_utc"] <= "2026-10-07T05:00:00+00:00"]
for b in wed_pre:
    print(f"  Wed@{b['time_utc']}: C={b['close']:.1f} L={b['low']:.1f}")
thu_pre = [b for b in h4_by_day.get("2026-10-08", []) if b["time_utc"] <= "2026-10-08T05:00:00+00:00"]
for b in thu_pre:
    print(f"  Thu@{b['time_utc']}: C={b['close']:.1f} L={b['low']:.1f}")

print("\n=== 6 consecutive up closes claim (walker 10-06, as of Oct 6) ===")
days_seq = ["2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06"]
prev = d1_by_day["2026-09-28"]["close"]
ups = 0
for dd in days_seq:
    b = d1_by_day.get(dd)
    if b is None:
        print(f"  {dd}: NO BAR"); break
    ch = b["close"] - prev
    ups += 1 if ch > 0 else 0
    print(f"  {dd}: c2c {ch:+.1f} ({(b['close']/prev-1)*100:+.2f}%) {'UP' if ch>0 else 'DOWN'}")
    prev = b["close"]
print(f"  -> consecutive up closes ending Oct 6: {ups}")

print("\n=== Week aggregates (corrected) ===")
f2, f9 = d1_by_day["2026-10-02"], d1_by_day["2026-10-09"]
print(f"Fri2Fri: {f2['close']:.1f} -> {f9['close']:.1f} = {(f9['close']/f2['close']-1)*100:+.2f}%")
mon = d1_by_day["2026-10-12"]
print(f"Mon 10-12 as-of close {mon['close']:.1f} (bar incomplete at fetch; equity RTH ended 16:00 NY) -> week-to-date {(mon['close']/f2['close']-1)*100:+.2f}%")
print(f"Mon 10-12 c2c vs Fri: {mon['close']-f9['close']:+.1f} ({(mon['close']/f9['close']-1)*100:+.2f}%)")

print("\n=== US500 SMT (walker 10-12 'none, both HH+HL') ===")
u5 = json.load(open(os.path.join(OUT, "raw_US500_D1.json")))
u5_by_day = {sess_date_d1(b): b for b in u5}
seq = ["2026-09-22", "2026-09-23", "2026-09-28", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-08", "2026-10-09"]
for dd in seq:
    b = u5_by_day.get(dd)
    n = d1_by_day.get(dd)
    print(f"  {dd}: US500 H={b['high']:.1f} L={b['low']:.1f}" if b else f"  {dd}: no US500 bar",
          f"| NAS100 H={n['high']:.1f} L={n['low']:.1f}" if n else "")
print("  NAS: HH 31386.3(10/6)>30820.4(9/23)? ", 31386.3 > 30820.4, "| HL 30568.2(10/8)>30100.8(9/28)? ", 30568.2 > 30100.8)
print("  US500: HH 7845.3(10/6)>7795.0(10/5)>7754.8(10/2)? ", 7845.3 > 7795.0, "| HL 7732.4(10/8)>7668.0(10/2)? ", 7732.4 > 7668.0)
# walker 10-05 SMT-at-issue: US500 Mon live high 7740.2 vs 7785.0 (Sep 22)
print("  walker 10-05 SMT-at-issue: US500 Mon live H 7740.2 < 7785.0 (at 10:36Z); final Mon H =", f"{u5_by_day['2026-10-05']['high']:.1f}", "-> sweep completed later Mon")
