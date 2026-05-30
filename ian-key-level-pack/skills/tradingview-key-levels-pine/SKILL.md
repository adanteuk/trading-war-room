---
name: tradingview-key-levels-pine
description: Build Pine Script v5 indicators for ICT/CRT key level analysis that exactly match the ian-key-level skill methodology. Covers architecture, multi-tolerance scanning, HTF data handling, and Pine Script constraints.
version: 1.0.0
author: Walker
tags: trading, Pine Script, TradingView, key levels, ICT, multi-timeframe, ian-key-level
---

# TradingView Pine Script — Key Levels Indicator

Build a Pine Script v5 indicator that implements the **ian-key-level skill methodology** — matching the Python `verify_key_levels.py` analysis exactly (numerical match within ±0.1).

## Core Architecture

Pine Script **cannot fetch external HTTP data**. The indicator must run natively on TradingView using:

1. `request.security()` to fetch W1/D1/H4 OHLCV series
2. `ta.pivothigh()` / `ta.pivotlow()` for swing detection per TF
3. Array-based tracking for deduplicated swing levels
4. Scoring + drawing only on `barstate.islast`

## ⚠️ Critical Pitfalls (Learned from 4 Iterations)

### Pitfall 1: request.security Loop Doesn't Work

**Wrong (v1.0 approach)**:
```pine
for i = 0 to 4999
    array.push(arr, w1_high[i])  // Doesn't work — security() returns a single value per chart bar
```

**Right**: Use `ta.pivothigh()` with `request.security()` to detect swings:
```pine
w1_ph = request.security(syminfo.tickerid, "W", ta.pivothigh(1,1), lookahead=barmerge.lookahead_off)
```

### Pitfall 2: Fixed Tolerance Causes Massive Scoring Errors

**Wrong (v2.1 approach)**:
```pine
score = f_score_level(level, tol_w1, ...)  // Single tolerance per TF
```
This caused **50+ point scoring errors**. Example: level 24700.9 scored 91.5 in Python (multi-tol) but only 41.1 with fixed tolerance.

**Right (v2.2 approach)**: Single-pass scan tracking **all 6 tolerances simultaneously**:
```pine
tols_6 = array.from(5.0, 10.0, 15.0, 20.0, 30.0, 50.0)
arr_intx   = array.new_int(6, 0)
arr_wr     = array.new_int(6, 0)
arr_rp_sum = array.new_float(6, 0.0)
arr_rp_cnt = array.new_int(6, 0)

for i = 1 to max_offset
    // ... unique bar detection ...
    for t = 0 to 5
        float tol = array.get(tols_6, t)
        // Track interaction per tolerance
        // ...
// After scan: pick tolerance with highest composite
```

This is **1 scan per TF**, not 6. Computationally efficient and matches Python exactly.

### Pitfall 3: HTF Series Value Replication

`request.security` replicates HTF values across chart bars. A W1 bar's high repeats ~42 times on an H4 chart.

**Fix**: Detect unique bars via value change:
```pine
float nh = h_s[i + 1]
bool is_unique = na(nh) or (h != nh)
if not is_unique
    continue  // skip replicated values
```

**Replication factors** for H4 chart:
- W1: rep_factor = 48 (W1 bar ≈ 42 H4 bars + safety)
- D1: rep_factor = 8 (D1 bar ≈ 6 H4 bars + safety)
- H4: rep_factor = 1

### Pitfall 4: Functions Must Be at Top Level

**Wrong**:
```pine
if barstate.islast
    f_score_level(...) =>  // ERROR — functions can't be declared inside if blocks
```

**Right**: Declare ALL functions before any executable code.

### Pitfall 5: `var` in Functions Persists Across Calls

Using `var` inside a function causes state to leak between calls. Use regular variables or arrays initialized per call.

## Pine Script Functions

### Multi-Tolerance Scoring Function

