#!/usr/bin/env python3
"""GBPUSD Key Level Analysis — Alfred MT5 full W1/D1/H4."""
import json, os

CACHE_DIR = os.path.expanduser("~/.hermes/data/key-level-cache/data/GBPUSD")

def load_data(tf):
    with open(os.path.join(CACHE_DIR, f"{tf}.json")) as f:
        raw = json.load(f)
    return raw["data"]

w1_bars = load_data("W1")
d1_bars = load_data("D1")
h4_bars = load_data("H4")

current_price = d1_bars[-1]["close"]
print(f"Current price: {current_price}")
print(f"Bars — W1: {len(w1_bars)}, D1: {len(d1_bars)}, H4: {len(h4_bars)}")

# ============================================================
# Swing detection
# ============================================================
def find_swing_highs(data, swing=2):
    swings = []
    for i in range(swing, len(data) - swing):
        if all(data[i]["high"] > data[i-j]["high"] and data[i]["high"] > data[i+j]["high"] for j in range(1, swing+1)):
            swings.append({"price": data[i]["high"], "idx": i, "time": data[i]["time"], "type": "high"})
    return swings

def find_swing_lows(data, swing=2):
    swings = []
    for i in range(swing, len(data) - swing):
        if all(data[i]["low"] < data[i-j]["low"] and data[i]["low"] < data[i+j]["low"] for j in range(1, swing+1)):
            swings.append({"price": data[i]["low"], "idx": i, "time": data[i]["time"], "type": "low"})
    return swings

def cluster_levels(swings, cluster_range):
    if not swings:
        return []
    sorted_p = sorted(swings, key=lambda x: x["price"])
    clusters = []
    current = [sorted_p[0]]
    for p in sorted_p[1:]:
        if abs(p["price"] - sum(x["price"] for x in current) / len(current)) <= cluster_range:
            current.append(p)
        else:
            clusters.append(current)
            current = [p]
    clusters.append(current)
    results = []
    for c in clusters:
        prices = [x["price"] for x in c]
        results.append({
            "price": round(sum(prices) / len(prices), 5),
            "count": len(c), "type": c[0]["type"],
            "min": round(min(prices), 5), "max": round(max(prices), 5),
            "recent_time": max(x["time"] for x in c)
        })
    return results

# ============================================================
# Wick Precision validation
# ============================================================
def validate_level(data, level, tolerances, is_res):
    results = []
    for tol in tolerances:
        interactions = 0
        wick_rejections = 0
        rejections = []
        for bar in data:
            touched = False
            if is_res:
                if bar["high"] >= level - tol and bar["high"] <= level + tol:
                    touched = True
                    body_top = max(bar["open"], bar["close"])
                    if bar["high"] > body_top:
                        wick_rejections += 1
                        bar_range = bar["high"] - bar["low"]
                        if bar_range > 0:
                            rejections.append((bar["high"] - body_top) / bar_range * 100)
            else:
                if bar["low"] >= level - tol and bar["low"] <= level + tol:
                    touched = True
                    body_bottom = min(bar["open"], bar["close"])
                    if bar["low"] < body_bottom:
                        wick_rejections += 1
                        bar_range = bar["high"] - bar["low"]
                        if bar_range > 0:
                            rejections.append((body_bottom - bar["low"]) / bar_range * 100)
            if touched:
                interactions += 1
        wp = (wick_rejections / interactions * 100) if interactions > 0 else 0
        avg_rej = sum(rejections) / len(rejections) if rejections else 0
        wp_score = min(wp, 100)
        intx_score = 100 if interactions >= 2 else (50 if interactions == 1 else 0)
        rej_score = min(avg_rej / 30 * 100, 100)
        tf_composite = wp_score * 0.50 + intx_score * 0.30 + rej_score * 0.20
        results.append({
            "tolerance": tol, "interactions": interactions,
            "wick_rejections": wick_rejections, "wick_precision": round(wp, 1),
            "avg_rejection_pct": round(avg_rej, 3), "tf_composite": round(tf_composite, 1),
        })
    best = max(results, key=lambda x: x["wick_precision"])
    return results, best

# GBPUSD: ~1.34 range, use pips-based tolerances
# 1 pip = 0.0001, 5 pips = 0.0005, 10 pips = 0.0010, etc.
# Testing: ±0.0005 (5 pips), ±0.0010 (10 pips), ±0.0015 (15 pips), ±0.0020 (20 pips), ±0.0030 (30 pips), ±0.0050 (50 pips)
tolerances = [0.0005, 0.0010, 0.0015, 0.0020, 0.0030, 0.0050]

# Cluster range for forex: 0.005 (50 pips)
cluster_range = 0.005

# Swing detection
w1_highs = find_swing_highs(w1_bars, 1)
w1_lows = find_swing_lows(w1_bars, 1)
d1_highs = find_swing_highs(d1_bars, 2)
d1_lows = find_swing_lows(d1_bars, 2)
h4_highs = find_swing_highs(h4_bars, 3)
h4_lows = find_swing_lows(h4_bars, 3)

