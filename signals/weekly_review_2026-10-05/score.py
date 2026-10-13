#!/usr/bin/env python3
"""Score the 2026-10-05 week's NAS100 daily bias predictions against actual CFD price action.

Bias semantics (same as weekly_review_2026-09-28): directional bias issued ~18:30-19:00 HKT
(NY pre-market) targets the remainder of that CFD trading day -> score by direction of
post-issuance move (issue price vs day close). Also report candle direction + close-to-close
(pitfall #77: C2C is ground truth for weekly direction; candle color can diverge).
"""
import json, os, datetime

OUT = "/Users/ychen/.hermes/trading-war-room/signals/weekly_review_2026-10-05"
d1 = json.load(open(os.path.join(OUT, "raw_NAS100_D1.json")))
h4 = json.load(open(os.path.join(OUT, "raw_NAS100_H4.json")))
u5 = json.load(open(os.path.join(OUT, "raw_US500_D1.json")))

def sess_date(bar):
    t = datetime.datetime.fromisoformat(bar["time_utc"])
    return (t + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

d1_by_day = {sess_date(b): b for b in d1}
u5_by_day = {sess_date(b): b for b in u5}

# H4 grouped by session day (NY time): NY hour >= 17 -> next day's session
h4_by_day = {}
for b in h4:
    t_ny = datetime.datetime.fromisoformat(b["time_ny"])
    d = t_ny.date()
    if t_ny.hour >= 17:
        d = d + datetime.timedelta(days=1)
    h4_by_day.setdefault(d.isoformat(), []).append(b)

DAYS = ["2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09", "2026-10-12"]

print("=== NAS100 CFD D1 (session-day labels) ===")
prev_close = None
for day in DAYS:
    b = d1_by_day.get(day)
    if b is None:
        print(f"{day}: NO BAR")
        continue
    rng = b["high"] - b["low"]
    body = b["close"] - b["open"]
    close_pos = (b["close"] - b["low"]) / rng * 100 if rng else float("nan")
    line = (f"{day} ({datetime.date.fromisoformat(day).strftime('%a')}): "
            f"O={b['open']:.1f} H={b['high']:.1f} L={b['low']:.1f} C={b['close']:.1f} "
            f"range={rng:.1f} body={body:+.1f} close@{close_pos:.0f}%")
    if prev_close is not None:
        c2c = b["close"] - prev_close
        line += f" | c2c {c2c:+.1f} ({(b['close']/prev_close-1)*100:+.2f}%)"
    print(line)
    prev_close = b["close"]

print("\n=== Issue-time H4 context per signal ===")
def h4_bar_at(utc_iso):
    """The H4 bar whose time_utc == the 4h bucket containing utc_iso."""
    t = datetime.datetime.fromisoformat(utc_iso)
    bucket = t.replace(hour=(t.hour // 4) * 4, minute=0, second=0, microsecond=0)
    key = bucket.strftime("%Y-%m-%dT%H:00:00+00:00")
    for b in h4:
        if b["time_utc"] == key:
            return b
    return None

# issue-time prices stated in signal files (walker) or to be proxied from H4 (merlin)
issues = {
    "Mon 10-05 walker NEUTRAL conf40": {"price": 30737.6, "note": "walker l1_daily 'Current 30737.6' @10:36Z"},
    "Tue 10-06 walker BULLISH conf60": {"price": 31212.5, "note": "walker current_price @10:55Z"},
    "Wed 10-07 MERLIN* NEUTRAL conf45 (walker MISSING)": {"proxy_utc": "2026-10-07T03:00:00+00:00", "note": "merlin 11:00 HKT=03:00Z; H4 00-04Z close proxy"},
    "Thu 10-08 MERLIN* NEUTRAL conf45 (walker MISSING)": {"price": 30920.1, "note": "merlin states price 30920.1 @03:00Z; H4 00-04Z crosscheck"},
    "Fri 10-09 MERLIN* BULLISH conf55 (walker MISSING)": {"proxy_utc": "2026-10-09T11:00:00+00:00", "note": "merlin 11:00Z; H4 08-12Z close proxy"},
    "Mon 10-12 walker BEARISH conf45": {"price": 30875.9, "note": "walker l1 'now 30875.9' @10:46Z"},
}
for label, spec in issues.items():
    day = label.split()[1].replace("10-", "2026-10-")
    if "price" in spec:
        px = spec["price"]
        src = spec["note"]
    else:
        bar = h4_bar_at(spec["proxy_utc"])
        px = bar["close"] if bar else None
        src = f"{spec['note']} -> bar {bar['time_utc'] if bar else 'N/A'} C={px}"
    d1b = d1_by_day.get(day)
    if d1b is None or px is None:
        print(f"{label}: cannot compute")
        continue
    move = d1b["close"] - px
    pct = (d1b["close"] / px - 1) * 100
    print(f"{label}: issue {px:.1f} -> close {d1b['close']:.1f} | post-issue {move:+.1f} ({pct:+.2f}%) | candle {d1b['close']-d1b['open']:+.1f} | [{src}]")

print("\n=== H4 detail per session day (UTC labels as stored) ===")
for day in DAYS[1:]:
    bars = [b for b in h4 if sess_date({"time_utc": b["time_utc"]}) == day]
    if not bars:
        print(f"--- {day}: no H4 bars found (check grouping)")
        continue
    hi = max(b["high"] for b in bars); lo = min(b["low"] for b in bars)
    print(f"--- {day} ({datetime.date.fromisoformat(day).strftime('%a')}): session H={hi:.1f} L={lo:.1f}")
    for b in bars:
        t = datetime.datetime.fromisoformat(b["time_utc"])
        print(f"  {t.strftime('%H:%M')}Z: O={b['open']:.1f} H={b['high']:.1f} L={b['low']:.1f} C={b['close']:.1f}")

print("\n=== Signal-file claim checks vs actual ===")
checks = []
def ck(name, claimed, actual, ok):
    checks.append((name, claimed, actual, ok))
    print(f"  {'OK ' if ok else 'FAIL'} {name}: claimed={claimed} actual={actual}")

# Tue Oct 6 candle per merlin 10-07 claim: '93% body bearish'
t = d1_by_day.get("2026-10-06")
if t:
    rng = t["high"] - t["low"]; body = t["close"] - t["open"]
    ck("Tue 10-06 candle", f"merlin: bearish 93% body", f"body {body:+.1f} = {abs(body)/rng*100:.0f}% of range, {'bearish' if body<0 else 'bullish'}", (body < 0) and abs(body)/rng > 0.85)
# Wed Oct 7 per merlin 10-08: 'strong bearish 76% body'
w = d1_by_day.get("2026-10-07")
if w:
    rng = w["high"] - w["low"]; body = w["close"] - w["open"]
    ck("Wed 10-07 candle", "merlin: strong bearish 76% body", f"body {body:+.1f} = {abs(body)/rng*100:.0f}%, {'bearish' if body<0 else 'bullish'}", (body < 0) and abs(body)/rng > 0.6)
# ATH 31386 and which session
mx = max(d1[-15:], key=lambda b: b["high"])
mx_day = sess_date(mx)
ck("Week peak high", "merlin 10-07: ATH 31386", f"{mx['high']:.1f} on {mx_day}", abs(mx["high"] - 31386.3) < 1.5)
ck("Peak-high session date", "merlin 10-08: 'Oct 5 high 31271.3'", f"actual peak {mx_day} H={mx['high']:.1f}; Oct-5 H={d1_by_day['2026-10-05']['high']:.1f}", mx_day == "2026-10-05")
# Thu Oct 8 D1 low 30568.2 (walker 10-12 SL ref)
th = d1_by_day.get("2026-10-08")
if th:
    ck("Thu 10-08 low", "walker 10-12: 30568.2 (Oct 8 session)", f"{th['low']:.1f}", abs(th["low"] - 30568.2) < 1.5)
# Fri Oct 9: walker 10-12 claims high 31045.9 / low 30731.7 / bullish +106.5 / close@56%
f = d1_by_day.get("2026-10-09")
if f:
    rng = f["high"] - f["low"]; body = f["close"] - f["open"]
    ck("Fri 10-09 high", "walker 10-12: 31045.9", f"{f['high']:.1f}", abs(f["high"] - 31045.9) < 1.5)
    ck("Fri 10-09 low", "walker 10-12: 30731.7", f"{f['low']:.1f}", abs(f["low"] - 30731.7) < 1.5)
    ck("Fri 10-09 body", "walker 10-12: +106.5", f"{body:+.1f}", abs(body - 106.5) < 2.0)
    ck("Fri 10-09 close pos", "walker 10-12: 56% of range", f"{(f['close']-f['low'])/rng*100:.0f}%", abs((f["close"]-f["low"])/rng*100 - 56) < 3)
# Mon 10-12: walker claims Judas high 31080.0 (overnight), session low 30828.8 @10:30Z bar, close 19% of range at issue
m = d1_by_day.get("2026-10-12")
m12 = [b for b in h4 if sess_date({"time_utc": b["time_utc"]}) == "2026-10-12"]
if m12:
    hi = max(b["high"] for b in m12); lo = min(b["low"] for b in m12)
    ck("Mon 10-12 session high (Judas)", "walker 10-12: 31080.0", f"{hi:.1f}", abs(hi - 31080.0) < 1.5)
    ck("Mon 10-12 session low", "walker 10-12: 30828.8 (at issue; final L)", f"{lo:.1f}", lo <= 30828.8 + 0.5)
# Mon 10-12 close target zone: SSL 30731.7 -> 30568.2; actual close vs issue 30875.9
if m:
    print(f"  Mon 10-12 final(last H4) C={m12[-1]['close']:.1f}; walker issue 30875.9; D1 bar close(may be in-progress)={m['close']:.1f}")
# Tue 10-06: walker 'fresh 200-bar high 31225.3'; Tue session high?
tb = [b for b in h4 if sess_date({"time_utc": b["time_utc"]}) == "2026-10-06"]
if tb:
    hi = max(b["high"] for b in tb)
    ck("Tue 10-06 session high", "walker 10-06: 31225.3 (at issue 10:55Z; final H)", f"{hi:.1f}", hi >= 31225.3 - 0.5)
# US500 week (SMT context)
print("\n=== US500 D1 same days ===")
for day in DAYS:
    b = u5_by_day.get(day)
    if b:
        print(f"{day}: O={b['open']:.1f} H={b['high']:.1f} L={b['low']:.1f} C={b['close']:.1f} body={b['close']-b['open']:+.1f}")

print("\n=== Weekly summary ===")
f9 = d1_by_day.get("2026-10-09"); f2 = d1_by_day.get("2026-10-02")
if f9 and f2:
    print(f"Week (Fri2Fri close): {f2['close']:.1f} -> {f9['close']:.1f} = {(f9['close']/f2['close']-1)*100:+.2f}%")
if m12:
    print(f"Incl Mon 10-12 (last H4 close {m12[-1]['close']:.1f}): {(m12[-1]['close']/f2['close']-1)*100:+.2f}%")
print("checks passed:", sum(1 for c in checks if c[3]), "/", len(checks))
