---
name: ian-key-level
description: Ian's ICT/CRT Key Level Methodology for JPN225. Validates, records, and analyzes key levels based on wick precision, rejection strength, and zone clustering. Includes persistent caching to avoid redundant data downloads.
version: 1.8.0
author: Walker
tags: trading, ICT, Romeo CRT, key levels, JPN225, price action, wick analysis, caching, forex
---

# Ian's Key Level Skill v1.8

**Validated ICT/CRT methodology for identifying and confirming key levels on JPN225.**

---

## 🗄️ Persistent Cache System

**All OHLCV data and analysis results are cached persistently.** When a key level request comes in for a symbol:

1. **Check cache status first** — use `cache_manager.py` to see what's fresh
2. **Only download expired timeframes** — don't re-fetch data that's still valid
3. **Return cached results immediately** if all data is fresh and analysis exists
4. **Re-run analysis only on updated TFs** and merge with cached scores from fresh TFs

### Cache Directory
```
~/.hermes/data/key-level-cache/
├── data/
│   └── {SYMBOL}/
│       ├── W1.json  (raw OHLCV + metadata)
│       ├── D1.json
│       └── H4.json
└── results/
    └── {SYMBOL}.json  (analysis results)
```

### TTL Policy (Time-To-Live)
| Timeframe | TTL | Rationale |
|-----------|-----|-----------|
| H4 | 6 hours | Intraday — new bars form every 4 hours |
| D1 | 24 hours | Daily bar closes once per day |
| W1 | 7 days | Weekly bar changes slowly |

Results are valid only when ALL 3 TF data files are still fresh.

### Cache Manager Usage
```python
import sys
sys.path.insert(0, os.path.expanduser("~/.hermes/data/key-level-cache"))
from cache_manager import CacheManager

cache = CacheManager()

# Check what needs updating for a symbol
expired = cache.check_freshness("NAS100")
# Returns: {"W1": False, "D1": True, "H4": False}  (only D1 expired)

# Get full status
status = cache.get_status("NAS100")
# If status["has_cached_result"]: return the cached result immediately
# Otherwise: download only status["expired_tfs"], run analysis, save

# Save downloaded data
cache.save_data("NAS100", "D1", bars, last_price, source="alfred-mt5")

# Save analysis results
cache.save_result("NAS100", result_dict)
```

### Workflow: Key Level Request
```
1. status = cache.get_status(SYMBOL)
2. IF status["has_cached_result"]:
     → Return cached result immediately (DONE)
3. ELSE:
     → Download ONLY expired TFs (status["expired_tfs"])
     → Load fresh TFs from cache
     → Run full analysis
     → cache.save_data() for each downloaded TF
     → cache.save_result() for the analysis
     → Return result
```

---

## 🎯 Core Principles

### **1. Wick-Based Precision**
- **Later wicks carry more weight** in level validation
- Levels are **micro-adjusted from round numbers** (e.g., 52600 → 52644.1)
- **1 decimal place precision** is intentional and validated
- Based on: Swing Points + Price Clusters + Psychological Levels + Wick Analysis

### **2. Level Validation Criteria**
A key level is considered **confirmed** when:
- ✅ **Wick Precision Score > 70%** (wick interactions / total interactions)
- ✅ **Multiple tests** (minimum 2+ interactions)
- ✅ **Strong rejection** (average rejection % > 30%)
- ✅ **Tight tolerance** (±5-20 points from exact level)

**⚠️ Instrument Scaling Note:** Tolerances must be scaled to the instrument's price scale and daily range. The ±5 point tolerance was validated on JPN225 (~52,000). Using instrument-inappropriate tolerances will produce wrong results.

**Tolerance guidance by instrument:**

| Instrument | Price Range | Tolerances to Test | Notes |
|------------|-------------|--------------------|-------|
| JPN225 | ~50,000 | ±5, ±10, ±15, ±20, ±30, ±50 | Original validation standard |
| GER40 | ~24,000 | ±5, ±10, ±15, ±20, ±30, ±50 | ±5-10 optimal for CFD precision |
| NAS100 | ~26,000 | ±5, ±10, ±15, ±20, ±30, ±50 | Similar scale to GER40 |
| HK50 | ~25,000 | ±5, ±10, ±15, ±20, ±30, ±50 | Similar scale to GER40/NAS100 |
| US500 | ~7,000 | ±5, ±10, ±15, ±20, ±30, ±50 | Lower absolute range |
| BTCUSD | ~75,000 | ±100, ±200, ±300, ±500, ±750, ±1000 | High volatility, wider tolerances needed |
| XAUUSD | ~3,000 | ±2, ±5, ±10, ±15, ±20, ±30 | Tight precision for gold |
| AUDJPY | ~113 | ±5, ±10, ±15, ±20, ±30, ±50 | ±5 optimal for ~100-150 price range |
| EURUSD | ~1.08 | ±0.0005, ±0.0010, ±0.0015, ±0.0020, ±0.0030, ±0.0050 | 5-50 pip tolerances. ±5pip (0.0005) optimal |
| GBPUSD | ~1.34 | ±0.0005, ±0.0010, ±0.0015, ±0.0020, ±0.0030, ±0.0050 | 5-50 pip tolerances. ±5pip (0.0005) optimal |
| XAUUSD | ~3,000 | ±2, ±5, ±10, ±15, ±20, ±30 | Tight precision for gold |
| USOIL (WTI) | ~90 | ±0.5, ±1, ±2, ±3, ±5, ±10 | Commodity scale — tighter than indices |
| US Stocks ($50-$300) | ~$50-$300 | ±0.5, ±1, ±2, ±3, ±5, ±8, ±10 | Stock scale — yfinance data validated on SYNA |

Always test multiple tolerances and pick the one with the highest Wick Precision Score per timeframe.

### **3. Multi-Timeframe Weighted Validation**

Key levels should be validated across **W1, D1, and H4** timeframes with ICT/CRT hierarchical weighting:

| Timeframe | Weight | Rationale |
|-----------|--------|-----------|
| **W1** | 50% | Highest-timeframe structure, most significant institutional levels |
| **D1** | 30% | Primary trading timeframe, original validation standard |
| **H4** | 20% | Intraday structure, entry/exit precision refinement |

**Scoring Components per Timeframe (composite out of 100):**
- **Wick Precision** (50% of TF score): `wick_rejections / interactions × 100` — where each interaction is a bar that touched the zone, and wick_rejection means the bar had a wick beyond the body in the direction of the level touch. Capped at 100%.
  - **⚠️ Critical:** A bar that closes AT its high (no upper wick) counts as an interaction but NOT as a wick rejection. Do NOT count total touches as wick rejections — they are different metrics.
  - **⚠️ Common pitfall:** If WP > 100% at larger tolerances (e.g., ±100 on H4), it means some bars trigger BOTH upper AND lower wick rejection counts. This is a counting artifact, not a real metric > 100%. Cap at 100%.
  - **GER40 23480.9 corrected finding (2026-05-04):** After fixing the Rejection Strength formula, GER40 23480.9 scores **99.7/100** — W1:100 (±5), D1:100 (±5), H4:98.5 (±50). All three TFs show 100% WP at tight tolerances. The prior claim of "~14-16% WP at ±5" was based on a buggy RS formula that distorted tolerance selection.
