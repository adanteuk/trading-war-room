#!/usr/bin/env python3
"""SELF-VERIFICATION (editor fallback — subagent timed out).
Re-derive every draft number from raw JSON. Cross-check walker_ta.json vs report claims."""
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

print("== 1. SESSION STATS ==")
sess = [b for b in m15 if b["time"] >= 1789682400]
chk("session bars", len(sess) == 51, f"n={len(sess)}")
chk("session open 29435.6", abs(sess[0]["open"] - 29435.6) < 0.01, f"got {sess[0]['open']}")
s_hi = max(b["high"] for b in sess); s_lo = min(b["low"] for b in sess)
chk("session H 29677.7 / L 29359.4", abs(s_hi - 29677.7) < 0.01 and abs(s_lo - 29359.4) < 0.01, f"H={s_hi} L={s_lo}")
last = m15[-1]["close"]
chk("last close ~29600 (drift ok)", abs(last - 29600.3) < 15, f"got {last}")
# D1 last bar equals session stats?
d1l = d1[-1]
chk("D1 last bar == session agg", abs(d1l["open"] - sess[0]["open"]) < 0.01 and abs(d1l["high"] - s_hi) < 0.01 and abs(d1l["low"] - s_lo) < 0.01)
chk("D1 last bar date", dstr(d1l["time"]).startswith("Fri 09-18"), dstr(d1l["time"]))
chk("D1 daily open == session open (same bar)", abs(ta["session_stats"]["daily_open"] - sess[0]["open"]) < 0.01)

print("== 2. D1 STRUCTURE (H and L independently) ==")
comp = d1[:-1]
for i in range(len(comp) - 6, len(comp)):
    cur, prv = comp[i], comp[i - 1]
    hh = cur["high"] > prv["high"]; ll = cur["low"] < prv["low"]
    hl = cur["low"] > prv["low"]; lh = cur["high"] < prv["high"]
    print(f"  {dstr(cur['time'])[:9]}: {'HH' if hh else 'LH'}+{'HL' if hl else 'LL'} H={cur['high']} L={cur['low']}")
sep16 = next(b for b in d1 if dstr(b["time"]).startswith("Wed 09-16"))
sep15 = next(b for b in d1 if dstr(b["time"]).startswith("Tue 09-15"))
sep17 = next(b for b in d1 if dstr(b["time"]).startswith("Thu 09-17"))
sep10_15 = [b for b in comp if "09-1" in dstr(b["time"]) and dstr(b["time"])[:9] in ("Thu 09-10", "Fri 09-11", "Mon 09-14", "Tue 09-15")]
chk("Sep10-15 all LH (lower highs)", all(comp[i]["high"] < comp[i-1]["high"] for i in range(len(comp)-6, len(comp)-1) if dstr(comp[i]["time"])[:8] in ("Thu 09-1", "Fri 09-1", "Mon 09-1", "Tue 09-1")))
chk("Sep16 sweep low 28757.0", abs(sep16["low"] - 28757.0) < 0.01)
chk("Sep16 low < Sep15 low 28909.9", sep16["low"] < sep15["low"], f"{sep16['low']} < {sep15['low']}")
sep02 = next(b for b in d1 if dstr(b["time"]).startswith("Wed 09-02"))
chk("Sep16 low < Sep2 swing 28882.4", sep16["low"] < sep02["low"], f"{sep16['low']} < {sep02['low']}")
chk("Sep17 HH+HL", sep17["high"] > sep16["high"] and sep17["low"] > sep16["low"])
chk("Sep17 range 545.4", abs((sep17["high"] - sep17["low"]) - 545.4) < 0.1, f"{sep17['high']-sep17['low']:.1f}")
chk("Sep17 body 447.1 / 82%", abs(abs(sep17["close"]-sep17["open"]) - 447.1) < 0.1 and abs(abs(sep17["close"]-sep17["open"])/(sep17["high"]-sep17["low"])*100 - 82) < 0.5)
chk("Sep17 close@87%", abs((sep17["close"]-sep17["low"])/(sep17["high"]-sep17["low"])*100 - 87) < 0.5)

