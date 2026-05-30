#!/usr/bin/env python3
"""HK50 Key Level Analysis using cached TradingView MCP data."""
import json, os

CACHE_DIR = os.path.expanduser("~/.hermes/data/key-level-cache/data/HK50")

# Load data from cache files
with open(os.path.join(CACHE_DIR, "D1.json")) as f:
    d1_raw = json.load(f)
d1_bars = d1_raw["data"]

with open(os.path.join(CACHE_DIR, "H4.json")) as f:
    h4_raw = json.load(f)
h4_bars = h4_raw["data"]

current_price = d1_bars[-1]["close"]
print(f"Current price: {current_price}")
print(f"D1 bars: {len(d1_bars)}, H4 bars: {len(h4_bars)}")

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
            "price": round(sum(prices) / len(prices), 1),
            "count": len(c), "type": c[0]["type"],
            "min": round(min(prices), 1), "max": round(max(prices), 1)
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

tolerances = [5, 10, 15, 20, 30, 50]

# Find swings
d1_highs = find_swing_highs(d1_bars, 2)
d1_lows = find_swing_lows(d1_bars, 2)
h4_highs = find_swing_highs(h4_bars, 3)
h4_lows = find_swing_lows(h4_bars, 3)

print(f"D1 swing highs: {len(d1_highs)}, lows: {len(d1_lows)}")
print(f"H4 swing highs: {len(h4_highs)}, lows: {len(h4_lows)}")

# Cluster (HK50 range = $30)
d1_res = cluster_levels(d1_highs, 30)
d1_sup = cluster_levels(d1_lows, 30)
h4_res = cluster_levels(h4_highs, 30)
h4_sup = cluster_levels(h4_lows, 30)

# Get nearest levels
all_res = sorted(d1_res + h4_res, key=lambda x: abs(x["price"] - current_price))[:10]
all_sup = sorted(d1_sup + h4_sup, key=lambda x: abs(x["price"] - current_price))[:10]

# Deduplicate
seen = set()
unique = []
for item in all_res + all_sup:
    key = round(item["price"], 0)
    if key not in seen:
        seen.add(key)
        unique.append(item)

# Validate on D1 first
print(f"\n{'='*60}")
print(f"  HK50 KEY LEVELS — PEPPERSTONE CFD (D1 Validation)")
print(f"  Current Price: {current_price}")
print(f"{'='*60}")

strong_levels = []
for item in sorted(unique, key=lambda x: abs(x["price"] - current_price)):
    is_res = item["price"] > current_price
    _, best = validate_level(d1_bars, item["price"], tolerances, is_res)
    lv_type = "RES" if is_res else "SUP"
    status = "✅" if best["wick_precision"] >= 70 and best["interactions"] >= 2 else "❌"
    dist = item["price"] - current_price
    print(f"  {lv_type} {item['price']} | D1: WP={best['wick_precision']}% intx={best['interactions']} rej={best['avg_rejection_pct']:.1f}% score={best['tf_composite']:.1f} (tol=±{best['tolerance']}) {status}")
    if best["wick_precision"] >= 70 and best["interactions"] >= 2:
        strong_levels.append({"price": item["price"], "type": lv_type, "d1_score": best["tf_composite"], "d1_wp": best["wick_precision"], "d1_intx": best["interactions"], "d1_rej": best["avg_rejection_pct"], "d1_tol": best["tolerance"]})

# Validate strong levels on H4 too
print(f"\n{'='*60}")
print(f"  H4 Validation + Multi-TF Scoring (D1:60% + H4:40%)")
print(f"{'='*60}")

final_levels = []
for l in strong_levels:
    is_res = l["type"] == "RES"
    _, h4_best = validate_level(h4_bars, l["price"], tolerances, is_res)
    print(f"  {l['type']} {l['price']} | D1: WP={l['d1_wp']}% score={l['d1_score']:.1f} | H4: WP={h4_best['wick_precision']}% intx={h4_best['interactions']} rej={h4_best['avg_rejection_pct']:.1f}% score={h4_best['tf_composite']:.1f}")
    weighted = l["d1_score"] * 0.60 + h4_best["tf_composite"] * 0.40
    final_levels.append({
        "price": l["price"], "type": l["type"], 
        "d1_score": l["d1_score"], "h4_score": h4_best["tf_composite"],
        "overall": round(weighted, 1),
        "d1_wp": l["d1_wp"], "h4_wp": h4_best["wick_precision"],
        "d1_intx": l["d1_intx"], "h4_intx": h4_best["interactions"]
    })

final_levels.sort(key=lambda x: abs(x["price"] - current_price))

print(f"\n{'='*60}")
print(f"  FINAL SCORED LEVELS")
print(f"{'='*60}")
for l in final_levels:
    v = "✅ HIGH" if l["overall"] >= 90 else "⚠️ MED" if l["overall"] >= 70 else "❌ LOW"
    print(f"  {l['type']} {l['price']} | Overall: {l['overall']}/100 [{v}] | D1:{l['d1_score']:.1f} H4:{l['h4_score']:.1f} | Dist: {l['price']-current_price:+.1f}")

# Plot output
print(f"\n=== PLOT OUTPUT ===")
for l in final_levels:
    if l["overall"] >= 70:
        print(f"PLOT|{l['type']}|{l['price']}|{l['overall']:.0f}")