- **Interaction Count** (30% of TF score): `100` if ≥2 interactions, `50` if 1, `0` if none
- **Rejection Strength** (20% of TF score): `min(avg_rejection_pct / 30 × 100, 100)`
  - **⚠️ Correct formula:** `rejection_pct = wick_length / bar_range × 100` where `wick_length = high - max(open, close)` (for upper/high touches) or `min(open, close) - low` (for lower/low touches), and `bar_range = high - low`
  - **This measures how much of the bar's total range was the wick** — a 30%+ wick means price was pushed back significantly after touching the level
  - **❌ Wrong formula (pre-2026-05-04):** `(high - close) / high × 100` — this produces values <1% because it divides by price magnitude instead of bar range, making RS always near zero

**Overall Score = Σ (TF_composite × TF_weight)**

| Score Range | Verdict | Display |
|-------------|---------|---------|
| **90–100** | ✅ HIGH CONFIDENCE — 必須回報，高參考價值 | 🟢 綠色 |
| **70–89** | ⚠️ MEDIUM — 可參考，但信心不足 | 🟠 橙色 |
| **< 70** | ❌ LOW — 參考價值低 | 🔴 紅色 |

**Ian 的硬性要求：低於 90 分的關鍵位一律不回報。** 寧可回報遠一點但高分的位，也不要近距離低分位的噪音。低分位完全沒有參考價值。

**⚠️ 顯示要求：** 每個 Key Level 都必須顯示分數。格式：`Score: XX/100 [W1:XX D1:XX H4:XX]`，並用顏色區分置信度。

### **Data requirements per timeframe:**
- W1: 500+ bars (~10 years) — minimum 200 bars to pass cache validation
- D1: 999+ bars (~4 years) — minimum 500 bars to pass cache validation
- H4: 5000+ bars (~5 years) — minimum 2000 bars to pass cache validation

### **⚠️ ATH (All-Time High) Scenario**

When price is at or near all-time highs:
- **Swing high detection yields zero levels above current price** — this is methodologically correct, not a bug
- All detected key levels will be **supports** (below current price)
- The absence of resistance above price = **"blue sky"** territory
- **Scoring consequence:** Even with multi-tolerance testing, no >90 score levels will be found above price
- **Fallback:** When no >90 levels exist above, report the nearest support below and note "ATH — no historical resistance above"
- **Scoring caveat for new ATH supports:** After a strong rally to ATH, nearby support levels will score below 90 because they haven't accumulated enough historical interactions yet (W1 score = 0 since price never tested those levels from above). This is methodologically correct — report the nearest multi-TF support anyway with its actual score and note "new level, insufficient historical tests"
- **Trading implication:** Without historical resistance, upside targets must use: (a) extension levels (Fibonacci), (b) psychological round numbers, (c) volatility projections

### **⚠️ IG Weekend Price URLs — Use EN version**

When scraping IG weekend prices:
- **Always use `ig.com/en/...`** — the English version returns complete data
- **Avoid `ig.com/cn/...`** — the Chinese version may return 404 (NAS100 CN URL was 404, GER40 CN worked but gave partial data)
- Verified working URLs (2026-04-19):
  - NAS100: `https://www.ig.com/en/indices/markets-indices/weekend-us-tech-100-e1`
  - GER40: `https://www.ig.com/en/indices/markets-indices/weekend-germany-40`

### **⚠️ Price Era Validation Rule**

Before running Wick Precision analysis, **check whether the price was ever near the level during the data range**:

- For a level at 23480.9 on GER40, if data starts from 2016 when price was ~10,000, the first ~8 years of bars will have zero interactions (price never reached the zone).
- **Solution:** Start analysis from the first bar where `High >= level * 0.85` (i.e., price entered the 85% threshold of the target level). This ensures you're only analyzing bars from the era when the price was actually trading in that zone.
- **Important:** This is a logical correctness fix, not a numerical one — bars without interactions don't affect Wick Precision ratios (neither numerator nor denominator). But it prevents misleading date ranges and ensures analysis makes methodological sense.
- **Implementation:** Find first index where `bar['high'] >= level * 0.85`, slice from there, then run standard Wick Precision analysis.

### **4. Zone Clustering — Tiered Fixed-Range Method**

**⚠️ CRITICAL (2026-05-10): Do NOT use percentage-based clustering for grouping swing points into zones.** Percentage clustering fails because it scales with price:
- $5 stock × 2% = $0.10 → too narrow, over-fragmented clusters
- $900 stock × 2% = $18 → too wide, merges unrelated levels

### **4b. Cross-TF Key Level Zone Clustering (2026-05-29)**

When building Key Level zones for filtering or analysis, **raw swing points on individual TFs rarely coincide at the exact same price** — so simple exact-match scoring produces maximum scores of only ~50-80 (single-TF only). The solution is to **cluster nearby swing points across TFs** within a tolerance band and sum their scores.

**Why this matters:** In the NAS100 backtest (2026-05-29), exact-match scoring yielded 0 levels at score≥100. After cross-TF clustering (±30pts), 56 zones scored ≥100, and filtering false breakouts by these zones improved 1-bar accuracy from 48.7% → 72.2% (+23.5pp).

**Method:**
```python
def cluster_cross_tf_levels(raw_levels, cluster_radius=30):
    """
    raw_levels: list of (tf_name, price, score_weight) tuples
    cluster_radius: fixed dollar range for clustering (see tiered table above)
    
    Groups nearby levels across TFs, sums scores, recenters cluster.
    """
    raw_sorted = sorted(raw_levels, key=lambda x: x[1])
    clusters = []
    
    for tf, price, score in raw_sorted:
        found = False
        for cluster in clusters:
            if abs(price - cluster["center"]) <= cluster_radius:
                cluster["prices"].append(price)
                cluster["score"] += score
                cluster["count"] += 1
                cluster["tf_set"].add(tf)
                cluster["center"] = sum(cluster["prices"]) / len(cluster["prices"])
                found = True
                break
        if not found:
            clusters.append({
                "center": price, "score": score, "count": 1,
                "prices": [price], "tf_set": {tf}
            })
    
    clusters.sort(key=lambda x: x["score"], reverse=True)
    return clusters
```

**Typical inputs:**
- D1 swing points: weight 50 per swing
- H4 swing points: weight 30 per swing  
- Psychological round numbers (every 500pts for indices): weight 20

**Recommended cluster_radius by instrument:**
- Indices ~25K (NAS100, HK50, GER40): ±30pts
- Indices ~50K (JPN225): ±50pts
- BTCUSD: ±500pts
- XAUUSD: ±5pts

**Output interpretation:**
- Score ≥130: Strong multi-TF confluent zone (D1+H4+Psych or multiple D1 swings)
- Score 80-129: Good zone (D1+H4 confluence or multiple H4 swings)
- Score 50-79: Single-TF zone (use with caution)

**This cross-TF clustering should be the default approach when building Key Level zones for any filtering, backtesting, or trade validation.**