print(f"W1 swings: highs={len(w1_highs)}, lows={len(w1_lows)}")
print(f"D1 swings: highs={len(d1_highs)}, lows={len(d1_lows)}")
print(f"H4 swings: highs={len(h4_highs)}, lows={len(h4_lows)}")

# Cluster
w1_res = cluster_levels(w1_highs, cluster_range)
w1_sup = cluster_levels(w1_lows, cluster_range)
d1_res = cluster_levels(d1_highs, cluster_range)
d1_sup = cluster_levels(d1_lows, cluster_range)
h4_res = cluster_levels(h4_highs, cluster_range)
h4_sup = cluster_levels(h4_lows, cluster_range)

print(f"W1 clusters: RES={len(w1_res)}, SUP={len(w1_sup)}")
print(f"D1 clusters: RES={len(d1_res)}, SUP={len(d1_sup)}")
print(f"H4 clusters: RES={len(h4_res)}, SUP={len(h4_sup)}")

# Get nearest 8 each side per TF
def get_nearest(clusters, price, limit=8):
    return sorted(clusters, key=lambda x: abs(x["price"] - price))[:limit]

candidates = []
for r in get_nearest(w1_res + d1_res + h4_res, current_price):
    candidates.append({"price": r["price"], "type": "RES"})
for s in get_nearest(w1_sup + d1_sup + h4_sup, current_price):
    candidates.append({"price": s["price"], "type": "SUP"})

# Deduplicate
seen = set()
unique = []
for c in sorted(candidates, key=lambda x: abs(x["price"] - current_price)):
    key = round(c["price"], 4)
    if key not in seen:
        seen.add(key)
        unique.append(c)

print(f"\nCandidate levels: {len(unique)}")
for c in unique[:15]:
    print(f"  {c['type']} {c['price']} | dist: {(c['price']-current_price)*10000:+.1f} pips")

# ============================================================
# Multi-TF validation (W1=50%, D1=30%, H4=20%)
# ============================================================
print(f"\n{'='*70}")
print(f"  GBPUSD KEY LEVELS — ALFRED MT5 (Pepperstone CFD)")
print(f"  Current Price: {current_price}")
print(f"{'='*70}")

scored = []
for c in unique[:15]:
    is_res = c["type"] == "RES"
    _, w1_best = validate_level(w1_bars, c["price"], tolerances, is_res)
    _, d1_best = validate_level(d1_bars, c["price"], tolerances, is_res)
    _, h4_best = validate_level(h4_bars, c["price"], tolerances, is_res)
    
    overall = w1_best["tf_composite"] * 0.50 + d1_best["tf_composite"] * 0.30 + h4_best["tf_composite"] * 0.20
    overall = round(overall, 1)
    
    v = "✅ HIGH" if overall >= 90 else "⚠️ MED" if overall >= 70 else "❌ LOW"
    print(f"  {c['type']} {c['price']} | Overall: {overall}/100 [{v}] | "
          f"W1:{w1_best['tf_composite']:.0f}({w1_best['interactions']}x±{w1_best['tolerance']*10000:.0f}pip) "
          f"D1:{d1_best['tf_composite']:.0f}({d1_best['interactions']}x±{d1_best['tolerance']*10000:.0f}pip) "
          f"H4:{h4_best['tf_composite']:.0f}({h4_best['interactions']}x±{h4_best['tolerance']*10000:.0f}pip)")
    
    scored.append({
        "price": c["price"], "type": c["type"],
        "overall": overall,
        "w1_score": w1_best["tf_composite"], "w1_wp": w1_best["wick_precision"], "w1_intx": w1_best["interactions"], "w1_tol": w1_best["tolerance"],
        "d1_score": d1_best["tf_composite"], "d1_wp": d1_best["wick_precision"], "d1_intx": d1_best["interactions"], "d1_tol": d1_best["tolerance"],
        "h4_score": h4_best["tf_composite"], "h4_wp": h4_best["wick_precision"], "h4_intx": h4_best["interactions"], "h4_tol": h4_best["tolerance"]
    })

# Sort by distance
scored.sort(key=lambda x: abs(x["price"] - current_price))

print(f"\n{'='*70}")
print(f"  SCORED LEVELS (sorted by distance)")
print(f"{'='*70}")
for l in scored:
    v = "✅ HIGH" if l["overall"] >= 90 else "⚠️ MED" if l["overall"] >= 70 else "❌ LOW"
    print(f"  {l['type']} {l['price']} | {l['overall']}/100 [{v}] | "
          f"W1:{l['w1_score']:.0f} D1:{l['d1_score']:.0f} H4:{l['h4_score']:.0f} | "
          f"Dist: {(l['price']-current_price)*10000:+.1f} pips")

# Plot output — high confidence only (≥90)
print(f"\n=== PLOT OUTPUT ===")
high_conf = [l for l in scored if l["overall"] >= 90]
if not high_conf:
    high_conf = scored[:6]

for l in high_conf:
    print(f"PLOT|{l['type']}|{l['price']}|{l['overall']:.0f}")
