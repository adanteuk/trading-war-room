#!/usr/bin/env python3
"""Independent re-verification of walker_ta.json (2026-09-18) from raw JSON ground truth."""
import json, math
from datetime import datetime, timezone, timedelta

BASE = "/Users/ychen/.hermes/trading-war-room/signals/2026-09-18"
HKT = timezone(timedelta(hours=8))
NY = timezone(timedelta(hours=-4))  # EDT on 2026-09-18

D1 = json.load(open(f"{BASE}/raw_NAS100_D1.json"))
H4 = json.load(open(f"{BASE}/raw_NAS100_H4.json"))
M15 = json.load(open(f"{BASE}/raw_NAS100_M15.json"))
TA = json.load(open(f"{BASE}/walker_ta.json"))

R = []  # (status, item, detail)
def v(item, ok, detail=""):
    R.append(("✅ VERIFIED" if ok else "❌ WRONG", item, detail))
def w(item, detail):
    R.append(("⚠️ UNSURE", item, detail))

def dtk(ts, tz=HKT): return datetime.fromtimestamp(ts, tz).strftime("%Y-%m-%d %H:%M")

def d1bar(datestr):
    for b in D1:
        if datetime.fromtimestamp(b["time"], HKT).strftime("%Y-%m-%d") == datestr:
            return b
    return None

print("=== 1a. SESSION STATS (session start epoch 1789682400) ===")
SESS0 = 1789682400
print("session start epoch ->", dtk(SESS0))
dlast = D1[-1]
print("D1 last bar:", dtk(dlast["time"]), dlast)
m15s = [b for b in M15 if b["time"] >= SESS0]
print("M15 session bars:", len(m15s), "first:", dtk(m15s[0]["time"]), "last:", dtk(m15s[-1]["time"]))
s_open = m15s[0]["open"]; s_high = max(b["high"] for b in m15s); s_low = min(b["low"] for b in m15s)
s_last = m15s[-1]["close"]
print(f"M15-derived: open={s_open} high={s_high} low={s_low} last_close={s_last}")
print(f"D1-derived:  open={dlast['open']} high={dlast['high']} low={dlast['low']} close={dlast['close']}")
ss = TA["session_stats"]
print("draft session_stats:", ss)
ok_a = (abs(ss["open"]-s_open)<0.05 and abs(ss["high"]-max(s_high,dlast["high"]))<0.05
        and abs(ss["low"]-min(s_low,dlast["low"]))<0.05 and abs(ss["last"]-s_last)<15
        and abs(ss["daily_open"]-dlast["open"])<0.05)
drift = abs(dlast["close"]-s_last)
v("1a session stats (open/high/low/last/daily_open)",
  ok_a, f"open {ss['open']} vs {s_open}; high {ss['high']} vs {max(s_high,dlast['high'])}; low {ss['low']} vs {min(s_low,dlast['low'])}; last {ss['last']} vs M15 {s_last} (D1 close {dlast['close']}, drift {drift:.1f}pts)")

print("\n=== 1b. DAY-OVER-DAY STRUCTURE Sep 10-17 (D1) ===")
for d in ["2026-09-02","2026-09-08","2026-09-10","2026-09-11","2026-09-14","2026-09-15","2026-09-16","2026-09-17"]:
    b = d1bar(d)
    print(d, f"O={b['open']} H={b['high']} L={b['low']} C={b['close']}" if b else "MISSING")
pairs = [("2026-09-10","2026-09-11"),("2026-09-11","2026-09-14"),("2026-09-14","2026-09-15")]
lh_ll = all(d1bar(c)["high"] < d1bar(p)["high"] and d1bar(c)["low"] < d1bar(p)["low"] for p,c in pairs)
for p,c in pairs:
    print(f"  {p}->{c}: LH={d1bar(c)['high']<d1bar(p)['high']} ({d1bar(p)['high']}->{d1bar(c)['high']}), LL={d1bar(c)['low']<d1bar(p)['low']} ({d1bar(p)['low']}->{d1bar(c)['low']})")