📄 **Full backtest results + data source comparison:** See `m15-amd-fakeout-analysis` skill → `references/key-level-clustering-backtest.md`

**Use tiered fixed-dollar ranges based on asset type and price scale:**

| Asset Type | Price Range | Clustering Range | Example |
|------------|-------------|-----------------|---------|
| Low-price stocks | <$20 | $1.0 | Penny/small-cap stocks |
| Mid-price stocks | $20–$200 | $3.0 | Most US stocks (SYNA, AAPL, etc.) |
| High-price stocks | $200–$500 | $5.0 | AVGO, etc. |
| Ultra-high stocks | >$500 | $10.0 | BRK.A, NVR |
| Forex pairs (AUDJPY, USDJPY) | ~80–200 | $0.5 | Pairs at ~100-200 range |
| Forex pairs (AUDJPY, USDJPY) | ~80–200 | $0.5 | Pairs at ~100-200 range |
| Forex majors (EURUSD, GBPUSD) | ~1.0–1.6 | 0.005 (50 pips) | 5-digit pairs — cluster in pip terms |
| Indices (GER40/DAX) | ~20K–30K | $30 | GER40 |
| Indices (HK50) | ~25K | $30 | HK50 |
| Indices (JPN225) | ~50K | $50 | JPN225 |
| BTCUSD | >50K | $500 | BTCUSD |
| Gold (XAUUSD) | ~2K–5K | $5 | XAUUSD |
| Commodities (USOIL) | ~80–100 | $2 | WTI crude |

**Implementation:**
```python
def get_cluster_range(price, asset_type="stock"):
    if asset_type == "forex_major": return 0.005  # EURUSD, GBPUSD (~1.0-1.6 range, 50 pips)
    elif asset_type == "forex_yen": return 0.5  # AUDJPY, USDJPY (~80-200 range)
    elif asset_type == "btc": return 500
    elif asset_type == "gold": return 5
    elif asset_type == "ger40": return 30
    elif asset_type == "hk50": return 30
    elif asset_type == "jpn225": return 50
    elif asset_type == "oil": return 2
    elif asset_type == "stock":
        if price < 20: return 1.0
        elif price < 200: return 3.0
        elif price < 500: return 5.0
        else: return 10.0
    else: return 3.0  # default

def cluster_swing_points(swings, cluster_range, current_price=None):
    """Cluster swing points within fixed dollar range"""
    if not swings: return []
    sorted_p = sorted(swings, key=lambda x: x['price'])
    clusters = []
    current_cluster = [sorted_p[0]]
    for p in sorted_p[1:]:
        if abs(p['price'] - np.mean([x['price'] for x in current_cluster])) <= cluster_range:
            current_cluster.append(p)
        else:
            clusters.append(current_cluster)
            current_cluster = [p]
    clusters.append(current_cluster)
    # Build results...
```

**Zone boundaries:** After clustering, treat each cluster as a zone with:
- Zone range: [min_price, max_price] of all swings in cluster
- Zone center: average of all swings
- Zone thickness: max_price - min_price (should be ≤ 2× cluster_range)

---

## 📊 Validated Parameters (Based on 999 D1 Bars Analysis)

### **JPN225 Key Level Parameters**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Decimal Precision** | 1 place (e.g., 52644.1) | Validated by 100% wick precision score |
| **Optimal Tolerance** | ±5 points | High-precision levels show tight clustering |
| **Zone Threshold** | < 50 points spread | Levels within 50 pts form a zone |
| **Min Tests for Confirmation** | 2+ interactions | Statistical significance |
| **Min Wick Precision** | > 70% | Strong wick-based rejection |
| **Min Rejection %** | > 30% | Meaningful price rejection |

---

## 🔧 Usage

### **Before Running Analysis — Check Cache First**

ALWAYS check the cache before downloading data:

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.hermes/data/key-level-cache"))
from cache_manager import CacheManager

cache = CacheManager()
status = cache.get_status(SYMBOL)

if status["has_cached_result"]:
    # Return cached result — no download needed
    print(f"Using cached result for {SYMBOL}")
    # ... display from status["result"]
else:
    # Download ONLY expired timeframes
    for tf in status["expired_tfs"]:
        download_data(SYMBOL, tf)  # via Alfred or TradingView
        cache.save_data(SYMBOL, tf, bars, last_price)
    # Load all TFs (mix of cached + freshly downloaded)
    # ... run analysis, then save:
    cache.save_result(SYMBOL, result_dict)
```

### 📁 Reusable Analysis Script

A standalone analysis script is available at:
`~/.hermes/skills/openclaw-imports/ian-key-level/scripts/analyze_key_levels.py`

```bash
# Requires data pre-fetched to ~/.hermes/data/key-level-cache/data/{SYMBOL}/{W1,D1,H4}.json
python3 ~/.hermes/skills/openclaw-imports/ian-key-level/scripts/analyze_key_levels.py NAS100
python3 ~/.hermes/skills/openclaw-imports/ian-key-level/scripts/analyze_key_levels.py GER40 30
```

Auto-detects cluster range and tolerances by symbol. Outputs scored levels + `PLOT|` lines for chart plotting.

### **Record a New Key Level**

When user confirms a key level:

```markdown
1. Verify level follows methodology:
   - 1 decimal place precision (e.g., 52663.2)
   - Based on wick analysis (not body close)
   - Micro-adjusted from round number

2. Check for existing nearby levels:
   - If within 50 points → forms a zone
   - If within 5 points → potential refinement

3. Record in MEMORY.md:
   | Date | Instrument | Key Level | Type | Notes |
   |------|------------|-----------|------|-------|
   | 2026-03-27 | JPN225 | 52663.2 | Ian's Key | Confirmed - resistance zone |
```

### **Validate a Proposed Level**

When user proposes a level for validation:

**⚠️ First check cache:** Use `cache.get_status(SYMBOL)` as described above. Only download expired TFs.

```markdown
1. Load data (prefer MT5 CFD data from Alfred bridge):
   - Check cache first: cache.get_status(SYMBOL)
   - Download only expired timeframes
   - Or load cached: cache.get_cached_data(SYMBOL, tf)

2. Run analysis on EACH timeframe (W1, D1, H4):
   - Test multiple tolerances (±5, ±10, ±15, ±20, ±30, ±50)
   - Calculate: Wick Precision, interactions count, avg rejection %
   - Pick best tolerance (highest Wick Precision) per timeframe
   - Compute TF composite score:
     score = (WP × 0.50) + (interaction_score × 0.30) + (rejection_score × 0.20)

3. Compute weighted overall score:
   overall = (W1_score × 0.50) + (D1_score × 0.30) + (H4_score × 0.20)

4. Assess by score range:
   ≥90:   ✅ HIGH CONFIDENCE — 必須回報
   < 90:  ❌ 不回報 — 沒有參考價值

5. Save result to cache: cache.save_result(SYMBOL, result_dict)

6. Report:
   - Per-TF table (best tolerance, WP, interactions, rejection, pass/fail)
   - Weighted score breakdown
   - Overall verdict
   - Recent interaction dates with OHLC details
