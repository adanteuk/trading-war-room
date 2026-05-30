---
name: key-level-analysis
description: >
  Multi-timeframe key level analysis using MT5 data — swing point detection,
  clustering, and composite scoring (W1×0.50 + D1×0.30 + H4×0.20) to find
  high-probability support/resistance levels for NAS100, GER40, and other symbols.
  Includes persistent caching to avoid redundant data downloads.
version: 2.0.0
author: Walker (cron job 2026-04-19)
tags: trading, key-levels, support, resistance, MT5, swing-points, scoring, caching
---

# Key Level Analysis Skill v2.0

Find high-probability support/resistance levels using multi-timeframe swing point analysis on MT5 data.

## 🗄️ Persistent Cache System

**All data and results are cached persistently.** Before downloading data or running analysis, ALWAYS check the cache first.

### Cache Directory
```
~/.hermes/data/key-level-cache/
├── data/{SYMBOL}/{W1|D1|H4}.json
└── results/{SYMBOL}.json
```

### TTL Policy
| Timeframe | TTL | Rationale |
|-----------|-----|-----------|
| H4 | 6 hours | Intraday — new bars every 4 hours |
| D1 | 24 hours | Daily bar closes once per day |
| W1 | 7 days | Weekly bar changes slowly |

### Workflow
```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.hermes/data/key-level-cache"))
from cache_manager import CacheManager

cache = CacheManager()

# Step 1: Check cache
status = cache.get_status("NAS100")
if status["has_cached_result"]:
    # Use cached result — NO download needed
    return status["result"]

# Step 2: Download ONLY expired TFs
for tf in status["expired_tfs"]:
    bars, last_price = download_tf("NAS100", tf)  # Alfred/TradingView
    cache.save_data("NAS100", tf, bars, last_price)

# Step 3: Load ALL TFs (mix cached + fresh)
# Step 4: Run analysis
# Step 5: cache.save_result("NAS100", result)
```

## Core Philosophy

> **Key levels are not arbitrary round numbers — they are price zones where market participants have repeatedly shown interest (via swing point clustering and price rejection).**

This method identifies levels by:
1. Detecting swing highs/lows across W1, D1, H4
2. Clustering nearby swings into zones
3. Scoring each zone on Wick Precision, Interaction Count, and Rejection Strength
4. Combining scores with TF-weighted composite

---

## Data Source

Uses **Alfred MT5 Bridge** via ZeroMQ. See `alfred-mt5-data` skill for connection details.

### ⚠️ Cache-First Workflow

**Before any data download, check the cache:**
```python
from cache_manager import CacheManager
cache = CacheManager()
status = cache.get_status(SYMBOL)
# Only download timeframes listed in status["expired_tfs"]
```

### Prerequisites
```bash
# Install pyzmq in the agent venv
uv pip install pyzmq -p /path/to/venv/bin/python3
```

### Fetch Multi-TF Data

**⚠️ Only download expired timeframes:**
```bash
# First check: which TFs are expired?
# Then download only those:
cd ~/.hermes/skills/trading/alfred-mt5-bridge/scripts

# Example: only D1 expired
python3 alfred_client.py multi SYM --tf D1 --count 999 --output /tmp/mt5-keylevel

# Save to persistent cache after download:
# python3 -c "
# from cache_manager import CacheManager; cache = CacheManager()
# cache.save_data('SYM', 'D1', bars, last_price)
# "
```

### Run Analysis
```bash
# From any directory — use absolute path
python3 ~/.hermes/skills/trading/key-level-analysis/scripts/key_level_analysis.py NAS100
```

---

## Analysis Pipeline

### Step 0: Cache Check (ALWAYS FIRST)

```python
from cache_manager import CacheManager
cache = CacheManager()
status = cache.get_status(SYMBOL)

if status["has_cached_result"]:
    # Return cached — skip all steps below
    print(f"Using cached result for {SYMBOL}")
    display_result(status["result"])
    return

# Only download expired TFs
for tf in status["expired_tfs"]:
    download_and_save_tf(SYMBOL, tf, cache)
```

### Step 1: Swing Point Detection

Different swing settings per timeframe:

| Timeframe | Swing Setting | Bars Compared | Sensitivity |
|-----------|--------------|---------------|-------------|
| W1 | swing=1 | ±1 bar | Broad structural levels |
| D1 | swing=2 | ±2 bars | Medium-term levels |
| H4 | swing=3 | ±3 bars | Granular near-term levels |

```python
def detect_swing_points(bars, swing, start_idx=0):
    swing_highs = []
    swing_lows = []
    
    for i in range(start_idx + swing, len(bars) - swing):
        bar = bars[i]
        is_high = True
        is_low = True
        for j in range(1, swing + 1):
            if bars[i - j]["high"] >= bar["high"] or bars[i + j]["high"] >= bar["high"]:
                is_high = False
            if bars[i - j]["low"] <= bar["low"] or bars[i + j]["low"] <= bar["low"]:
                is_low = False
        if is_high:
            swing_highs.append({"price": bar["high"], "time_epoch": bar.get("time_epoch", 0)})
        if is_low:
            swing_lows.append({"price": bar["low"], "time_epoch": bar.get("time_epoch", 0)})
    
    return swing_highs, swing_lows
```

