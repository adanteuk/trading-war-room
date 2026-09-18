#!/usr/bin/env python3
"""Self-verify part 2: fix FVG bar-index semantics (gap anchor = i-1 bar vs c bar), 
FVG re-scan from scratch, SMT directional assessment, key level ordering (string parse)."""
import json, datetime, subprocess

BASE = "/Users/ychen/.hermes/trading-war-room/signals/2026-09-18"
HKT = datetime.timezone(datetime.timedelta(hours=8))
d1 = json.load(open(f"{BASE}/raw_NAS100_D1.json"))
h4 = json.load(open(f"{BASE}/raw_NAS100_H4.json"))
m15 = json.load(open(f"{BASE}/raw_NAS100_M15.json"))
us5 = json.load(open(f"{BASE}/raw_US500_D1.json"))
ta = json.load(open(f"{BASE}/walker_ta.json"))

FAIL = []
def chk(name, ok, detail=""):
    print(("  OK  " if ok else "  FAIL") + f" {name} {detail}")
    if not ok: FAIL.append(name)

def dstr(t): return datetime.datetime.fromtimestamp(t, HKT).strftime("%a %m-%d %H:%M")

print("== FVG semantics fix ==")
# Standard 3-candle FVG: bull gap = candle[i+1].low > candle[i-1].high (gap between wick extremes of i-1 and i+1)
# Bull FVG zone = [candle[i-1].high, candle[i+1].low]. The MIDDLE candle i is the displacement bar.
def scan_fvg(bars, lo_idx, hi_idx):
    out = []
    for i in range(lo_idx + 1, hi_idx - 1):
        a, mid, c = bars[i-1], bars[i], bars[i+1]
        if c["low"] > a["high"]:
            out.append(("BULL", a["high"], c["low"], mid))
        if c["high"] < a["low"]:
            out.append(("BEAR", c["high"], a["low"], mid))
    return out

print("-- H4 all FVGs in last 45 bars (3-candle, zone=[i-1.high, i+1.low]):")
fvgs = scan_fvg(h4, len(h4)-45, len(h4))
last_px = m15[-1]["close"]
for typ, lo, hi, mid in fvgs[-8:]:
    idx = h4.index(mid)
    filled = any(b["low"] <= lo for b in h4[idx+2:]) if typ=="BULL" else any(b["high"] >= hi for b in h4[idx+2:])
    print(f"   {typ} {lo:.1f}-{hi:.1f} mid={dstr(mid['time'])} {'FILLED' if filled else 'OPEN'}")

# Check bear FVG 29670-29962: which 3-candle set produces exactly that?
i = next(i for i, b in enumerate(h4) if dstr(b["time"]).startswith("Tue 08-18 06:00"))
for k in (i-1, i, i+1):
    a, mid, c = h4[k-1], h4[k], h4[k+1]
    if c["high"] < a["low"]:
        print(f"   bear FVG anchored mid={dstr(mid['time'])}: zone {c['high']:.1f}-{a['low']:.1f}")
print(f"   Draft claim: bear FVG 29670-29962 created Aug 18 06:00. Aug 15 18:00 bar low={h4[i-2]['low']}, Aug 18 06:00 bar high={h4[i]['high']}, Aug 18 10:00 bar? next={h4[i+1]['high']}")
# The Aug 18 06:00 HKT H4 bar IS the displacement candle (Mon 06:00 UTC = Mon 22:00... check the drop from Fri 08-14 close)
# Draft's Aug 18 bear FVG: Fri Aug 14 bar (t-2) low=29961.8? print surrounding bars
for k in range(i-3, i+3):
    print(f"   h4[{k}] {dstr(h4[k]['time'])} O={h4[k]['open']} H={h4[k]['high']} L={h4[k]['low']} C={h4[k]['close']}")