```

### **Discover Key Levels for a Symbol**

When user asks "what are the nearest key levels for X?" (no specific level proposed):

**⚠️ First check cache:** Use `cache.get_status(SYMBOL)`. If cached result exists, return it immediately.
```markdown
1. **⚠️ Data source priority (2026-06-03):** Alfred MT5 > TradingView MCP > TradingView browser. Always try Alfred first for CFD symbols. Only fall back if the symbol is not found on MT5.

2. Check cache: cache.get_status(SYMBOL)
   - If has_cached_result: display and done
   - Otherwise: download only expired timeframes from Alfred (preferred) or TradingView (fallback)
   - ⚠️ Alfred v2.2 data uses `time_epoch` — convert to `time` after loading

3. Fetch data via Alfred (preferred):
   python3 alfred_client.py multi HK50 --tf W1 --count 300 --output cache_dir
   python3 alfred_client.py multi HK50 --tf D1 --count 999 --output cache_dir
   python3 alfred_client.py multi HK50 --tf H4 --count 5000 --output cache_dir
   Then convert time_epoch → time in the saved JSON files.
   Or fallback to TradingView MCP: chart_set_timeframe + data_get_ohlcv (only ~300 bars each TF).
   cache.save_data(SYMBOL, tf, bars, last_price)

3. Detect swing points on each timeframe:
   - W1: swing=1 (nearest neighbor comparison)
   - D1: swing=2 (2 bars on each side)
   - H4: swing=3 (3 bars on each side)
   A swing high = candle with highest high among N neighbors on each side
   A swing low = candle with lowest low among N neighbors on each side

4. Cluster nearby swing points using **fixed-dollar range** (NOT percentage):
   - Use `get_cluster_range(price, asset_type)` to get the appropriate range
   - Default: $3.0 for US stocks ($20-$200 range)
   - Group swings within cluster_range of each other
   - Average the clustered prices
   - Record frequency (how many swing points in cluster)
   - Record most recent touch date
   - Record zone boundaries (min/max price in cluster)

5. Rank by distance from current price (nearest first)
   - Separate into resistance (above price) and support (below price)
   - Also identify nearby psychological round numbers (1000, 5000, 10000, etc.)

6. Validate top 5-7 nearest levels using multi-TF weighted scoring (see "Validate a Proposed Level")

7. Save result: cache.save_result(SYMBOL, result_dict)

8. Report:
   - Top resistance levels with scores and distances
   - Top support levels with scores and distances
   - Highlight strongest confirmed levels
```

### **Plot Key Levels on TradingView**

**Method A: Pine Script (RECOMMENDED — most reliable)**
When MCP is down or unreliable, write a Pine Script indicator and add it via the Pine Editor:
```pinescript
//@version=6
indicator("Key Levels", overlay=true, max_lines_count=500, max_labels_count=500)
// Draw lines + labels for each level
// See tradingview-pine-indicator skill for full patterns
```
Use `browser_type` to inject the script into the Pine Editor textarea, then click "Add to chart".

**Method B: MCP draw_shape (when MCP is available)**
When `tradingview-mcp` skill is available, plot scored levels directly on the chart:

```python
# Set chart to D1 for best visibility
chart_set_timeframe(timeframe="D")

# Draw horizontal lines for each level
# Resistance = red (#EF4444), Support = green (#10B981), Strong (≥85) = orange (#F59E0B)
draw_shape(shape="horizontal_line",
    point={"time": last_bar_time, "price": level_price},
    overrides={"linecolor": "#10B981", "linewidth": 2, "linestyle": 2})

# Add text labels
draw_shape(shape="text",
    point={"time": last_bar_time - 86400*3, "price": level_price},
    text=f"SUP {level_price} ({score}/100)",
    overrides={"color": "#10B981", "fontSize": 12})

# Capture screenshot for verification
capture_screenshot(filename="{SYMBOL}_key_levels", region="chart")
```

Color convention: 🔴 red = resistance, 🟢 green = support, 🟡 orange = strongest (≥85 score).

### **Analyze Level Clusters**

When multiple levels exist:

```markdown
1. Calculate zone spread:
   zone_spread = max(levels) - min(levels)

2. Use the tiered cluster_range for the asset type (see Section 4):
   - US stocks: $3.0 (default)
   - Forex: $0.5, BTC: $500, Gold: $5, etc.

3. If zone_spread <= 2 × cluster_range:
   → Levels form a ZONE
   → Trade the zone, not individual levels
   → Entry/exit based on zone boundaries

4. Document zone:
   - Zone range: [min_level, max_level]
   - Zone thickness: spread points
   - Primary level: most tested/refined (center of cluster)
```

---

## 📈 Confirmed Levels (Live Reference)

**Load from MEMORY.md** → Section: "🎯 Ian's Key Levels (Recorded)"

Current confirmed levels are maintained in:
`C:/Users/AC/.openclaw/workspace/MEMORY.md`

---

## 🔍 Analysis Workflow

### **Step 1: Load Data**
```python
import json, pandas as pd

# Load MT5 JSON data (from Alfred bridge cache)
with open('~/.hermes/data/mt5/GER40_d1.json') as f:
    raw = json.load(f)
df = pd.DataFrame(raw['data'])
df['time'] = pd.to_datetime(df['time'])
df.set_index('time', inplace=True)

# Use last 1000 bars for analysis
if len(df) > 1000:
    df = df.tail(1000)
```

### ⚠️ CacheManager.get_cached_data() returns a tuple (2026-05-10 confirmed)

`cache.get_cached_data("GER40", "W1")` returns `(data_list, metadata)` — a **tuple**, not a list directly.

```python
# WRONG — causes TypeError: list indices must be integers or slices, not str
w1_data = cache.get_cached_data("GER40", "W1")
max_high = max(b['high'] for b in w1_data)  # FAILS!

# CORRECT — unpack the tuple
w1_data = cache.get_cached_data("GER40", "W1")[0]  # [0] = data list
max_high = max(b['high'] for b in w1_data)  # Works
```

Always index `[0]` when using `get_cached_data()` in analysis scripts.

### **Step 2: Find Level Interactions**
```python
def find_interactions(df, level, tolerance=5):
    """Find candles that touched the level within tolerance"""
    interactions = []
    for idx, row in df.iterrows():
        if (row['high'] >= level - tolerance and row['high'] <= level + tolerance) or \
           (row['low'] >= level - tolerance and row['low'] <= level + tolerance):
            
            # Classify interaction
            if row['high'] >= level - tolerance and row['high'] <= level + tolerance:
                body_top = max(row['open'], row['close'])
                is_wick = row['high'] > body_top  # Upper wick exists beyond body
                interactions.append({'date': idx, 'type': 'wick_high' if is_wick else 'body_high'})
            else:
                body_bottom = min(row['open'], row['close'])
                is_wick = row['low'] < body_bottom  # Lower wick exists beyond body
                interactions.append({'date': idx, 'type': 'wick_low' if is_wick else 'body_low'})
    
    return interactions
```

### **Step 3: Calculate Metrics (per timeframe)**
```python
interactions = find_interactions(df, level=52663.2, tolerance=5)
wick_count = sum(1 for i in interactions if i['type'].startswith('wick'))
wick_precision = (wick_count / len(interactions)) * 100 if interactions else 0

