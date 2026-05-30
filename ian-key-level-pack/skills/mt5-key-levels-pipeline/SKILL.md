---
name: mt5-key-levels-pipeline
description: >
  End-to-end pipeline: fetch Alfred MT5 data, calculate Ian's Key Levels
  (W1/D1/H4 multi-TF weighted scoring), plot on TradingView chart via MCP,
  capture M30 screenshot, and deliver to user. Always use Alfred MT5 as
  primary data source — NEVER TradingView data for key level analysis.
version: 1.3.0
author: Walker
tags: trading, MT5, Alfred, key levels, TradingView, pipeline, ICT, screenshot
---

# MT5 Key Levels Pipeline

Fetch MT5 data from Alfred, compute key levels, plot on TradingView, capture and deliver screenshot.

## Prerequisites

- Alfred MT5 bridge running on 192.168.11.211:5555 (`alfred-mt5-data` skill)
- TradingView Desktop with CDP enabled (`tradingview-mcp` skill)
- Skills loaded: `alfred-mt5-data`, `tradingview-mcp` (analysis script is self-contained — `ian-key-level` is NOT required)

## Step-by-Step Workflow

### Step 1: Verify Alfred MT5 Connection

```bash
python3 ~/.hermes/skills/trading/alfred-mt5-bridge/scripts/alfred_client.py ping
```

Expected: `OK  | Alfred is online | MT5: True`

If MT5: False → wait or ask user to check Alfred PC. If "zombie" state (MT5: True but symbols fail), restart `alfred_server.py`.

### Step 2: Fetch W1/D1/H4 Data from Alfred

```python
import os
CACHE_DIR = os.path.expanduser("~/.hermes/data/key-level-cache/data/{SYMBOL}")
os.makedirs(CACHE_DIR, exist_ok=True)

ALFRED = "~/.hermes/skills/trading/alfred-mt5-bridge/scripts/alfred_client.py"

for tf, count in [("W1", 300), ("D1", 999), ("H4", 5000)]:
    terminal(f"python3 {ALFRED} multi {SYMBOL} --tf {tf} --count {count} --output {CACHE_DIR}", timeout=30)
```

Each download produces `HK50_w1.json`, `HK50_d1.json`, `HK50_h4.json` in the cache directory.

### Step 3: Convert Data to Analysis Format

**For Alfred MT5 data** (the `SYMBOL_w1.json` format with `time_epoch`):
```python
import json, os

for tf in ["w1", "d1", "h4"]:
    with open(os.path.join(CACHE_DIR, f"{SYMBOL.lower()}_{tf}.json")) as f:
        raw = json.load(f)
    bars = raw["data"]
    last_price = raw.get("last_price", bars[-1]["close"])
    
    converted = []
    for b in bars:
        converted.append({
            "time": b["time_epoch"],
            "open": b["open"], "high": b["high"],
            "low": b["low"], "close": b["close"],
            "volume": b.get("volume", 0)
        })
    
    meta = {"symbol": SYMBOL, "timeframe": tf.upper(), "bar_count": len(converted),
            "last_price": last_price, "last_bar_time": converted[-1]["time"], "source": "alfred-mt5"}
    
    with open(os.path.join(CACHE_DIR, f"{tf.upper()}.json"), "w") as f:
        json.dump({"data": converted, "meta": meta}, f, indent=2)
```

**For TradingView fallback data** (raw bars from `mcp_tradingview_data_get_ohlcv`):
```python
import json, os
# bars = list of {time, open, high, low, close, volume} from MCP ohlcv call
# Run once per TF after switching chart timeframe

for tf, bars in [("W1", w1_bars), ("D1", d1_bars), ("H4", h4_bars)]:
    meta = {"symbol": SYMBOL, "timeframe": tf, "bar_count": len(bars),
            "last_price": bars[-1]["close"], "last_bar_time": bars[-1]["time"],
            "source": "tradingview-mcp"}
    with open(os.path.join(CACHE_DIR, f"{tf}.json"), "w") as f:
        json.dump({"data": bars, "meta": meta}, f, indent=2)
```

