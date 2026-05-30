#!/usr/bin/env python3
"""
NAS100 / Any Symbol Key Level Analysis — Multi-TF Weighted Scoring (W1/D1/H4)
Uses Ian's Key Level methodology v1.6.0

Usage: python3 analyze_key_levels.py <SYMBOL> [CLUSTER_RANGE]
  SYMBOL: e.g., NAS100, GER40, XAUUSD (data must exist in cache)
  CLUSTER_RANGE: optional fixed-dollar range for clustering (default: auto-detected)

Data must be pre-fetched and saved to:
  ~/.hermes/data/key-level-cache/data/{SYMBOL}/{W1,D1,H4}.json

Outputs:
  - Console: scored levels with breakdown
  - File: ~/.hermes/data/key-level-cache/results/{SYMBOL}.json
  - PLOT| lines for downstream chart plotting
"""

import json, os, sys
from datetime import datetime, timezone

# ============================================================
# Configuration
# ============================================================

CACHE_DIR = os.path.expanduser("~/.hermes/data/key-level-cache")

# Auto-detect cluster range by symbol
CLUSTER_RANGES = {
    "JPN225": 50, "GER40": 30, "NAS100": 30, "US500": 30, "HK50": 30,
    "BTCUSD": 500, "XAUUSD": 5, "USOIL": 2,
    "AUDJPY": 0.5, "EURUSD": 0.5,
}
}

TOLERANCES_BY_INSTRUMENT = {
    "JPN225": [5, 10, 15, 20, 30, 50],
    "GER40": [5, 10, 15, 20, 30, 50],
    "NAS100": [5, 10, 15, 20, 30, 50],
    "HK50": [5, 10, 15, 20, 30, 50],
    "US500": [5, 10, 15, 20, 30, 50],
    "TWN": [5, 10, 15, 20, 30, 50],  # SGX FTSE Taiwan Index Futures (~3K-4K)
    "BTCUSD": [100, 200, 300, 500, 750, 1000],
    "XAUUSD": [2, 5, 10, 15, 20, 30],
    "USOIL": [0.5, 1, 2, 3, 5, 10],
    "AUDJPY": [5, 10, 15, 20, 30, 50],
    "EURUSD": [5, 10, 15, 20, 30, 50],
}

# ============================================================
# Data Loading
# ============================================================

def load_data(symbol, tf):
    fpath = os.path.join(CACHE_DIR, "data", symbol, f"{tf}.json")
    if not os.path.exists(fpath):
        print(f"❌ No data: {fpath}")
        return None
    with open(fpath) as f:
        raw = json.load(f)
    return raw["data"]

# ============================================================
# Swing Point Detection
# ============================================================

def find_swing_highs(data, swing=2):
    swings = []
    for i in range(swing, len(data) - swing):
        is_swing = all(data[i]["high"] > data[i - j]["high"] and data[i]["high"] > data[i + j]["high"] for j in range(1, swing + 1))
        if is_swing:
            swings.append({"price": data[i]["high"], "idx": i, "time": data[i].get("time", 0), "type": "high"})
    return swings

def find_swing_lows(data, swing=2):
    swings = []
    for i in range(swing, len(data) - swing):
        is_swing = all(data[i]["low"] < data[i - j]["low"] and data[i]["low"] < data[i + j]["low"] for j in range(1, swing + 1))
        if is_swing:
            swings.append({"price": data[i]["low"], "idx": i, "time": data[i].get("time", 0), "type": "low"})
    return swings

# ============================================================
# Clustering (fixed-dollar range)
# ============================================================

def cluster_swing_points(swings, cluster_range):
    if not swings:
        return []
    sorted_p = sorted(swings, key=lambda x: x["price"])
    clusters = []
    current_cluster = [sorted_p[0]]
    for p in sorted_p[1:]:
        if abs(p["price"] - sum(x["price"] for x in current_cluster) / len(current_cluster)) <= cluster_range:
            current_cluster.append(p)
        else:
            clusters.append(current_cluster)
            current_cluster = [p]
    clusters.append(current_cluster)
    
    results = []
    for c in clusters:
        prices = [x["price"] for x in c]
        results.append({
            "center": round(sum(prices) / len(prices), 1),
            "min": min(prices), "max": max(prices),
            "thickness": round(max(prices) - min(prices), 1),
            "count": len(c), "type": c[0]["type"],
            "recent_time": max(x["time"] for x in c)
        })
    return results