# Calculate rejection strength: wick length as % of bar range
rej_pcts = []
for i in interactions:
    if i['type'].startswith('wick'):
        row = df.loc[i['date']]
        bar_range = row['high'] - row['low']
        if bar_range > 0:
            if 'high' in i['type']:
                wick_len = row['high'] - max(row['open'], row['close'])
            else:
                wick_len = min(row['open'], row['close']) - row['low']
            rej_pcts.append(wick_len / bar_range * 100)

avg_rejection_pct = sum(rej_pcts) / len(rej_pcts) if rej_pcts else 0

# TF composite score (0-100)
wp_score = min(wick_precision, 100)
intx_score = 100 if len(interactions) >= 2 else (50 if len(interactions) == 1 else 0)
rej_score = min(avg_rejection_pct / 30 * 100, 100)
tf_composite = (wp_score * 0.50 + intx_score * 0.30 + rej_score * 0.20)
```

### **Step 4: Multi-Timeframe Weighted Score**
```python
# Weights per ICT/CRT HTF hierarchy
weights = {'W1': 0.50, 'D1': 0.30, 'H4': 0.20}
total_weight = 0
weighted_score = 0

for tf_name, weight in weights.items():
    score = tf_scores[tf_name]  # from Step 3
    weighted_score += score * weight
    total_weight += weight

overall_score = (weighted_score / total_weight)

# Verdict — Ian's rule: only ≥90 gets reported
if overall_score >= 90: verdict = "✅ HIGH CONFIDENCE — 必須回報"
else: verdict = "❌ 低於90分 — 不回報"
```

### **Step 5: Report**
Test multiple tolerances programmatically (±5, ±10, ±15, ±20, ±30, ±50) per timeframe, pick the best tolerance per TF, compute weighted overall score, and report full breakdown.

---

## 🎓 ICT/CRT Methodology Notes

### **Why 1 Decimal Place?**
- **Wick extremes** often end in non-round numbers
- **Precision reflects actual price action**, not arbitrary rounding
- **Micro-adjustments** (e.g., 52644.1 → 52663.2) show level refinement based on newer data

### **Why Tight Tolerance (±5 pts)?**
- Analysis shows **100% wick precision** at confirmed levels
- Price respects levels with **high accuracy**
- Wide tolerance dilutes level significance

### **Why Zone Clustering?**
- Multiple levels within 50 points indicate **institutional interest zone**
- Banks/institutions defend **zones**, not single price points
- Trading the zone provides **better risk/reward**

---

## 📊 Recently Validated Levels

| Date | Instrument | Level | W1 | D1 | H4 | Overall | Verdict |
|------|-----------|-------|-----|-----|-----|:-------:|---------|
| 2026-05-06 | HK50 | 25707.0 | 91.8 | 100 | 99.5 | **95.8** | ✅ HIGH |
| 2026-05-06 | GER40 | 23859.5 | 100 | 100 | 98.2 | **99.6** | ✅ HIGH |
| 2026-05-06 | XAU | 4405.1 | 100 | 100 | 100 | **100.0** ⭐ | Triple-100 |
| 2026-05-06 | XAU | 4857.0 | 100 | 100 | 100 | **100.0** ⭐ | Triple-100 |
| 2026-05-06 | XAU | 4651.6 | 96 | 99.1 | 100 | **97.7** | ✅ HIGH |
| 2026-05-06 | XAU | 4099 | 100 | 100 | 85 | **97.0** | ✅ HIGH |
| 2026-05-07 | AUDJPY | 112.404 | 97.4 | 98.8 | 98.0 | **97.9** | ✅ HIGH (yfinance data) |
| 2026-05-10 | SYNA | $108.7 (RES) | 100 | 100 | 100 | **100.0** ⭐ | Triple-100 (US stock, yfinance) |
| 2026-05-10 | SYNA | $104.0 (SUP) | 100 | 100 | 100 | **100.0** ⭐ | Triple-100 (US stock, yfinance) |
| 2026-05-10 | SYNA | $116.1 (RES) | 100 | 100 | 100 | **100.0** ⭐ | Triple-100 (US stock, yfinance) |
| 2026-05-10 | XAUUSD | 4857.0 (RES) | 100 | 100 | 100 | **100.0** ⭐ | Triple-100 (XAUUSD, TV CFD data) |
| 2026-05-10 | XAUUSD | 4500.6 (SUP) | 100 | 93.6 | 100 | **98.1** | Triple-100 W1+H4, D1 93.6 (XAUUSD, TV CFD) |
| 2026-05-10 | XAUUSD | 4681.7 (SUP) | 96.9 | 95.5 | 100 | **97.1** | Triple TF, H4 54 interactions (XAUUSD, TV CFD) |
| 2026-05-11 | SYNA | $95.5 (SUP) | 100 | 94(±5) | 100 | **98.1** | 269x D1 — decade-long supply wall (US stock, yfinance, fixed-$3 clustering) |
| 2026-05-11 | SYNA | $115.5 (SUP) | 100 | 100 | 100 | **100.0** ⭐ | Triple-100, breakout retest zone |
| 2026-05-11 | SYNA | $108.2 (SUP) | 100 | 98(±1) | 100 | **99.3** | 46x D1, major 2024 base |
| 2026-05-11 | CRM | $179.7 (current) | — | — | — | — | Resistance $184.4, Support $172.6 (quick scan) |
| 2026-05-11 | WDAY | $125.7 (current) | — | — | — | — | Resistance $132.6, Support $121.7 (quick scan) |
| 2026-05-11 | NOW | $91.1 (current) | — | — | — | — | Resistance $94.8, Support $88.2 (quick scan) |
| 2026-05-27 | NAS100 | 28661.4 (SUP) | 85 | 85 | 85 | **85.0** | Multi-TF support at ATH, no >90 levels (insufficient historical tests at new highs) |
| 2026-05-27 | NAS100 | 29373.1 (SUP) | 0 | 89 | 99 | **46.3** | W1:0 (never tested from above) — new ATH support |
| 2026-06-03 | HK50 (MT5) | 25519.9 (SUP) | 100 | 100 | 89 | **97.8** | Alfred MT5 — 300 W1, 999 D1, 5000 H4 |
| 2026-06-03 | HK50 (MT5) | 25513.1 (SUP) | 100 | 93 | 99 | **97.6** | Tight 12-point cluster with 25519.9 |
| 2026-06-03 | HK50 (MT5) | 25454.2 (SUP) | 85 | 100 | 95 | **91.5** | 7x H4 tests confirm strong floor |
| 2026-06-03 | HK50 (MT5) | 24376.0 (SUP) | 93 | 100 | 100 | **96.5** | Deep major floor — triple-100 potential |
| 2026-06-03 | HK50 (MT5) | 24430.1 (RES) | 85 | 100 | 98 | **92.1** | Former support turned resistance |
| 2026-06-03 | GBPUSD (MT5) | 1.34474 (RES) | 100 | 94 | 100 | **98.3** | Alfred MT5 — tight 5-pip tolerance, 71x H4 |
| 2026-06-03 | GBPUSD (MT5) | 1.3432 (SUP) | 100 | 96 | 98 | **98.5** | 4x W1, 7x D1, 52x H4 |
| 2026-06-03 | GBPUSD (MT5) | 1.34675 (RES) | 100 | 100 | 99 | **99.6** | Triple-100 potential, 198x H4 interactions |
| 2026-06-03 | GBPUSD (MT5) | 1.35708 (RES) | 100 | 99 | 99 | **99.4** | Ceiling resistance, 357x H4 tests |
| 2026-06-03 | GBPUSD (MT5) | 1.33261 (RES) | 98 | 100 | 100 | **98.8** | Triple-100 potential |
| 2026-06-03 | GBPUSD (MT5) | 1.3373 (RES) | 100 | 98 | 95 | **98.6** | Major resistance below price |

---

## 📝 Example: JPN225 Resistance Zone

**Confirmed Levels:**
- 52644.1 (2026-03-24)
- 52663.2 (2026-03-27)

**Zone Analysis:**
```
Zone Range: 52644.1 - 52663.2
Zone Thickness: 19.1 points
Wick Precision: 100% (both levels)
Optimal Tolerance: ±5 points each

