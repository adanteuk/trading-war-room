#!/usr/bin/env python3
"""Verify swing-level claims: NAS100 Sep-23 HH / Sep-16 LL, US500 Sep-22 swing high, final numbers."""
import json, os, datetime

OUT = "/Users/ychen/.hermes/trading-war-room/signals/weekly_review_2026-09-28"
d1 = json.load(open(os.path.join(OUT, "raw_NAS100_D1.json")))
u1 = json.load(open(os.path.join(OUT, "raw_US500_D1.json")))

def sess_date(bar):
    t = datetime.datetime.fromisoformat(bar["time_utc"])
    return (t + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

nas = {sess_date(b): b for b in d1}
us = {sess_date(b): b for b in u1}

print("=== NAS100 swing claims ===")
print(f"Sep 16 LL claim 28756.7 -> actual {nas['2026-09-16']['low']}")
print(f"Sep 23 HH claim 30820.4 -> actual {nas['2026-09-23']['high']}")
print(f"Sep 22 high claim 30788.3 -> actual {nas['2026-09-22']['high']}")
print(f"Sep 24 SSL claim 30100.9 -> actual {nas['2026-09-24']['low']}")

print("\n=== US500 swing claims (Thu signal) ===")
print(f"Sep 22 swing high claim 7785.0 -> actual {us['2026-09-22']['high']}")
print(f"Oct 1 ONH claim 7711.7 -> actual {us['2026-10-01']['high']}")
print(f"Sep 30 PDH claim 7725.2 -> actual {us['2026-09-30']['high']}")
print(f"Sep 24 SSL claim 7650.3 -> actual {us['2026-09-24']['low']}")
print(f"Tue 9/29 low 7655.5 -> actual {us['2026-09-29']['low']} (swept Mon 7668.4: {us['2026-09-29']['low'] < us['2026-09-28']['low']}, held SSL by {us['2026-09-29']['low']-us['2026-09-24']['low']:.1f}pt)")

print("\n=== FINAL scored numbers (Friday close now final 30808.3) ===")
closes = {"2026-09-25": nas['2026-09-25']['close'], "2026-09-28": nas['2026-09-28']['close'],
          "2026-09-29": nas['2026-09-29']['close'], "2026-09-30": nas['2026-09-30']['close'],
          "2026-10-01": nas['2026-10-01']['close'], "2026-10-02": 30808.3}
order = ["2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02"]
for i in range(1, len(order)):
    p, c = closes[order[i-1]], closes[order[i]]
    print(f"{order[i]}: c2c {c-p:+.1f} ({(c/p-1)*100:+.3f}%)")
print(f"Week: {closes['2026-09-25']} -> {closes['2026-10-02']} = {(closes['2026-10-02']/closes['2026-09-25']-1)*100:+.2f}%")
print(f"Fri as-issued: 30728.0 -> 30808.3 = {(30808.3/30728.0-1)*100:+.3f}%")

# calibration math
dir_res = [("2026-09-28", "bearish", 55, "bearish"), ("2026-09-29", "bullish", 55, "bullish"),
           ("2026-10-01", "bearish", 58, "bullish-c2c"), ("2026-10-02", "bullish", 52, "bullish")]
ok_conf = [55, 55, 52]; bad_conf = [58]
print(f"\nAvg conf correct: {sum(ok_conf)/3:.1f} | wrong: {bad_conf} | all directional: {sum(ok_conf+bad_conf)/4:.1f}")