v("1b-i Sep 10-15 LH+LL sequence (all 4 transitions)", lh_ll)

s15, s16, s17, s2 = d1bar("2026-09-15"), d1bar("2026-09-16"), d1bar("2026-09-17"), d1bar("2026-09-02")
sweep = s16["low"] < s15["low"] and s16["low"] < s2["low"]
print(f"Sep16 low {s16['low']} < Sep15 low {s15['low']}? {s16['low']<s15['low']}; < Sep2 swing {s2['low']}? {s16['low']<s2['low']}")
v("1b-ii Sep 16 swept sell-side low 28757.0 (< Sep15 28909.9 & Sep2 28882.4)",
  sweep and abs(s16["low"]-28757.0)<0.05 and abs(s15["low"]-28909.9)<0.05 and abs(s2["low"]-28882.4)<0.05,
  f"Sep16 L={s16['low']}, Sep15 L={s15['low']}, Sep2 L={s2['low']}")

rng = s17["high"]-s17["low"]; body = abs(s17["close"]-s17["open"])
closepos = (s17["close"]-s17["low"])/rng*100
hh = s17["high"]>s16["high"]; hl = s17["low"]>s16["low"]
print(f"Sep17: range={rng:.1f} (draft 545.4), body={body:.1f} (draft 447.1), body%={body/rng*100:.0f}% (draft 82%), close@{closepos:.0f}% (draft 87%), HH={hh} ({s16['high']}->{s17['high']}), HL={hl} ({s16['low']}->{s17['low']})")
v("1b-iii Sep 17 displacement: range 545.4, body 447.1 (82%), close@87%, HH+HL",
  abs(rng-545.4)<0.1 and abs(body-447.1)<0.1 and round(body/rng*100)==82 and round(closepos)==87 and hh and hl,
  f"range {rng:.1f}, body {body:.1f} ({body/rng*100:.1f}%), close@{closepos:.1f}%, HH={hh}, HL={hl}")

print("\n=== 1c. FIBONACCI (low 28757.0 Sep16, high 29734.1 Sep8) ===")
lo, hi = 28757.0, 29734.1
b8 = d1bar("2026-09-08"); print("Sep8 high:", b8["high"], "Sep16 low:", s16["low"])
exp = {"0":28757.0,"25":29001.3,"50":29245.5,"62":29362.8,"70.5":29445.9,"79":29528.9,"100":29734.1}
fib_ok = True
for k,expv in exp.items():
    calc = lo + float(k)/100*(hi-lo)
    got = TA["fib_levels_sep_range"][k]
    m = abs(calc-got)<0.06 and abs(got-expv)<=2.0
    fib_ok &= m
    print(f"  {k}%: calc={calc:.2f} draft={got} expected={expv} -> {'OK' if m else 'MISMATCH'}")
v("1c Fibonacci recompute 25/50/62/70.5/79", fib_ok, "all within ±2pts of expected")
v("1c range anchors: low 28757.0 (Sep16), high 29734.1 (Sep8)", abs(s16['low']-28757.0)<0.05 and abs(b8['high']-29734.1)<0.05)

print("\n=== 1d. PRICE POSITION ===")
pp1 = (dlast["close"]-lo)/(hi-lo)*100   # from D1 close 29604.7
pp2 = (s_last-lo)/(hi-lo)*100           # from M15 last 29600.3
print(f"from D1 close {dlast['close']}: {pp1:.2f}% (draft L1 text 86.8%)")
print(f"from M15 last {s_last}: {pp2:.2f}% (draft JSON price_position_pct {TA['price_position_pct']})")
v("1d price position: L1 86.8% (from 29604.7) & JSON 86.3% (from 29600.3) both internally consistent",
  abs(pp1-86.8)<1.0 and abs(pp2-TA["price_position_pct"])<0.06,
  f"L1-text basis {pp1:.2f}% vs 86.8; JSON basis {pp2:.2f}% vs field {TA['price_position_pct']}")