Assessment: HIGH PRECISION RESISTANCE ZONE
Trading Implication: 
  - Look for shorts in 52644-52663 zone
  - Stop loss: above 52670 (zone + buffer)
  - Target: next support level below
```

---

## 🔄 Level Refinement Process

When a level is **micro-adjusted** (e.g., 52644.1 → 52663.2):

1. **Reason for adjustment:**
   - New wick data (later wicks carry more weight)
   - Price action invalidated old level
   - More precise swing point identified

2. **Document both levels:**
   - Old level → Historical reference
   - New level → Active key level

3. **Update MEMORY.md:**
   - Add new level with date
   - Keep old level for context
   - Note the refinement reason

---

## ⚠️ Limitations

- **Forward-testing levels:** Levels above current price cannot be validated historically
- **Timeframe dependency:** Validation now runs across W1/D1/H4 with weighted scoring (W1=50%, D1=30%, H4=20%). Individual TF results may differ — the overall weighted score is the definitive assessment
- **Market context:** Levels work best when aligned with market structure (HTF bias)
- **Instrument-agnostic:** This methodology works on any instrument (GER40, NAS100, US500, JPN225) — tolerance thresholds may need scaling for different point values
- **Data source matters:** Index data (Yahoo Finance) and CFD data (MT5 broker) produce different validation results. Always use broker-matching CFD data for key level validation
- **Yahoo Finance caveat:** ^GDAXI (DAX index) and GER40 (Pepperstone CFD) diverge by hundreds of points — validation results can flip from FAIL to PASS

---

## 🔌 Data Sources

### ⭐ PRIMARY: Alfred MT5 Bridge (ZeroMQ) — USE THIS FIRST
**Always prefer Alfred MT5 when the CFD symbol is available.** It provides the deepest historical data (999+ D1 bars, 5000+ H4 bars, 300+ W1 bars) and matches broker pricing exactly.

**⚠️ 2026-06-03 Lesson:** When asked to find key levels for a CFD asset (HK50, GER40, NAS100, etc.), do NOT default to TradingView data. Alfred MT5 has 5-16x more bars per timeframe. Always check Alfred first with `alfred_client.py ping`, then `data SYM --tf D1 --count 3` to verify the symbol exists. Only fall back to TradingView if the symbol is not found on MT5.

Alfred runs MT5 on a Windows PC (192.168.11.211:5555). See `alfred-mt5-bridge` and `alfred-mt5-data` skills.

```bash
# Check connection
python3 alfred_client.py ping

# Verify symbol exists (quick spot check)
python3 alfred_client.py data HK50 --tf D1 --count 3

# Fetch multi-TF data for analysis (saves JSON to cache)
python3 alfred_client.py multi HK50 --tf W1 --count 300 --output ~/.hermes/data/key-level-cache/data/HK50
python3 alfred_client.py multi HK50 --tf D1 --count 999 --output ~/.hermes/data/key-level-cache/data/HK50
python3 alfred_client.py multi HK50 --tf H4 --count 5000 --output ~/.hermes/data/key-level-cache/data/HK50
```

**Data output:** JSON files at `~/.hermes/data/key-level-cache/data/{SYMBOL}/HK50_{tf}.json`
**Data format (Alfred v2.2+):** Bars use `time_epoch` (int), `time_utc`, `time_ny`, `time_hkt`, plus `open/high/low/close/volume`. The `time` string field no longer exists.

**⚠️ Conversion required:** Analysis scripts expect `time` field. Convert after loading:
```python
for b in bars:
    b["time"] = b["time_epoch"]
```

To load for analysis:
```python
import json
with open('~/.hermes/data/key-level-cache/data/HK50/HK50_d1.json') as f:
    raw = json.load(f)
bars = raw["data"]
for b in bars:
    b["time"] = b["time_epoch"]  # v2.2 fix
```

### Secondary: TradingView Browser Extraction (CFD Data)
**Use when MT5/Alfred is unavailable. Provides CFD broker data including Pepperstone.**
### Secondary: TradingView Browser Extraction (CFD Data)
**Use when MT5/Alfred is unavailable. Provides CFD broker data including Pepperstone.**

Extract OHLCV data directly from TradingView's internal JavaScript objects via `browser_console`:

**⚠️ 2026-05-30 API Update:** The old `_exposed_chartWidgetCollection` path often returns 0 bars or `undefined` in the 2026 TradingView web UI. The reliable path is via `TradingViewApi`:

```javascript
// Working path (2026-05-30 verified):
const tv = window.TradingViewApi;
const wv = tv._activeChartWidgetWV;
const val = wv._value;
const cw = val._chartWidget;
const model = cw.model();
const ms = model.mainSeries();
const barsObj = ms.bars();
const items = barsObj._items;

// items[i].value = [time_epoch, open, high, low, close, volume]
const bars = [];
for (let i = 0; i < items.length; i++) {
  const v = items[i].value;
  bars.push({time: v[0], open: v[1], high: v[2], low: v[3], close: v[4], volume: v[5]});
}
```

**If `TradingViewApi` is undefined**, the page may not have fully loaded or JS context changed — re-navigate and retry. If `_activeChartWidgetWV` exists but `_value` is empty, try accessing `val._chartWidget._paneWidgets._value[0].mainDataSource` for alternative data paths.

**Fallback: Pine Script for chart plotting** — When direct JS drawing (`model.createLineTool`, `model.createPriceLine`) fails due to API changes, write a Pine Script indicator and have the user click "Add to chart" in the Pine Editor panel. This is the most reliable way to plot levels when the JS drawing API is unstable.

**Step-by-step extraction:**
```python
# 1. Navigate to TradingView chart with specific symbol
browser_navigate("https://www.tradingview.com/chart/?symbol=PEPPERSTONE:GER40")
# Note: www.tradingview.com is the standard URL

# 2. Wait for chart to fully load (~5 seconds)
# Verify by checking page title contains the symbol name

# 3. Extract OHLCV bars via browser_console with this JavaScript:
# e.g., type "30" for M30, "D" for daily, "240" for H4