TV data is already in the correct `{time, open, high, low, close, volume}` format — no conversion needed.

### Step 4: Run Multi-TF Key Level Analysis

Use the `ian-key-level` methodology. Key parameters:

| Parameter | Value |
|-----------|-------|
| W1 swing | 1 (nearest neighbor) |
| D1 swing | 2 (2 bars each side) |
| H4 swing | 3 (3 bars each side) |
| Cluster range (indices ~25K) | $30 |
| Tolerances | [5, 10, 15, 20, 30, 50] |
| Weights | W1: 50%, D1: 30%, H4: 20% |
| Min reportable score | ≥90 |

**Scoring formula:**
```
WP = wick_rejections / interactions × 100  (capped at 100)
Intx = 100 if ≥2 interactions, 50 if 1, 0 if 0
Rej = min(avg_rejection_pct / 30 × 100, 100)
TF_score = WP×0.50 + Intx×0.30 + Rej×0.20
Overall = W1×0.50 + D1×0.30 + H4×0.20
```

Output the top 5 high-confidence (≥90) levels, or the nearest 5 if none qualify.

### Step 5: Clean TradingView Chart

Remove all old drawings before plotting:

```python
# Ctrl+A then Delete
tv_ui_keyboard(key="a", modifiers=["ctrl"])
tv_ui_keyboard(key="Delete")
```

### Step 6: Plot Key Levels on TradingView (M30 Timeframe)

Set chart to M30 (standard delivery timeframe):
```python
tv_chart_set_timeframe(timeframe="30")
```

For each level:
```python
color = "#EF4444" if level["type"] == "RES" else "#10B981"
linewidth = 3 if level["overall"] >= 95 else 2

tv_draw_shape(shape="horizontal_line",
    point={"time": last_bar_time, "price": level["price"]},
    overrides={"linecolor": color, "linewidth": linewidth, "linestyle": 2})
```

Use `last_bar_time` from the H4 data.

### Step 7: Capture Screenshot

```python
tv_capture_screenshot(
    filename=f"{SYMBOL}_M30_key_levels_MT5_{YYYYMMDD}",
    region="chart"
)
```

Returns: `~/projects/tradingview-mcp/screenshots/{filename}.png`

### Step 8: Verify and Deliver

Deliver the screenshot as a chat attachment with markdown:

```markdown
## 📊 PEPPERSTONE:{SYMBOL} Key Levels — Alfred MT5 (W1:50% + D1:30% + H4:20%)
```

Include: current price, all scored levels with W1/D1/H4 breakdowns, zone analysis, and data source note.

## ⚠️ Pitfalls

### Symbol Availability — MT5 vs TradingView Fallback
NOT all symbols on TradingView exist on Alfred's Pepperstone MT5 feed.

**✅ Confirmed available on MT5:** HK50, GER40, NAS100, US500, US30, JPN225, US2000, XAUUSD, EURUSD, GBPUSD, BTCUSD, AUDJPY