# ============================================================
# Wick Precision Analysis
# ============================================================

def find_era_start(data, level, threshold_pct=0.85):
    threshold = level * threshold_pct
    for i, bar in enumerate(data):
        if bar["high"] >= threshold:
            return i
    return 0

def validate_level(data, level, tolerances):
    results = []
    for tol in tolerances:
        interaction_count = 0
        wick_rejections = 0
        rejections = []
        
        for bar in data:
            touched = False
            if bar["high"] >= level - tol and bar["high"] <= level + tol:
                touched = True
                body_top = max(bar["open"], bar["close"])
                if bar["high"] > body_top:
                    wick_rejections += 1
                    bar_range = bar["high"] - bar["low"]
                    if bar_range > 0:
                        rejections.append((bar["high"] - body_top) / bar_range * 100)
            if bar["low"] >= level - tol and bar["low"] <= level + tol:
                touched = True
                body_bottom = min(bar["open"], bar["close"])
                if bar["low"] < body_bottom:
                    wick_rejections += 1
                    bar_range = bar["high"] - bar["low"]
                    if bar_range > 0:
                        rejections.append((body_bottom - bar["low"]) / bar_range * 100)
            if touched:
                interaction_count += 1
        
        wp = (wick_rejections / interaction_count * 100) if interaction_count > 0 else 0
        avg_rej = sum(rejections) / len(rejections) if rejections else 0
        
        wp_score = min(wp, 100)
        intx_score = 100 if interaction_count >= 2 else (50 if interaction_count == 1 else 0)
        rej_score = min(avg_rej / 30 * 100, 100)
        tf_composite = wp_score * 0.50 + intx_score * 0.30 + rej_score * 0.20
        
        results.append({
            "tolerance": tol, "interactions": interaction_count,
            "wick_rejections": wick_rejections, "wick_precision": round(wp, 1),
            "avg_rejection_pct": round(avg_rej, 3), "tf_composite": round(tf_composite, 1),
        })
    
    best = max(results, key=lambda x: x["wick_precision"])
    return results, best

# ============================================================
# Level Deduplication
# ============================================================

def dedup_levels(levels, dedup_range=50):
    if not levels:
        return []
    sorted_l = sorted(levels, key=lambda x: x["price"])
    merged = []
    current = [sorted_l[0]]
    for l in sorted_l[1:]:
        if abs(l["price"] - sum(x["price"] for x in current) / len(current)) <= dedup_range:
            current.append(l)
        else:
            merged.append(current)
            current = [l]
    merged.append(current)
    
    results = []
    for group in merged:
        prices = [x["price"] for x in group]
        results.append({
            "price": round(sum(prices) / len(prices), 1),
            "tfs": list(set(x["tf"] for x in group)),
            "tf_count": len(set(x["tf"] for x in group)),
            "total_interactions": sum(x["count"] for x in group),
            "distance_from_price": round(sum(prices) / len(prices) - current_price, 1)
        })
    return results

# ============================================================
# Scoring
# ============================================================

def score_level(level_price, data_configs, tolerances):
    tf_scores = {}
    for tf_name, data in data_configs:
        era_start = find_era_start(data, level_price)
        data_filtered = data[era_start:]
        _, best = validate_level(data_filtered, level_price, tolerances)
        tf_scores[tf_name] = best["tf_composite"]
    
    weights = {"W1": 0.50, "D1": 0.30, "H4": 0.20}
    overall = sum(tf_scores.get(tf, 0) * w for tf, w in weights.items())
    return tf_scores, round(overall, 1)

# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_key_levels.py <SYMBOL> [CLUSTER_RANGE]")
        sys.exit(1)
    
    SYMBOL = sys.argv[1]
    cluster_range = float(sys.argv[2]) if len(sys.argv) > 2 else CLUSTER_RANGES.get(SYMBOL, 30)
    tolerances = TOLERANCES_BY_INSTRUMENT.get(SYMBOL, [5, 10, 15, 20, 30, 50])
    
    # Load data
    configs = [("W1", load_data(SYMBOL, "W1"), 1, 0.50),
               ("D1", load_data(SYMBOL, "D1"), 2, 0.30),
               ("H4", load_data(SYMBOL, "H4"), 3, 0.20)]
    
    valid = [(n, d, s, w) for n, d, s, w in configs if d is not None]
    if not valid:
        print(f"❌ No data found for {SYMBOL}. Fetch data first.")
        sys.exit(1)
    
    current_price = valid[0][1][-1]["close"]
    print(f"\n📊 {SYMBOL} Current Price: {current_price}")
    for n, d, s, w in valid:
        print(f"   {n}: {len(d)} bars")
    
    # Detect swings and cluster
    all_resistance = []
    all_support = []
    for tf_name, data, swing, weight in valid:
        highs = find_swing_highs(data, swing)
        lows = find_swing_lows(data, swing)
        for c in cluster_swing_points(highs, cluster_range):
            all_resistance.append({"price": c["center"], "tf": tf_name, "count": c["count"], "recent_time": c["recent_time"], "weight": weight})
        for c in cluster_swing_points(lows, cluster_range):
            all_support.append({"price": c["center"], "tf": tf_name, "count": c["count"], "recent_time": c["recent_time"], "weight": weight})
    
    res_levels = dedup_levels(all_resistance)
    sup_levels = dedup_levels(all_support)
    
    # Nearest 5 each side
    res_near = sorted([l for l in res_levels if l["distance_from_price"] > 0], key=lambda x: x["distance_from_price"])[:5]
    sup_near = sorted([l for l in sup_levels if l["distance_from_price"] < 0], key=lambda x: -x["distance_from_price"])[:5]
    
    # Score
    data_for_scoring = [(n, d) for n, d, s, w in valid]
    scored = []
    for level in res_near + sup_near:
        tf_scores, overall = score_level(level["price"], data_for_scoring, tolerances)
        scored.append({
            "price": level["price"], "type": "RES" if level["price"] > current_price else "SUP",
            "score": overall, "tf_scores": tf_scores, "distance": level["distance_from_price"],
            "tfs": level["tfs"], "tf_count": level["tf_count"], "interactions": level["total_interactions"]
        })
    
    # Report
    print(f"\n{'=' * 60}")
    print(f"  {SYMBOL} KEY LEVELS — Multi-TF Weighted Scoring")
    print(f"{'=' * 60}")
    for l in scored:
        v = "✅ HIGH" if l["score"] >= 90 else "⚠️ MED" if l["score"] >= 70 else "❌ LOW"
        tf_str = " ".join(f"{k}:{l['tf_scores'].get(k,0)}" for k in ["W1","D1","H4"])
        print(f"  {l['type']} {l['price']} | Score: {l['score']}/100 [{v}] | Dist: {l['distance']:+.1f} | {tf_str}")
    
    high_conf = [l for l in scored if l["score"] >= 90]
    print(f"\n🎯 High Confidence (≥90): {len(high_conf)} levels")
    
    # Save results
    result = {"symbol": SYMBOL, "current_price": current_price, "analyzed_at": datetime.now(timezone.utc).isoformat(),
              "scored_levels": scored, "high_confidence": high_conf, "methodology": "ian-key-level v1.6.0"}
    os.makedirs(os.path.join(CACHE_DIR, "results"), exist_ok=True)
    with open(os.path.join(CACHE_DIR, "results", f"{SYMBOL}.json"), "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n✅ Results saved")
    
    # Output for plotting
    plot_levels = high_conf if high_conf else scored[:6]
    for l in plot_levels:
        print(f"PLOT|{l['type']}|{l['price']}|{l['score']}")
