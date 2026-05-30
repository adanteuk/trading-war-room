#!/usr/bin/env python3
"""
MT5 Key Levels Pipeline — Full W1/D1/H4 analysis from Alfred MT5 data.

Usage: python3 mt5_key_levels_pipeline.py <SYMBOL>

Expects data files at:
  ~/.hermes/data/key-level-cache/data/<SYMBOL>/W1.json
  ~/.hermes/data/key-level-cache/data/<SYMBOL>/D1.json
  ~/.hermes/data/key-level-cache/data/<SYMBOL>/H4.json

Outputs scored levels + PLOT| lines for downstream chart plotting.
"""

import json, os, sys

CACHE_DIR = os.path.expanduser("~/.hermes/data/key-level-cache/data")

CLUSTER_RANGES = {
    # Indices (~25K-30K range): ±30 points
    "JPN225": 50, "GER40": 30, "NAS100": 30, "US500": 30,
    "HK50": 30, "US30": 30, "US2000": 30,
    # TWN is ~3900 range: ±50 points
    "TWN": 50,
    # Crypto/commodities
    "BTCUSD": 500, "XAUUSD": 5, "USOIL": 2,
    # Forex pairs
    "AUDJPY": 0.5, "EURUSD": 0.5, "GBPUSD": 0.5,
}

TOLERANCES = [5, 10, 15, 20, 30, 50]

def load_data(symbol, tf):
    fpath = os.path.join(CACHE_DIR, symbol, f"{tf}.json")
    if not os.path.exists(fpath):
        print(f"❌ No data: {fpath}")
        return None
    with open(fpath) as f:
        raw = json.load(f)
    return raw["data"]

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
            "min": round(min(prices), 1), "max": round(max(prices), 1),
            "recent_time": max(x["time"] for x in c)
        })
    return results

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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mt5_key_levels_pipeline.py <SYMBOL>")
        sys.exit(1)
    
    SYMBOL = sys.argv[1]
    cluster_range = CLUSTER_RANGES.get(SYMBOL, 30)
    
    w1_bars = load_data(SYMBOL, "W1")
    d1_bars = load_data(SYMBOL, "D1")
    h4_bars = load_data(SYMBOL, "H4")
    
    configs = [("W1", w1_bars, 1, 0.50), ("D1", d1_bars, 2, 0.30), ("H4", h4_bars, 3, 0.20)]
    valid = [(n, d, s, w) for n, d, s, w in configs if d is not None]
    
    if not valid:
        print(f"❌ No data found for {SYMBOL}. Fetch from Alfred first.")
        sys.exit(1)
    
    current_price = d1_bars[-1]["close"] if d1_bars else valid[0][1][-1]["close"]
    print(f"\n📊 {SYMBOL} Current Price: {current_price}")
    for n, d, s, w in valid:
        print(f"   {n}: {len(d)} bars")
    
    all_resistance = []
    all_support = []
    for tf_name, data, swing, weight in valid:
        for c in cluster_levels(find_swing_highs(data, swing), cluster_range):
            all_resistance.append({"price": c["price"], "tf": tf_name})
        for c in cluster_levels(find_swing_lows(data, swing), cluster_range):
            all_support.append({"price": c["price"], "tf": tf_name})
    
    def get_nearest(items, price, limit=10):
        return sorted(items, key=lambda x: abs(x["price"] - price))[:limit]
    
    seen = set()
    unique = []
    for item in get_nearest(all_resistance, current_price) + get_nearest(all_support, current_price):
        key = round(item["price"], 0)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    
    data_for_scoring = [(n, d) for n, d, s, w in valid]
    weights = {"W1": 0.50, "D1": 0.30, "H4": 0.20}
    
    scored = []
    for item in unique[:15]:
        is_res = item["price"] > current_price
        tf_scores = {}
        for tf_name, data in data_for_scoring:
            _, best = validate_level(data, item["price"], TOLERANCES, is_res)
            tf_scores[tf_name] = best
        
        overall = sum(tf_scores[tf]["tf_composite"] * weights[tf] for tf in weights if tf in tf_scores)
        overall = round(overall, 1)
        
        scored.append({
            "price": item["price"], "type": "RES" if is_res else "SUP",
            "overall": overall,
            "tf_scores": {tf: {"score": tf_scores[tf]["tf_composite"],
                               "wp": tf_scores[tf]["wick_precision"],
                               "intx": tf_scores[tf]["interactions"],
                               "tol": tf_scores[tf]["tolerance"]} for tf in tf_scores}
        })
    
    scored.sort(key=lambda x: abs(x["price"] - current_price))
    
    print(f"\n{'='*70}")
    print(f"  {SYMBOL} KEY LEVELS — Alfred MT5 Multi-TF Scoring")
    print(f"{'='*70}")
    for l in scored:
        v = "✅ HIGH" if l["overall"] >= 90 else "⚠️ MED" if l["overall"] >= 70 else "❌ LOW"
        tf_parts = []
        for tf in ["W1", "D1", "H4"]:
            if tf in l["tf_scores"]:
                t = l["tf_scores"][tf]
                tf_parts.append(f"{tf}:{t['score']:.0f}({t['intx']}x±{t['tol']})")
        print(f"  {l['type']} {l['price']} | {l['overall']}/100 [{v}] | {' '.join(tf_parts)} | Dist: {l['price']-current_price:+.1f}")
    
    high_conf = [l for l in scored if l["overall"] >= 90]
    plot_levels = high_conf if high_conf else scored[:5]
    
    print(f"\n=== PLOT OUTPUT ===")
    for l in plot_levels:
        print(f"PLOT|{l['type']}|{l['price']}|{l['overall']:.0f}")
