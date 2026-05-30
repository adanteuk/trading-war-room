#!/usr/bin/env python3
"""Key Level Analysis - Multi-TF swing point scoring.
Usage: python3 key_level_analysis.py SYMBOL1 SYMBOL2 ...
Requires: MT5 data JSON files at /tmp/mt5-keylevel/SYMBOL_{w1,d1,h4}.json
Compatible with: alfred-mt5-data skill for data fetching.
"""

import json
import sys

DATA_DIR = "/tmp/mt5-keylevel"

def load_data(path):
    with open(path) as f:
        data = json.load(f)
    if data.get("status") != "ok":
        raise ValueError(f"Data error: {data}")
    bars = data["data"]
    last_price = data.get("last_price", bars[-1]["close"] if bars else 0)
    return bars, last_price

def find_first_era_bar(bars, level):
    """Price Era Validation: find first bar where high >= level * 0.85."""
    threshold = level * 0.85
    for i, bar in enumerate(bars):
        if bar["high"] >= threshold:
            return i
    return 0

def detect_swing_points(bars, swing, start_idx=0):
    """Detect swing highs and lows. swing=N means compare with N bars on each side."""
    swing_highs = []
    swing_lows = []
    for i in range(start_idx + swing, len(bars) - swing):
        bar = bars[i]
        is_high = all(
            bar["high"] > bars[i - j]["high"] and bar["high"] > bars[i + j]["high"]
            for j in range(1, swing + 1)
        )
        is_low = all(
            bar["low"] < bars[i - j]["low"] and bar["low"] < bars[i + j]["low"]
            for j in range(1, swing + 1)
        )
        if is_high:
            swing_highs.append({"price": bar["high"], "time_epoch": bar.get("time_epoch", 0)})
        if is_low:
            swing_lows.append({"price": bar["low"], "time_epoch": bar.get("time_epoch", 0)})
    return swing_highs, swing_lows

def cluster_levels(points, current_price, tolerance_pct=0.002):
    """Cluster swing points within tolerance_pct. Separate into resistance/support."""
    if not points:
        return [], []
    sorted_pts = sorted(points, key=lambda x: x["price"])
    clusters = []
    current_cluster = [sorted_pts[0]]
    for i in range(1, len(sorted_pts)):
        prev_avg = sum(p["price"] for p in current_cluster) / len(current_cluster)
        if abs(sorted_pts[i]["price"] - prev_avg) / prev_avg <= tolerance_pct:
            current_cluster.append(sorted_pts[i])
        else:
            clusters.append(current_cluster)
            current_cluster = [sorted_pts[i]]
    clusters.append(current_cluster)
    result = []
    for cluster in clusters:
        avg_price = sum(p["price"] for p in cluster) / len(cluster)
        level_type = "resistance" if avg_price > current_price else "support"
        result.append({
            "price": avg_price,
            "count": len(cluster),
            "type": level_type,
            "distance_pct": abs(avg_price - current_price) / current_price * 100
        })
    resistance = [c for c in result if c["type"] == "resistance"]
    support = [c for c in result if c["type"] == "support"]
    return resistance, support

def compute_interactions(bars, level_price, tolerance_pct=0.015, start_idx=0):
    """Count bar interactions with level. Return (interactions, wick_rejections, avg_rejection_pct)."""
    interactions = 0
    wick_rejections = 0
    total_rejection_pct = 0.0
    for i in range(start_idx, len(bars)):
        bar = bars[i]
        high, low = bar["high"], bar["low"]
        upper = level_price * (1 + tolerance_pct)
        lower = level_price * (1 - tolerance_pct)
        
        bar_range = high - low
        if bar_range <= 0:
            continue
        
        touched = False
        # High touch
        if high >= lower and high <= upper:
            touched = True
            body_top = max(bar["open"], bar["close"])
            if high > body_top:  # Has upper wick beyond body
                wick_rejections += 1
                total_rejection_pct += (high - body_top) / bar_range * 100
        
        # Low touch
        if low >= lower and low <= upper:
            touched = True
            body_bottom = min(bar["open"], bar["close"])
            if low < body_bottom:  # Has lower wick beyond body
                wick_rejections += 1
                total_rejection_pct += (body_bottom - low) / bar_range * 100
        
        if touched:
            interactions += 1
    
    avg_rejection_pct = (total_rejection_pct / wick_rejections) if wick_rejections > 0 else 0
    return interactions, wick_rejections, avg_rejection_pct

def score_single_tf(levels, bars, current_price):
    """Score levels for a single TF. Composite = WP×0.50 + IC×0.30 + RS×0.20."""
    results = []
    for level in levels:
        price = level["price"]
        era = find_first_era_bar(bars, price)
        intx, wick, avg_rej = compute_interactions(bars, price, start_idx=era)
        wp = min((wick / intx * 100) if intx > 0 else 0, 100)
        ic = 100 if intx >= 2 else (50 if intx == 1 else 0)
        rs = min(avg_rej / 30 * 100, 100)
        composite = wp * 0.50 + ic * 0.30 + rs * 0.20
        results.append({
            "price": price, "type": level["type"], "composite": composite,
            "interactions": intx, "wick": wick, "count": level["count"],
            "distance_pct": abs(price - current_price) / current_price * 100
        })
    return results