# 4. Extract OHLCV bars via browser_console with this JavaScript (NEW 2026-06-03):
```
```javascript
(() => {
  // NEW path via TradingViewApi (old _exposed_chartWidgetCollection path is broken)
  const tv = window.TradingViewApi;
  if (!tv || !tv._activeChartWidgetWV || !tv._activeChartWidgetWV._value) {
    return JSON.stringify({error: "No TradingViewApi or widget value found"});
  }
  
  const val = tv._activeChartWidgetWV._value;
  const cw = val._chartWidget;
  if (!cw) return JSON.stringify({error: "No _chartWidget"});
  
  const model = cw.model();  // model is a FUNCTION — call it
  if (!model) return JSON.stringify({error: "No model"});
  
  const ms = model.mainSeries();  // mainSeries is also a FUNCTION
  if (!ms) return JSON.stringify({error: "No mainSeries"});
  
  const barsObj = ms.bars();  // bars() returns object with _items
  if (!barsObj || !barsObj._items) return JSON.stringify({error: "No bars"});
  
  // _items[i].value = [time, open, high, low, close, volume]
  const items = barsObj._items;
  const bars = [];
  for (let i = 0; i < items.length; i++) {
    const v = items[i].value;
    bars.push({
      time: v[0],
      open: v[1],
      high: v[2],
      low: v[3],
      close: v[4],
      volume: v[5] || 0
    });
  }
  return JSON.stringify({count: bars.length, bars: bars});
})()
```
```python
# 5. Parse the JSON output and save for analysis
# Data format matches MT5: [{"time": unix_timestamp, "open": ..., "high": ..., ...}, ...]
# Note: ~300 visible bars max in browser view (sufficient for D1, limited for H4/W1)

# 6. To get more historical data on lower TFs (H4, etc.), navigate to a higher TF first
# then use browser scrolling to load more bars before switching back
```

**⚠️ Key differences from old method:**
- `cw.model()` — `model` is a **function**, not a property. Must call it.
- `model.mainSeries()` — `mainSeries` is also a **function**.
- `ms.bars()` — returns object with `_items` array, not a direct array.
- `_items[i].value` is an **array**: `[time, open, high, low, close, volume]` (not an object with named keys).

**Instrument mappings for TradingView URLs:**
| Instrument | TradingView URL pattern | Status |
|------------|------------------------|--------|
| GER40 | `https://tw.tradingview.com/chart/?symbol=PEPPERSTONE:GER40` | ✅ Works |
| NAS100 | `https://tw.tradingview.com/chart/?symbol=PEPPERSTONE:USTECH100` | ✅ Works |
| US500 | `https://tw.tradingview.com/chart/?symbol=PEPPERSTONE:US500` | ✅ Works |
| JPN225 | `https://tw.tradingview.com/chart/?symbol=PEPPERSTONE:JPN225` | ✅ Works (CFD data, verified 2026-05-11) |
| XAUUSD | `https://tw.tradingview.com/chart/?symbol=PEPPERSTONE:XAUUSD` | ✅ Works |
| BTCUSD | `https://tw.tradingview.com/chart/?symbol=PEPPERSTONE:BTCUSD` | ✅ Works |
| HK50 | `https://tw.tradingview.com/chart/?symbol=PEPPERSTONE:HK50` | ✅ Works |
| AUDJPY | `https://tw.tradingview.com/chart/?symbol=PEPPERSTONE:AUDJPY` | ❌ "This symbol doesn't exist" |
| EURJPY | `https://tw.tradingview.com/chart/?symbol=PEPPERSTONE:EURJPY` | ⚠️ Unverified — TV forex CFDs inconsistent |
| AUDJPY | `https://tw.tradingview.com/chart/?symbol=PEPPERSTONE:AUDJPY` | ❌ "This symbol doesn't exist" — NOT available on TradingView |

**⚠️ Known Missing Symbols on TradingView:**
- `PEPPERSTONE:JAPAN225` — Does NOT exist (wrong name). Use **`PEPPERSTONE:JPN225`** instead — fully extractable CFD data on TradingView (verified 2026-05-11).
- `PEPPERSTONE:AUDJPY` — Does NOT exist. For forex pairs, use **yfinance** with `=X` suffix (e.g., `AUDJPY=X`). See yfinance section below for forex-specific guidance.

**⚠️ 2026-05-11 Correction:** Previous guidance said `PEPPERSTONE:JAPAN225` doesn't exist — correct, but the RIGHT symbol is **`PEPPERSTONE:JPN225`** which DOES exist and provides full CFD data on TradingView. Use this as primary data source when MT5/Alfred is unavailable. TVC:JP225 and INDEX:NIKKEI still return "This symbol doesn't exist".

**Limitations:**
- ~300 visible bars max in browser view (sufficient for D1, limited for W1/H4)
- H4 typically only yields ~3 months of data (Feb 2026+ on a 2026 system)
- W1 typically yields ~200-260 bars (5+ years)
- Need to scroll back in browser for more historical data (complex)
- CFD broker availability depends on TradingView listings
- **2026-04-30 Finding:** TradingView CFD data produces comparable key level scores to MT5 data. For GER40 23480.9, MT5 scores 99.7/100 and TV data yields similar high scores. This validates TV as a reliable fallback for level validation.

### Tertiary: TradingView MCP (CDP Bridge)
**Use when MT5/Alfred is unavailable. Requires `tradingview-mcp` skill setup.**

Fetch OHLCV via the TradingView Desktop CDP bridge (repo at `~/projects/tradingview-mcp`).

**CLI usage:**
```bash
# Set timeframe and fetch
cd ~/projects/tradingview-mcp
node src/cli/index.js timeframe --resolution D    # or W, 240, 60, etc.
node src/cli/index.js ohlcv --count 999           # outputs JSON to stdout
```

**⚠️ CLI output parsing:** The `ohlcv` command outputs non-JSON text (like `{timeframe}` responses) before/after the JSON object. Parse by extracting between the first `{` and last `}`:
```python
import json, sys
lines = sys.stdin.read().strip()
first = lines.find('{')
last = lines.rfind('}')
data = json.loads(lines[first:last+1])
bars = data.get('bars', [])
```

**Python MCP usage (in Hermes session):**
```python
# Use mcp_tradingview_chart_set_timeframe(timeframe="D")
# Then mcp_tradingview_data_get_ohlcv(count=999, summary=False)
```

**Timeframe codes:** `W` (weekly), `D` (daily), `240` (H4), `60` (H1), `15` (M15), `5` (M5), `1` (M1)

**⚠️ Visible bar limits (2026-05-29 confirmed):** TradingView MCP returns only **visible bars** on the chart, capped at **~300 bars across ALL timeframes**:
- D1: ~300 bars (~15 months) — sufficient for swing detection
- H4: ~300 bars (~50 days) — **insufficient for deep H4 validation** (needs 2000+ bars)
- M15: ~300 bars (~4 days) — **useless for any meaningful analysis**
- `chart_set_visible_range` snaps back to current view — cannot force historical loading
- `batch_run` with `get_ohlcv` action fails with "JS evaluation error"
- When H4 data is shallow, W1 and D1 carry more weight in scoring
- **Alfred MT5 comparison:** D1=500 bars (~24mo), H4=2000 bars (~15mo) vs TV's 300 for both