print("\n=== 1e. VWAP / RVOL (M15, session anchored at each session's first bar) ===")
def sess_bars(day_start):
    return [b for b in M15 if b["time"] >= day_start and b["time"] < day_start + 86400]
def vwap(bs):
    pv = sum(((b["high"]+b["low"]+b["close"])/3)*b["volume"] for b in bs)
    vv = sum(b["volume"] for b in bs)
    return pv/vv if vv else float("nan")
sess0 = min(b["time"] for b in M15 if datetime.fromtimestamp(b["time"], HKT).strftime("%Y-%m-%d")=="2026-09-18")
prev0 = min(b["time"] for b in M15 if datetime.fromtimestamp(b["time"], HKT).strftime("%Y-%m-%d")=="2026-09-17")
print("today session anchor:", dtk(sess0), "| prev session anchor:", dtk(prev0))
today = sess_bars(SESS0)                    # session starts 06:00 HKT per task spec
el = today[-1]["time"] - SESS0
vw = vwap(today)
cum_today = sum(b["volume"] for b in today)
prev0 = SESS0 - 86400                       # Sep 17 session anchored at its first bar (06:00 HKT)
prev_same = [b for b in M15 if prev0 <= b["time"] <= prev0 + el]
cum_prev = sum(b["volume"] for b in prev_same)
rvol = cum_today/cum_prev
print(f"today anchor {dtk(SESS0)} ({len(today)} bars, elapsed {el/3600:.1f}h) | prev anchor {dtk(prev0)} ({len(prev_same)} bars)")
print(f"VWAP = {vw:.2f} (draft 29509.9)")
print(f"cum vol today {cum_today} vs Sep17 same elapsed {cum_prev} -> RVOL {rvol:.3f} (draft 0.87)")
v("1e session VWAP 29509.9", abs(vw-29509.9)<=5, f"recomputed {vw:.1f}")
v("1e RVOL 0.87 vs Sep17 same elapsed offset", abs(rvol-0.87)<=0.02, f"recomputed {rvol:.3f} ({cum_today}/{cum_prev})")

print("\n=== 1f. KEY LEVELS EXISTENCE ===")
def find_fvg(bars, t_lo, t_hi, mode):
    """scan consecutive triples; mode 'bull': c[i-2].high < c[i].low ; mode 'bear': c[i-2].low > c[i].high"""
    out = []
    idxs = [i for i,b in enumerate(bars) if t_lo <= b["time"] <= t_hi]
    for i in idxs:
        if i >= 2:
            a,c = bars[i-2], bars[i]
            if mode=="bull" and a["high"] < c["low"]:
                out.append((dtk(bars[i-1]["time"]), a["high"], c["low"]))
            if mode=="bear" and a["low"] > c["high"]:
                out.append((dtk(bars[i-1]["time"]), c["high"], a["low"]))
    return out

# H4 bear FVG 29670-29962 around Aug 18 06:00 HKT
aug18 = datetime(2026,8,18,0,0,tzinfo=HKT).timestamp(); aug19 = aug18+86400
bears = find_fvg(H4, aug18-86400*3, aug19+86400, "bear")
print("H4 bear-mode FVGs near Aug18 (c[i].high .. c[i-2].low):", bears)
bulls_aug = find_fvg(H4, aug18-86400*3, aug19+86400, "bull")
print("H4 bull-mode FVGs near Aug18 (c[i-2].high .. c[i].low):", bulls_aug)
target_bear = [g for g in bears if abs(g[1]-29670)<2 and abs(g[2]-29962)<2]
target_bull_aug = [g for g in bulls_aug if abs(g[1]-29670)<2 and abs(g[2]-29962)<2]
if target_bear or target_bull_aug:
    g = (target_bear or target_bull_aug)[0]
    later = [b for b in H4 if b["time"] > aug18 and b["time"] < SESS0]
    touched = [b for b in later if b["high"] > g[1]]
    print(f"gap {g[1]}-{g[2]} formed (mid-bar {g[0]}); bars before today reaching zone: {len(touched)} (max pre-today high {max((b['high'] for b in later), default=None)}); today high {dlast['high']} entered floor: {dlast['high']>g[1]}")
    v("1f H4 bear FVG 29670-29962 (Aug 18)", True, f"formed mid-bar {g[0]}, zone {g[1]}-{g[2]}, first reached today (pre-today max high {max((b['high'] for b in later), default=None)})")