def combine_multitf_scores(w1_scores, d1_scores, h4_scores, current_price):
    """Combine scores: Overall = W1×0.50 + D1×0.30 + H4×0.20. Cross-TF match within 0.5%."""
    combined = []
    seen = set()
    all_tf = [("W1", w1_scores), ("D1", d1_scores), ("H4", h4_scores)]
    for tf_name, scores in all_tf:
        for level in scores:
            price_key = round(level["price"], 1)
            if price_key in seen:
                continue
            seen.add(price_key)
            w1_c = d1_c = h4_c = 0
            for t, sc in all_tf:
                best = 0
                for s in sc:
                    if abs(s["price"] - level["price"]) / level["price"] < 0.005:
                        if s["composite"] > best:
                            best = s["composite"]
                if t == "W1": w1_c = best
                elif t == "D1": d1_c = best
                else: h4_c = best
            overall = w1_c * 0.50 + d1_c * 0.30 + h4_c * 0.20
            combined.append({
                "price": level["price"], "type": level["type"],
                "w1_composite": w1_c, "d1_composite": d1_c, "h4_composite": h4_c,
                "overall": overall,
                "distance_pct": abs(level["price"] - current_price) / current_price * 100,
                "distance_pts": abs(level["price"] - current_price),
                "interactions": level["interactions"]
            })
    return sorted(combined, key=lambda x: x["overall"], reverse=True)

def analyze_symbol(symbol, last_price):
    """Full analysis pipeline for one symbol."""
    w1_bars, _ = load_data(f"{DATA_DIR}/{symbol}_w1.json")
    d1_bars, _ = load_data(f"{DATA_DIR}/{symbol}_d1.json")
    h4_bars, _ = load_data(f"{DATA_DIR}/{symbol}_h4.json")

    w1_h, w1_l = detect_swing_points(w1_bars, swing=1)
    d1_h, d1_l = detect_swing_points(d1_bars, swing=2)
    h4_h, h4_l = detect_swing_points(h4_bars, swing=3)

    best_overall = -1
    best_result = None
    best_tol = 0.01

    # Sweep tolerances, pick best
    for tol in [0.005, 0.010, 0.015, 0.020, 0.030, 0.050]:
        w1_r, w1_s = cluster_levels(w1_h + w1_l, last_price, tolerance_pct=tol)
        d1_r, d1_s = cluster_levels(d1_h + d1_l, last_price, tolerance_pct=tol)
        h4_r, h4_s = cluster_levels(h4_h + h4_l, last_price, tolerance_pct=tol)

        w1_scores = score_single_tf(w1_r + w1_s, w1_bars, last_price)
        d1_scores = score_single_tf(d1_r + d1_s, d1_bars, last_price)
        h4_scores = score_single_tf(h4_r + h4_s, h4_bars, last_price)

        combined = combine_multitf_scores(w1_scores, d1_scores, h4_scores, last_price)
        if combined:
            mx = max(c["overall"] for c in combined)
            if mx > best_overall:
                best_overall = mx
                best_result = combined
                best_tol = tol

    # Filter > 90 or fallback
    high_score = [r for r in best_result if r["overall"] > 90] if best_result else []
    fallback = not high_score

    # Find nearest resistance and support (separate lists)
    nearest_res = nearest_sup = None
    if best_result:
        res_list = sorted([r for r in best_result if r["type"] == "resistance"], key=lambda x: x["distance_pct"])
        sup_list = sorted([r for r in best_result if r["type"] == "support"], key=lambda x: x["distance_pct"])
        if res_list: nearest_res = res_list[0]
        if sup_list: nearest_sup = sup_list[0]

    # ATH for context
    ath = max(b["high"] for b in d1_bars)

    return {
        "symbol": symbol, "last_price": last_price, "ath": ath,
        "nearest_resistance": nearest_res, "nearest_support": nearest_sup,
        "top_levels": best_result or [], "fallback": fallback, "best_tol": best_tol
    }

if __name__ == "__main__":
    symbols = sys.argv[1:] if len(sys.argv) > 1 else ["NAS100", "GER40"]
    results = {}
    for sym in symbols:
        with open(f"{DATA_DIR}/{sym}_w1.json") as f:
            d = json.load(f)
        last = d.get("last_price", d["data"][-1]["close"])
        print(f"Analyzing {sym} (price: {last})...")
        results[sym] = analyze_symbol(sym, last)

    with open(f"{DATA_DIR}/results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Results saved to", f"{DATA_DIR}/results.json")