**❌ Confirmed NOT on MT5 (use TV fallback):** TWN (Taiwan index — Pepperstone CFDs don't carry it)

**Verify before running:**
```bash
python3 alfred_client.py data SYMBOL --tf D1 --count 1
```
If "Symbol not found" → fall back to TradingView data:
1. `mcp_tradingview_data_get_ohlcv(count=300)` for each TF (switch chart TF between calls: W → D → 240)
2. Save to cache as `{TF}.json` format, then run analysis script normally
3. Note in output: "Data source: TradingView (300 bars/TF) — symbol not available on MT5"

**⚠️ `batch_run(action="get_ohlcv")` is broken** — fails with JS eval errors. Use individual `mcp_tradingview_data_get_ohlcv()` calls instead.

### ATH Discovery Pattern
When an instrument is near all-time highs (e.g., NAS100 at 30200+, TWN at 3943+), the scoring engine will produce **few or zero HIGH CONFIDENCE (≥90) levels**. This is **expected and correct** — the methodology requires multiple interactions at specific price levels to build confidence, and ATH instruments haven't revisited those levels enough times.

**What to report when no ≥90 levels exist:**
- List nearest supports by proximity with actual scores
- Highlight medium-confidence (70-89) as "notable"
- Note highest-scored deep levels separately
- State: "No HIGH CONFIDENCE levels (≥90) — instrument in blue-sky/ATH discovery mode"
- Do NOT lower threshold or fabricate confidence

### TradingView Pop-ups / Overlays
TradingView Desktop may show promotional pop-ups or modal overlays on the chart. Before capturing a screenshot, press `Escape` to dismiss any pop-up:
```python
tv_ui_keyboard(key="Escape")
```
If unsure, capture the screenshot first then use `vision_analyze` to verify it's clean. If a pop-up is visible, dismiss it and recapture.

### Script Syntax Corruption After Edits
The analysis script (`mt5_key_levels_pipeline.py`) is prone to silent syntax corruption when edited via `patch` — duplicate lines or partial merges can produce `SyntaxError` (e.g., `}N": 50,`). **Always verify the script runs** with a quick test after any patch. If SyntaxError, re-read the file fully before retrying the edit.

### TV MCP Troubleshooting Before Pipeline

Before running the pipeline, verify TradingView MCP is functional:
```python
tv_health_check  # Must return success with cdp_connected: true
```
If MCP is unreachable (timeout + "unreachable after N consecutive failures"):
1. **Kill duplicate server processes:** `pkill -f tradingview-mcp/src/server.js` (multiple instances cause conflicts)
2. **Check CDP port:** `curl -s http://localhost:9222/json/version` — if timeout, TV Desktop's CDP is stale
3. **Restart TV Desktop:** `killall TradingView && sleep 3 && /Applications/TradingView.app/Contents/MacOS/TradingView --remote-debugging-port=9222`
4. Wait 5s, then restart server: `node ~/projects/tradingview-mcp/src/server.js &`
5. Retry `tv_health_check`

### MCP Tool Availability for Plotting
Not all MCP tools work reliably after recovery. For the plotting step:
- ✅ **Use:** `draw_shape(shape="horizontal_line")` — confirmed working for drawing key level lines
- ❌ **Avoid:** `draw_list` ("getChartApi is not defined"), `chart_get_visible_range` ("evaluate is not defined")
- For `last_bar_time`, use OHLCV data from `data_get_ohlcv` or Alfred MT5 — don't rely on `chart_get_visible_range`

### Screenshot Capture — Two Methods
`capture_screenshot(method="cdp", region="chart")` may only capture the header/top portion of the chart (chart area appears blank white). If this happens:
- **Fallback 1:** Use `method="api"` — triggers TradingView's native screenshot (saved to TV's own location)
- **Fallback 2:** Scroll the chart first with `tv_ui_scroll(direction="down")` then retry CDP capture
- **Fallback 3:** Use `region="full"` to capture the entire viewport instead of just "chart"

### draw_shape Returns Null entity_id
Some `tv_draw_shape` calls return `\"entity_id\": null` — the line still draws but you can't reference it later. This is cosmetic; the shape is visible on chart.

## Output Format

```markdown
## 📊 PEPPERSTONE:{SYMBOL} Key Levels — Alfred MT5 (W1:50% + D1:30% + H4:20%)

**Current Price:** {price}

### 🟢 HIGH CONFIDENCE Levels (≥90/100)

**🟢 SUP {price} — Score: {score}/100** (Dist: {dist})
- W1: {wp}% ({intx}x ±{tol}) | D1: {wp}% ({intx}x ±{tol}) | H4: {wp}% ({intx}x ±{tol})
- Description

### ⚠️ Zone Analysis
- Support zone range, resistance zone range
- Price position relative to zones
```

## Quick Reference Command

```bash
# Full pipeline for any symbol:
python3 alfred_client.py multi SYMBOL --tf W1 --count 300 --output cache/
python3 alfred_client.py multi SYMBOL --tf D1 --count 999 --output cache/
python3 alfred_client.py multi SYMBOL --tf H4 --count 5000 --output cache/
# → convert → analyze → plot → screenshot → deliver
```