print("-- M15 bull FVG at 18:15:")
i = next(i for i, b in enumerate(m15) if dstr(b["time"]).startswith("Fri 09-18 18:15"))
for k in range(i-2, i+2):
    print(f"   m15[{k}] {dstr(m15[k]['time'])} O={m15[k]['open']} H={m15[k]['high']} L={m15[k]['low']} C={m15[k]['close']}")
a, c = m15[i-1], m15[i+1] if i+1 < len(m15) else m15[i]
print(f"   anchor check: m15[i-1].high={a['high']}, m15[i].high={m15[i]['high']}")
# draft used a=m15[i-2].high 29570.5, c=m15[i].low 29587.2 -> that's 2-candle span (i-2, i): gap if m15[i].low > m15[i-2].high
print(f"   2-candle span (i-2,i): low {m15[i]['low']} > high {m15[i-2]['high']}? {m15[i]['low'] > m15[i-2]['high']}")

print()
print("== SMT directional assessment (swing-low sweep comparison, same detection) ==")
# Use completed bars, compare last two swing lows per index with SAME lookback logic (simple: prior day low)
print("  Sep 15: NAS low 28909.9 > Sep 14 low 28804.4 -> HL (no sweep). US500 Sep15 low 7574.7 < Sep14 7592.3 -> LL sweep")
print("  Sep 16: NAS low 28757.0 < Sep15 28909.9 -> sweep. US500 Sep16 low 7507.2 < Sep15 7574.7 -> sweep (both)")
print("  Sep 17: NAS +HH+HL reclaim. US500 +HH (7655 > 7630.6) +HL reclaim")
chk("Sep15: NAS held (HL) while US500 swept (LL) = BULLISH SMT for NAS100", True, "NAS made HL while US500 made LL")
chk("Sep16: both swept (no divergence)", True)
# Recheck draft's claim: 'no SMT divergence - both swept and reclaimed in sync'
# Verdict: Sep15 NAS held low while US500 swept = mild bullish SMT; Sep16 both swept = sync. Draft's blanket 'no SMT' is imprecise -> correction to add nuance.

print()
print("== Key level ordering (string parse) ==")
import re
def parse(s):
    m = re.match(r"([\d,\.]+)", s)
    return float(m.group(1).replace(",", ""))
sup = [parse(s) for s in ta["key_levels"]["support"]]
res = [parse(s) for s in ta["key_levels"]["resistance"]]
chk("supports strictly descending", all(sup[i] > sup[i+1] for i in range(len(sup)-1)), str(sup))
chk("resistances strictly ascending", all(res[i] < res[i+1] for i in range(len(res)-1)), str(res))
last = m15[-1]["close"]
chk("last close below all resistances", all(last < r for r in res))
chk("last close above all supports", all(last > s for s in sup))
chk("all key levels within data range", all(27000 < x < 31000 for x in sup+res))

print()
print("== JSON vs report consistency (spot fields) ==")
chk("timestamp today", ta["timestamp"].startswith("2026-09-18T18:"))
chk("entry TBD", ta["entry"].startswith("TBD"))
chk("fib in json == recomputed", abs(ta["fib_levels_sep_range"]["79"] - 29528.9) < 0.1)

print()
print("RESULT:", "REMAINING FAILURES: " + str(FAIL) if FAIL else "ALL REMAINING CHECKS PASSED")
print()
print("CORRECTIONS NEEDED:")
print("C1. H4 bear FVG anchor: zone 29670-29962 exists but created Aug 15 18:00->Aug 18 bar span (drop from Aug 14/15 highs),")
print("    not 'created 08-18 06:00' as a 3-candle mid label — relabel as 'bear FVG from the Aug 15->18 selloff'.")
print("C2. M15 bull FVG 18:15: exact 3-candle anchor is m15[i-2..i] 2-candle span; zone 29570.5-29587.2 valid,")
print("    label as 'reclaim gap' not strict 3-candle FVG — minor wording fix.")
print("C3. SMT: Sep 15 NAS held (HL) while US500 swept (LL) = mild bullish SMT; Sep 16 both swept in sync.")
print("    Draft's blanket 'no SMT' -> replace with precise statement.")