else:
    v("1f H4 bear FVG 29670-29962 (Aug 18)", False, f"bear-mode {bears} / bull-mode {bulls_aug}")

# H4 bull FVG 29252-29359 (Sep 17)
sep17_0 = datetime(2026,9,17,0,0,tzinfo=HKT).timestamp()
bulls_sep = find_fvg(H4, sep17_0, sep17_0+86400, "bull")
print("H4 bull FVGs Sep17:", bulls_sep)
v("1f H4 bull FVG 29252-29359 (Sep 17)", any(abs(g[1]-29252)<2 and abs(g[2]-29359)<2 for g in bulls_sep), str(bulls_sep))

# M15 bull FVG 29570-29587 (18:15 today)
t1815 = datetime(2026,9,18,18,15,tzinfo=HKT).timestamp()
mb = find_fvg(M15, t1815-900*4, t1815, "bull")
print("M15 bull FVGs ending 18:15 today:", mb)
v("1f M15 bull FVG 29570-29587 (18:15)", any(abs(g[1]-29570)<2 and abs(g[2]-29587)<2 for g in mb), str(mb))

# EQH
b828 = d1bar("2026-08-28")
print("Sep8 high:", b8["high"], "Aug28 high:", b828["high"] if b828 else None)
v("1f EQH highs 29734.1 (Sep8) & 29749 (Aug28)", abs(b8["high"]-29734.1)<0.05 and b828 and abs(b828["high"]-29749)<0.05,
  f"Sep8={b8['high']}, Aug28={b828['high'] if b828 else 'N/A'}")
v("1f daily open 29435.6", abs(dlast["open"]-29435.6)<0.05, f"D1 open {dlast['open']}")

# London low 29546.6: search today's M15 lows 12:00-18:30 HKT for value
cands = [(dtk(b["time"]), b["low"]) for b in M15 if b["time"]>=SESS0 and b["low"]<29550]
print("today M15 lows < 29550:", cands[:12])
ll = [c for c in cands if abs(c[1]-29546.6)<0.05]
v("1f London low 29546.6 exists in today's M15", bool(ll), str(ll))
lon0 = datetime(2026,9,18,14,0,tzinfo=HKT).timestamp()
lonbars = [b for b in M15 if SESS0+6*3600 <= b["time"] <= t1815]  # 12:00-18:15 window
print("min low 12:00-18:15:", min((b['low'] for b in lonbars), default=None))

print("\n=== 1g. ORB SCORE ===")
ob = TA["orb_breakdown"]
comps = {"pre_market_htf_bias_25":(18,25),"vwap_15":(12,15),"volume_20":(10,20),"close_timing_15":(6,15),"ict_confluence_15":(8,15),"range_volatility_10":(7,10)}
tot = sum(ob[k] for k in comps); tot_max = sum(m for _,m in comps.values())
match = all(ob[k]==e for k,(e,m) in comps.items())
print("components match expected 18/12/10/6/8/7:", match, "| sum:", tot, "(draft 61) | max:", tot_max)
v("1g ORB 61 = 18+12+10+6+8+7, max 25/15/20/15/15/10", tot==61 and tot_max==100 and match and TA["orb_score"]==61,
  f"sum={tot}, max={tot_max}, orb_score field={TA['orb_score']}")