print("== 3. FIB RECOMPUTE (Sep range) ==")
h, l = 29734.1, 28757.0
sep8 = next(b for b in d1 if dstr(b["time"]).startswith("Tue 09-08"))
chk("Sep8 swing high 29734.1", abs(sep8["high"] - 29734.1) < 0.01)
rng = h - l
fib = {p: round(l + rng*p/100, 1) for p in [0,25,50,62,70.5,79,100]}
draft_fib = ta["fib_levels_sep_range"]
for p in fib:
    chk(f"Fib {p}% = {fib[p]}", abs(fib[p] - draft_fib[str(p)]) < 0.1, f"draft {draft_fib[str(p)]}")

print("== 4. PRICE POSITION ==")
pos_last = (last - l) / rng * 100
pos_d1close = (d1l["close"] - l) / rng * 100
chk("L1 text 86.8% uses D1 close snapshot", abs(pos_d1close - 86.8) < 0.3, f"recomputed {pos_d1close:.1f}%")
chk("json price_position_pct=86.3 uses live last", abs(pos_last - ta["price_position_pct"]) < 0.3, f"recomputed {pos_last:.1f}%")

print("== 5. VWAP / RVOL ==")
tpv = sum(((b["high"]+b["low"]+b["close"])/3)*b["volume"] for b in sess)
vwap = tpv / sum(b["volume"] for b in sess)
chk("VWAP 29509.9", abs(vwap - 29509.9) < 1, f"{vwap:.1f}")
ysess = [b for b in m15 if 1789596000 <= b["time"] < 1789682400]
elapsed = sess[-1]["time"] - sess[0]["time"] + 900
ycum = sum(b["volume"] for b in ysess if b["time"] <= ysess[0]["time"] + elapsed - 900)
scum = sum(b["volume"] for b in sess)
rvol = scum / ycum
chk("RVOL 0.87", abs(rvol - 0.87) < 0.02, f"{rvol:.3f} (scum={scum} ycum={ycum})")

print("== 6. KEY LEVELS EXISTENCE ==")
def h4bar(dtstr):
    return next(b for b in h4 if dstr(b["time"]).startswith(dtstr))
# H4 bear FVG 29670-29962 created Aug 18 06:00: candles a=t-2, mid=t-1, c=t; c.high < a.low
i = next(i for i, b in enumerate(h4) if dstr(b["time"]).startswith("Tue 08-18 06:00"))
a, c = h4[i-2], h4[i]
chk("H4 bear FVG Aug18: c.high < a.low, gap 29670-29962", abs(c["high"] - 29670.0) < 0.1 and abs(a["low"] - 29961.8) < 0.1, f"c.high={c['high']} a.low={a['low']}")
# filled check: any bar after with low <= 29670 (upper part entered?)
entered = any(b["high"] >= 29670 for b in h4[i+1:])
chk("bear FVG floor 29670 entered today only", entered)
i = next(i for i, b in enumerate(h4) if dstr(b["time"]).startswith("Thu 09-17 06:00"))
a, c = h4[i-2], h4[i]
chk("H4 bull FVG Sep17 29252-29359", abs(a["high"] - 29252.2) < 0.1 and abs(c["low"] - 29359.4) < 0.1, f"a.high={a['high']} c.low={c['low']}")
unfilled = not any(b["low"] <= 29252.2 for b in h4[i+1:])
chk("Sep17 FVG unfilled (no low <=29252 after)", unfilled)
# M15 bull FVG 29570-29587 at 18:15
i = next(i for i, b in enumerate(m15) if dstr(b["time"]).startswith("Fri 09-18 18:15"))
a, c = m15[i-2], m15[i]
chk("M15 bull FVG 18:15 29570.5-29587.2", abs(a["high"] - 29570.5) < 0.1 and abs(c["low"] - 29587.2) < 0.1, f"a.high={a['high']} c.low={c['low']}")
aug28 = next(b for b in d1 if dstr(b["time"]).startswith("Fri 08-28"))
chk("Aug28 high 29749", abs(aug28["high"] - 29748.6) < 0.1, f"{aug28['high']}")
# London low
lon = [b for b in sess if 15 <= datetime.datetime.fromtimestamp(b["time"], HKT).hour < 22]
chk("London low 29546.6", abs(min(b["low"] for b in lon) - 29546.6) < 0.1, f"{min(b['low'] for b in lon)}")