**Data format matches MT5:**
```json
{"time": 1779746400, "open": 29914.4, "high": 30066.9, "low": 29692.7, "close": 29881.4, "volume": 352464}
```

**Saving to cache:**
```python
meta = {
    "symbol": "NAS100", "timeframe": "D1", "bar_count": len(bars),
    "last_price": bars[-1]["close"], "last_bar_time": bars[-1]["time"],
    "cached_at": datetime.now(timezone.utc).isoformat(), "source": "tradingview-mcp"
}
with open(f"~/.hermes/data/key-level-cache/data/NAS100/D1.json", "w") as f:
    json.dump({"data": bars, "meta": meta}, f)
```

### ⚠️ Tertiary Fallback: Yahoo Finance (yfinance) — CONTEXT-DEPENDENT

**For FOREX pairs (AUDJPY, EURUSD, GBPJPY, etc.): ✅ ACCEPTABLE**
Forex yfinance tickers (`AUDJPY=X`, `EURUSD=X`, etc.) provide actual interbank forex rates that closely track CFD forex prices. Validated on AUDJPY 112.404 (2026-05-07): yfinance data produced strong multi-TF scores (W1:97.4, D1:98.8, H4:98.0, Overall: 97.9). **Safe to use for forex pair key level analysis.**

**For INDEX CFDs (GER40, NAS100, JPN225, etc.): ⚠️ NOT RECOMMENDED**
Yahoo Finance provides **index prices**, not **CFD prices**. These differ materially and can cause **wrong validation results**.

**Real examples:**
| Level | Data Source | Wick Precision | Result |
|-------|-------------|---------------|--------|
| GER40 23480.9 | Yahoo Finance (^GDAXI index) | 36.7% | ❌ FAIL |
| GER40 23480.9 | MT5 Alfred (Pepperstone CFD) | W1:100% D1:100% H4:96.9% | ✅ STRONG (99.7/100) |
| BTCUSD 77116 | MT5 Alfred (CFD, multi-TF) | W1:100% D1:100% H4:81.5% | ✅ STRONG (98.1/100) |
| JPN225 59998 | Yahoo Finance (^N225 index) | 80.7/100 MEDIUM | ⚠️ Caveated — CFD data needed |

Only use Yahoo Finance when MT5 is completely unavailable, and flag results as tentative.

**Yahoo Finance ticker mappings:**

| Category | Instrument | Ticker | Notes |
|----------|-----------|--------|-------|
| Forex | AUDJPY | AUDJPY=X | ✅ Safe for key level analysis |
| Forex | EURUSD | EURUSD=X | ✅ Safe for key level analysis |
| Forex | GBPUSD | GBPUSD=X | ✅ Safe for key level analysis |
| Forex | GBPJPY | GBPJPY=X | ✅ Safe for key level analysis |
| Forex | USDJPY | USDJPY=X | ✅ Safe for key level analysis |
| Index | GER40 (DAX) | ^GDAXI | ⚠️ Index data, not CFD |
| Index | NAS100 | ^NDX | ⚠️ Index data, not CFD |
| Index | US500 (S&P500) | ^GSPC | ⚠️ Index data, not CFD |
| Index | JPN225 (Nikkei) | ^N225 | ⚠️ Index data, not CFD |
| Index | US30 (Dow Jones) | ^DJI | ⚠️ Index data, not CFD |

**yfinance interval support (2026-05-06 confirmed):**
- `interval="1d"` → D1 data (max available, ~15,000+ bars for ^N225)
- `interval="1wk"` → W1 data (or resample D1 with `.resample('W').agg(...)`)
- `interval="4h"` → H4 data directly (~1,458 bars over 730d for ^N225)
- `interval="1h"` → H1 data (can resample to H4 if needed)
- **⚠️ Pandas resample case sensitivity:** Use lowercase `'4h'` NOT `'4H'` — pandas raises `ValueError: Invalid frequency: 4H`

**⚠️ yfinance MultiIndex Column Format (2026-05-10 confirmed):**
yfinance returns MultiIndex columns like `('Close', 'SYNA'), ('High', 'SYNA'), ...` where the ticker symbol is the second level. Standard flattening:
```python
df = yf.download(symbol, period='max', interval='1d', progress=False)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = [c[0] for c in df.columns]  # Extract 'Close', 'High', 'Low', 'Open', 'Volume'
df = df.reset_index()
```
For H1→H4 resampling:
```python
df_h1 = yf.download(symbol, period='max', interval='1h', progress=False)
if isinstance(df_h1.columns, pd.MultiIndex):
    df_h1.columns = [c[0] for c in df_h1.columns]
df_h1 = df_h1.reset_index()
df_h1['datetime'] = pd.to_datetime(df_h1.columns[0], utc=True)
df_h1 = df_h1.set_index('datetime')
df_h1_clean = df_h1[['Open','High','Low','Close']].dropna()
df_h4 = df_h1_clean.resample('4h').agg({'Open':'first','High':'max','Low':'min','Close':'last'}).dropna()
```

**⚠️ US Stock-Specific Tolerances (2026-05-10):**
For individual US stocks (price range ~$50-$500), the index tolerances (±5, ±10, ±15...) are too wide. Use:
```python
stock_tolerances = [0.5, 1, 2, 3, 5, 8, 10]  # For stocks priced $50-$300
```
These produce meaningful wick precision results. The standard index tolerance table does NOT apply to individual stocks.

**Important:** Yahoo Finance data may have mixed timezones. Always use:
```python
df['time'] = pd.to_datetime(df['time'], utc=True)
```

---

## 📞 Support

**Cache:** `~/.hermes/data/key-level-cache/`
**Analysis Script:** `~/.hermes/skills/openclaw-imports/ian-key-level/scripts/analyze_key_levels.py`
**TradingView MCP:** `~/projects/tradingview-mcp/` (CDP bridge for OHLCV + chart plotting)

---

*Version: 1.9.0*
*Created: 2026-03-27*
*Updated: 2026-06-03 — v1.9.0: Fixed TradingView browser extraction — old `_exposed_chartWidgetCollection` path broken. New path via `TradingViewApi._activeChartWidgetWV._value._chartWidget.model().mainSeries().bars()._items`. Bar values are arrays [time,open,high,low,close,vol], not objects. Added v1.8.0: Added forex pip-based tolerances (EURUSD, GBPUSD ±0.0005-0.0050). Added forex cluster range 0.005 (50 pips) for major pairs. Validated HK50 and GBPUSD via Alfred MT5 pipeline (300 W1 + 999 D1 + 5000 H4 bars). GBPUSD validated at ±5pip optimal tolerance with 71-357 H4 interactions. HK50 deep floor 24376.0 confirmed as 96.5/100.*
*Based on: JPN225 (999 D1), GER40 (W1/D1/H4), HK50 (W1/D1/H4), XAU (W1/D1/H4), BTCUSD (W1/D1/H4), AUDJPY (W1/D1/H4)*
*Validated by: Walker (ICT/CRT Analysis)*