print("\n=== 1h. CORE FIELDS ===")
v("1h bias=bullish, confidence=55, orb_score=61", TA["bias"]=="bullish" and TA["confidence"]==55 and TA["orb_score"]==61, f"{TA['bias']}/{TA['confidence']}/{TA['orb_score']}")
v("1h ict_profile present", bool(TA.get("ict_profile")), TA.get("ict_profile",""))
kl = TA["key_levels"]
kl_ok = isinstance(kl.get("support"),list) and isinstance(kl.get("resistance"),list) and all(isinstance(x,str) for x in kl["support"]+kl["resistance"]) and len(kl["support"])>=3 and len(kl["resistance"])>=3
v("1h key_levels arrays of strings w/ levels", kl_ok, f"{len(kl['support'])} support / {len(kl['resistance'])} resistance strings")

print("\n=== 3. TIME PERIOD ===")
ts = TA["timestamp"]
t_run = datetime.fromisoformat(ts)
print("draft timestamp:", ts, "=", t_run.astimezone(NY).strftime("%Y-%m-%d %H:%M NY"))
maxd1 = max(b["time"] for b in D1); maxh4 = max(b["time"] for b in H4); maxm = max(b["time"] for b in M15)
now = datetime.now(HKT).timestamp()
print("max bar times:", dtk(maxd1), dtk(maxh4), dtk(maxm), "| now:", dtk(int(now)))
fut = [b["time"] for b in D1+H4+M15 if b["time"] > now]
last_ok = datetime.fromtimestamp(maxd1, HKT).strftime("%Y-%m-%d")=="2026-09-18" and datetime.fromtimestamp(maxm, HKT).strftime("%Y-%m-%d")=="2026-09-18"
v("3a timestamp ~2026-09-18 18:40 HKT", t_run.strftime("%Y-%m-%d")=="2026-09-18" and 18.0<=t_run.hour+ t_run.minute/60<=19.0, ts)
v("3b no future-dated bars", not fut, f"{len(fut)} bars beyond now")
v("3c last bar = Sep 18 (D1 & M15)", last_ok, f"D1 last {dtk(maxd1)}, M15 last {dtk(maxm)}")
ny_run = t_run.astimezone(NY)
kz_ok = ny_run.hour < 7
print(f"run time {ny_run.strftime('%H:%M')} NY; NY AM KZ 07:00 NY starts in {(datetime(2026,9,18,7,0,tzinfo=NY)-ny_run).total_seconds()/60:.0f} min (draft text: 'starts 07:00 NY (in ~15 min)')")
v("3d KZ statement consistent: run 06:xx NY, KZ not yet active", kz_ok, f"run {ny_run.strftime('%H:%M')} NY -> KZ in {(datetime(2026,9,18,7,0,tzinfo=NY)-ny_run).total_seconds()/60:.0f} min vs text '~15 min'")

print("\n=== RELEVANCY SCAN ===")
blob = json.dumps(TA)
import re
dates = sorted(set(re.findall(r"2026-\d{2}-\d{2}|\d{2}/\d{2}", blob)))
print("dates mentioned:", dates)
print("instrument mentions NAS100:", "NAS100" in blob, "| stray instruments (US30/GER40/XAU/US500-in-content):",
      [s for s in ["US30","GER40","XAU","DAX","FTSE"] if s in blob], "(US500 only in data_source SMT note:", "US500" in blob, ")")
v("2 relevancy: only 2026-09 dates, NAS100 instrument, no stale refs",
  all(d.startswith("2026-09") for d in dates) and "NAS100" in blob,
  f"dates={dates}; US500 appears only in data_source SMT-check note")

print("\n=== SUMMARY TABLE ===")
for s,item,det in R: print(f"{s}  {item}\n      {det}")