```pine
f_score_tf_multitol(float h_s, float l_s, float o_s, float c_s, float level, bool is_res, int lb, int rep_factor) =>
    arr_intx   = array.new_int(6, 0)
    arr_wr     = array.new_int(6, 0)
    arr_rp_sum = array.new_float(6, 0.0)
    arr_rp_cnt = array.new_int(6, 0)
    tols_6 = array.from(5.0, 10.0, 15.0, 20.0, 30.0, 50.0)
    
    int unique_bars = 0
    int max_offset = math.min(lb * rep_factor + rep_factor * 2, 20000)
    bool era_valid = true
    
    for i = 1 to max_offset
        float h = h_s[i]; float l = l_s[i]
        if na(h) continue
        
        // Detect unique HTF bar
        float nh = h_s[i + 1]; float nl = l_s[i + 1]
        bool is_unique = na(nh) or (h != nh) or (l != nl)
        if not is_unique continue
        
        unique_bars += 1
        if unique_bars > lb break
        
        // Era filter (skip bars before price reached 85% of level)
        if era_valid
            bool in_era = is_res ? (h >= level * 0.85) : (l <= level * 1.15)
            if not in_era
                era_valid := false
                break
        
        float bar_range = h - l
        if bar_range <= 0 continue
        
        float wick_len_h = h - math.max(o_s[i], c_s[i])
        float wick_len_l = math.min(o_s[i], c_s[i]) - l
        
        // Single-pass multi-tolerance tracking
        for t = 0 to 5
            float tol = array.get(tols_6, t)
            bool touched = is_res
                ? (h >= level - tol and h <= level + tol)
                : (l >= level - tol and l <= level + tol)
            if not touched continue
            
            array.set(arr_intx, t, array.get(arr_intx, t) + 1)
            float wick_len = is_res ? wick_len_h : wick_len_l
            if wick_len > 0.01
                array.set(arr_wr, t, array.get(arr_wr, t) + 1)
                array.set(arr_rp_cnt, t, array.get(arr_rp_cnt, t) + 1)
                array.set(arr_rp_sum, t, array.get(arr_rp_sum, t) + wick_len / bar_range * 100.0)
    
    // Pick best tolerance
    float best_score = 0.0; float best_tol = 0.0; int best_intx = 0
    for t = 0 to 5
        int intx = array.get(arr_intx, t)
        if intx == 0 continue
        float wp = math.min(array.get(arr_wr, t) / intx * 100.0, 100.0)
        float intx_s = intx >= 2 ? 100.0 : 50.0
        float avg_rej = array.get(arr_rp_cnt, t) > 0 ? array.get(arr_rp_sum, t) / array.get(arr_rp_cnt, t) : 0.0
        float rej_s = math.min(avg_rej / 30.0 * 100.0, 100.0)
        float composite = wp * 0.50 + intx_s * 0.30 + rej_s * 0.20
        if composite > best_score
            best_score := composite; best_tol := array.get(tols_6, t)
            best_intx := intx
    
    [best_score, best_tol, best_intx]
```

### Zone Clustering Function

Merge levels within `zone_tol` points:
```pine
f_cluster_zones(levels, scores, tfs, w1s, d1s, h4s, intxs, ztol) =>
    // Sort by price ascending, then merge consecutive levels within ztol
    // Merged zone price = average of clustered levels
    // Merged zone score = max of clustered scores
    // ... (see key_levels_v1.pine for full implementation)
```

## Scoring Formula (Must Match ian-key-level Skill Exactly)

```
Wick Precision    = wick_rejections / interactions × 100  (capped at 100)
Interaction Score = 100 if ≥2 interactions, 50 if 1, 0 if 0
Rejection Strength = min(avg_rejection_pct / 30 × 100, 100)
TF Composite      = WP×0.50 + Intx×0.30 + Rej×0.20
Overall Score     = W1_Score×0.50 + D1_Score×0.30 + H4_Score×0.20
```

## Verified Numerical Match

Tested on GER40 with Python `verify_key_levels.py`:

| Level | Python | Pine v2.2 | Diff |
|-------|:---:|:---:|:---:|
| 24645.5 | 98.0 | 97.9 | -0.1 |
| 24648.1 | 98.1 | 98.1 | 0.0 |
| 24670.9 | 100.0 | 100.0 | 0.0 |
| 24700.9 | 91.5 | 91.5 | 0.0 |
| 24777.2 | 93.8 | 93.8 | 0.0 |

## Display Format

Labels must match skill format: `"Score: XX/100 [W1:XX D1:XX H4:XX]"`

```pine
label.new(bar_index, lv,
    text=str.format("Score: {0}/100\n[{1}:{2} {3}:{4} {5}:{6}]\n{7} | +{8}%",
        str.tostring(sc, "#.0"),
        "W1", str.tostring(sw1, "#.0"),
        "D1", str.tostring(sd1, "#.0"),
        "H4", str.tostring(sh4, "#.0"),
        str.tostring(lv, "#.0"),
        str.tostring(dist_pct, "#.00")))
```

## Ian's Hard Rules

- **Default min_score = 90** (not 70). Below 90 = no reference value.
- Levels below 90 should NOT be reported.
- Zone threshold = 50 points.

## File Location

`~/.hermes/projects/tradingview-key-levels/indicator/key_levels_v1.pine`