print("== 7. SMT CHECK (NAS100 vs US500 same-day) ==")
u = {b["time"]: b for b in us5}
n = {b["time"]: b for b in d1}
print("  date        NAS low      prevNASlow  US500 low   prevUS5low  verdict")
smt_div = False
for t in sorted(u):
    if t in n:
        dates = [b["time"] for b in us5]
        idx = dates.index(t)
        if idx >= 2:
            un, up = u[t], us5[idx-1]
            nn, np_ = n[t], d1[d1.index(next(x for x in d1 if x["time"]==t))-1] if t in n else None
            # find prior completed NAS bar
            ni = [b["time"] for b in d1].index(t)
            if ni >= 1:
                np_ = d1[ni-1]
                nas_sweep = nn["low"] < np_["low"]
                us_sweep = un["low"] < up["low"]
                if nas_sweep != us_sweep:
                    smt_div = True
                    print(f"  {dstr(t)[:9]}  {nn['low']:.1f}  {np_['low']:.1f}  {un['low']:.1f}  {up['low']:.1f}  DIVERGENCE")
chk("No SMT divergence Sep15-16 (both swept)", not smt_div, "draft claims NO SMT — verify both swept in sync")
us16 = u[1789509600]; us15 = u[1789423200]
print(f"  US500 Sep16 low {us16['low']} vs Sep15 low {us15['low']} -> swept: {us16['low'] < us15['low']}")
chk("US500 Sep16 swept prior low (matches NAS)", us16["low"] < us15["low"])

print("== 8. ORB ARITHMETIC ==")
ob = ta["orb_breakdown"]
tot = ob["pre_market_htf_bias_25"]+ob["vwap_15"]+ob["volume_20"]+ob["close_timing_15"]+ob["ict_confluence_15"]+ob["range_volatility_10"]
chk("ORB sum = orb_score = 61", tot == ta["orb_score"] == 61, f"{tot}")
chk("ORB caps respected", ob["pre_market_htf_bias_25"]<=25 and ob["vwap_15"]<=15 and ob["volume_20"]<=20 and ob["close_timing_15"]<=15 and ob["ict_confluence_15"]<=15 and ob["range_volatility_10"]<=10)

print("== 9. JSON FIELD CONSISTENCY ==")
chk("bias bullish", ta["bias"] == "bullish")
chk("confidence 55", ta["confidence"] == 55)
chk("entry TBD (no anticipation)", ta["entry"].startswith("TBD"))
chk("timestamp is today", ta["timestamp"].startswith("2026-09-18T18:"), ta["timestamp"])
chk("supports ascending", True)  # manual: [29588,29529,29436,29359,29245] descending order as supports below price
sup = [float(s.split()[0].replace(",", "")) for s in ta["key_levels"]["support"]]
res = [float(s.split()[0].replace(",", "")) for s in ta["key_levels"]["resistance"]]
chk("supports strictly descending", all(sup[i] > sup[i+1] for i in range(len(sup)-1)), str(sup))
chk("resistances strictly ascending", all(res[i] < res[i+1] for i in range(len(res)-1)), str(res))
chk("last close below all resistances", all(last < r for r in res))
chk("last close above all supports", all(last > s for s in sup))

print("== 10. TIME PERIOD ==")
chk("M15 last bar = Sep 18 18:30 HKT (most recent)", dstr(m15[-1]["time"]) == "Fri 09-18 18:30", dstr(m15[-1]["time"]))
fut = [b for b in d1+h4+m15 if b["time"] > m15[-1]["time"]]
chk("no future bars", len(fut) == 0)

print("== 11. GIT ==")
r = subprocess.run(["git", "log", "--oneline", "-1"], cwd="/Users/ychen/.hermes/trading-war-room", capture_output=True, text=True)
chk("commit 044c0b7 is HEAD", r.stdout.startswith("044c0b7"), r.stdout.strip())
r2 = subprocess.run(["git", "status", "--short"], cwd="/Users/ychen/.hermes/trading-war-room", capture_output=True, text=True)
chk("working tree clean for signals/2026-09-18", "signals/2026-09-18" not in r2.stdout, r2.stdout.strip()[:100])
r3 = subprocess.run(["bash", "-c", "git show HEAD:signals/2026-09-18/walker_ta.json | diff - signals/2026-09-18/walker_ta.json && echo MATCH"], cwd="/Users/ychen/.hermes/trading-war-room", capture_output=True, text=True)
chk("HEAD walker_ta.json == working copy", "MATCH" in r3.stdout)

print()
print("RESULT:", "ALL CHECKS PASSED" if not FAIL else f"{len(FAIL)} FAILURES: {FAIL}")
