#!/usr/bin/env python3
"""Deep-dive on items that failed or need closer inspection in pass 1."""
import json, re
from datetime import datetime, timezone, timedelta

BASE = "/Users/ychen/.hermes/trading-war-room/signals/2026-09-18"
HKT = timezone(timedelta(hours=8))
D1 = json.load(open(f"{BASE}/raw_NAS100_D1.json"))
H4 = json.load(open(f"{BASE}/raw_NAS100_H4.json"))
M15 = json.load(open(f"{BASE}/raw_NAS100_M15.json"))
TA = json.load(open(f"{BASE}/walker_ta.json"))
SESS0 = 1789682400

def dtk(ts): return datetime.fromtimestamp(ts, HKT).strftime("%m-%d %H:%M")

print("=== A. H4 bull FVG claim 29252-29359 (Sep 17) ===")
sep16 = datetime(2026,9,16,0,0,tzinfo=HKT).timestamp()
sep19 = datetime(2026,9,19,0,0,tzinfo=HKT).timestamp()
w = [b for b in H4 if sep16-86400 <= b["time"] < sep19]
for b in w: print(f"  {dtk(b['time'])}  O={b['open']:<8} H={b['high']:<8} L={b['low']:<8} C={b['close']:<8}")
print("  -- triple scan (i-2 high vs i low), i in Sep16-19 window:")
for j in range(2, len(w)):
    a, c = w[j-2], w[j]
    if a["high"] < c["low"]:
        print(f"  BULL FVG: mid={dtk(w[j-1]['time'])}  gap {a['high']} .. {c['low']}")
    if a["low"] > c["high"]:
        print(f"  BEAR FVG: mid={dtk(w[j-1]['time'])}  gap {c['high']} .. {a['low']}")
print("  -- also scan wider Sep 10-19 for any bull FVG overlapping 29252-29359:")
sep10 = datetime(2026,9,10,0,0,tzinfo=HKT).timestamp()
w2 = [b for b in H4 if sep10 <= b["time"] < sep19]
for j in range(2, len(w2)):
    a, c = w2[j-2], w2[j]
    if a["high"] < c["low"]:
        g1, g2 = a["high"], c["low"]
        if g2 >= 29252-50 and g1 <= 29359+50:
            print(f"  BULL FVG mid={dtk(w2[j-1]['time'])}  {g1}..{g2}")

print("\n=== B. M15 bull FVG claim 29570-29587 (18:15) ===")
t0 = datetime(2026,9,18,16,0,tzinfo=HKT).timestamp()
w = [b for b in M15 if b["time"] >= t0]
for b in w: print(f"  {dtk(b['time'])}  O={b['open']:<8} H={b['high']:<8} L={b['low']:<8} C={b['close']:<8} V={b['volume']}")
print("  -- all M15 bull FVGs today:")
today = [b for b in M15 if b["time"] >= SESS0]
for j in range(2, len(today)):
    a, c = today[j-2], today[j]
    if a["high"] < c["low"]:
        print(f"  BULL FVG mid={dtk(today[j-1]['time'])}  {a['high']}..{c['low']}")
    if a["low"] > c["high"]:
        print(f"  BEAR FVG mid={dtk(today[j-1]['time'])}  {c['high']}..{a['low']}")

print("\n=== C. Day high timing & M15 structure 10:15-14:45 ===")
dh = max(today, key=lambda b: b["high"])
print(f"  day high {dh['high']} at {dtk(dh['time'])}")
w = [b for b in today if datetime.fromtimestamp(b['time'],HKT).strftime('%H:%M') >= '10:15' and datetime.fromtimestamp(b['time'],HKT).strftime('%H:%M') <= '14:45']
hhhl = True
for j in range(1, len(w)):
    print(f"  {dtk(w[j]['time'])} H={w[j]['high']} L={w[j]['low']}  HH={w[j]['high']>w[j-1]['high']} HL={w[j]['low']>w[j-1]['low']}")
# pullback after 14:45: lows
after = [b for b in today if b["time"] > dh["time"]]
if after:
    pb = min(after, key=lambda b: b["low"])
    print(f"  after day high: pullback low {pb['low']} at {dtk(pb['time'])}")

print("\n=== D. When did price cross Sep17 high 29500.6 (purge 'last night' vs today)? ===")
first = next((b for b in today if b["high"] > 29500.6), None)
print(f"  first M15 bar today exceeding 29500.6: {dtk(first['time']) if first else 'none'} (H={first['high'] if first else '-'})")
ovn = [b for b in H4 if sep16 <= b["time"] < SESS0]
for b in ovn[-6:]:
    print(f"  H4 {dtk(b['time'])} H={b['high']} L={b['low']} C={b['close']}")

print("\n=== E. EQH / Aug28 high, cross-check D1 & H4 ===")
b28 = next(b for b in D1 if datetime.fromtimestamp(b["time"],HKT).strftime("%Y-%m-%d")=="2026-08-28")
print(f"  D1 Aug28 high = {b28['high']}")
h4_28 = [b for b in H4 if datetime.fromtimestamp(b["time"],HKT).strftime("%Y-%m-%d")=="2026-08-28"]
print(f"  H4 Aug28 max high = {max(b['high'] for b in h4_28)}  -> rounded {round(max(b['high'] for b in h4_28))}")

print("\n=== F. 'Sep 17 close reclaimed 50%/62% Fibs' ===")
c17 = next(b for b in D1 if datetime.fromtimestamp(b["time"],HKT).strftime("%Y-%m-%d")=="2026-09-17")["close"]
print(f"  Sep17 close {c17} vs 50% {29245.55} -> {c17>29245.55}; vs 62% {29362.8} -> {c17>29362.8}")

print("\n=== G. L2 'price at 92%' check ===")
lo, hi = 28757.0, 29734.1
for label, px in [("D1 close", 29604.7), ("M15 last", 29600.3), ("day high", 29677.7), ("H4 last close", 29609.9)]:
    print(f"  {label} {px}: {(px-lo)/(hi-lo)*100:.1f}%")
print(f"  price needed for 92%: {lo+0.92*(hi-lo):.1f}")

print("\n=== H. Relevancy regex fixed (exclude score patterns like 55/100) ===")
blob = json.dumps(TA, ensure_ascii=False)
dates = sorted(set(re.findall(r"2026-\d{2}-\d{2}", blob)))
md = sorted(set(m for m in re.findall(r"\b(\d{1,2}/\d{1,2})\b", blob) if not re.match(r"^\d+/100$", m)))
print("  full dates:", dates, "| MM/DD-like:", md)
print("  time mentions:", sorted(set(re.findall(r"\b\d{2}:\d{2}\b", blob))))
print("  instrument words:", [s for s in ["NAS100","US500","US30","GER40","XAU","DAX","FTSE","NK225","MT5"] if s in blob])

print("\n=== I. 'reclaim to 29,600' & support cluster numbers in L3 ===")
print(f"  M15 last close: {M15[-1]['close']}")
print("  (checked visually against L3 text: FVG stack 29,588-29,612; London low 29,546.6)")