### Step 2: Cluster Nearby Swing Points

Group swings within a tolerance percentage into single zones:

```python
def cluster_levels(points, current_price, tolerance_pct=0.002):
    # Sort by price, cluster consecutive points within tolerance
    # Separate into resistance (> current_price) and support (< current_price)
    # Return list of {price: avg_price, count: N, type: "resistance"/"support"}
```

### Step 3: Score Each Level

Three components per level:

| Component | Weight | Formula |
|-----------|--------|---------|
| Wick Precision (WP) | 50% | `wick_rejections / interactions × 100`, capped at 100% |
| Interaction Count (IC) | 30% | ≥2 interactions = 100, 1 = 50, 0 = 0 |
| Rejection Strength (RS) | 20% | `min(avg_rejection_pct / 30 × 100, 100)` |

**Per-TF Composite:** `WP × 0.50 + IC × 0.30 + RS × 0.20`

**Overall Score:** `W1_composite × 0.50 + D1_composite × 0.30 + H4_composite × 0.20`

### Step 4: Test Multiple Tolerances

Test clustering at ±5, ±10, ±15, ±20, ±30, ±50 bps (0.005 to 0.050).
Pick the tolerance that produces the highest-scoring levels.

### Step 5: Filter & Report

- Primary filter: Overall Score > 90
- Fallback: If no > 90 levels, show the highest-score levels (annotate as "No >90 levels found")
- Report nearest resistance (above price) and nearest support (below price)

---

## Price Era Validation Rule

Before analyzing a level, verify the price has actually traded near it:

```python
def find_first_era_bar(bars, level):
    threshold = level * 0.85  # Price must have reached at least 85% of level
    for i, bar in enumerate(bars):
        if bar["high"] >= threshold:
            return i
    return 0  # Analyze from the beginning
```

Only count interactions from the era start bar forward. This prevents counting ancient bars that predate the current price regime.

---

## ⚠️ Pitfalls & Edge Cases

### ATH Edge Case — No Resistance Above Price
When price is at or near all-time highs (e.g., NAS100 at 27,867 vs ATH 27,867.2):
- **No swing highs exist above current price** → resistance list is empty
- All clustered levels become support
- Report the ATH as the nearest resistance with a note: "No validated key level above — nearest is ATH"
- **At ATH, scores rarely exceed 70-75** — fallback to "highest-score levels" is expected, not an error. Always annotate when using fallback.

### IG Weekend Gap vs MT5 Close
- IG weekend prices can differ significantly from Friday MT5 close
- GER40 example: MT5 close 24,629 vs IG weekend ~23,873 = -3% gap
- Always cross-reference: if gap is large, adjust key level distance from weekend price, not MT5 close

### No Levels > 90
- In trending markets or at ATH, scores rarely exceed 70-75
- The fallback to "highest-score levels" is the expected behavior, not an error
- Always annotate when using fallback: "No >90 levels found, showing nearest high-score levels"
- The `execute_code` sandbox does NOT have pandas installed
- All analysis must use standard library: `json`, `math`, `statistics`
- Load MT5 JSON data with `json.load()`, iterate bars as dicts

### Cross-TF Level Matching
When combining scores across W1/D1/H4, use 0.5% tolerance to find the same level across timeframes:
```python
if abs(other_tf_level_price - this_tf_level_price) / this_tf_level_price < 0.005:
    # Same level, use other TF's composite score
```
If a level only exists on one TF, its composite from other TFs is 0 (penalized in overall score).

---

## Reporting Format

```
💹 {SYMBOL} Key Level Analysis:
現價: XXXX.XX (MT5 收盤)

📈 最近上方 Key Level: XXXX.X (Score: XX/100, W1:XX D1:XX H4:XX, 距離 +XX 點)
📉 最近下方 Key Level: XXXX.X (Score: XX/100, W1:XX D1:XX H4:XX, 距離 -XX 點)

[簡評：gap 方向、開盤 bias、關鍵位距離]

⚠️ Score 說明：
- ≥90: HIGH CONFIDENCE（綠色）
- 70-89: MEDIUM（橙色）
- <70: LOW（紅色）
```

**Every key level MUST display its Score (Overall/100) and TF Breakdown (W1, D1, H4 composite scores).**

---

*Created: 2026-04-19*
*Updated: 2026-05-05 — v2.0: Added persistent caching system. Data/Results cached at ~/.hermes/data/key-level-cache/. Only expired TFs are re-downloaded.*
*Compatible with: alfred-mt5-data skill, cache_manager.py*
*First used in: MSCI Weekly Report cron job*