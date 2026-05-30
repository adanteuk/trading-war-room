#!/usr/bin/env python3
"""NAS100 Multi-TF Key Level Analysis - Ian's Key Level v1.6.0"""
import json
import os
from datetime import datetime

CACHE_DIR = "/Users/ychen/.hermes/data/key-level-cache"
DATA_DIR = f"{CACHE_DIR}/data/NAS100"
RESULTS_DIR = f"{CACHE_DIR}/results"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

CURRENT_PRICE = 29912.9

# ============================================================
# 1. Load and normalize all TF data
# ============================================================

def load_w1():
    """Load W1 from existing cache (structured format)"""
    with open(f"{DATA_DIR}/W1.json") as f:
        raw = json.load(f)
    bars = []
    for b in raw["data"]:
        t = b["time"]
        # Parse string timestamp to unix
        if isinstance(t, str):
            dt = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
            ts = int(dt.timestamp())
        else:
            ts = t
        bars.append({
            "time": ts,
            "open": float(b["open"]),
            "high": float(b["high"]),
            "low": float(b["low"]),
            "close": float(b["close"]),
            "volume": float(b.get("tick_volume", b.get("volume", 0)))
        })
    return bars

def load_d1_from_tv():
    """Load D1 data that we fetched via MCP"""
    # We need to save it first
    pass

def load_h4_from_tv():
    """Load H4 data that we fetched via MCP"""
    pass

def normalize_tv_bars(bars):
    """Ensure bars have consistent float types"""
    return [{
        "time": int(b["time"]),
        "open": float(b["open"]),
        "high": float(b["high"]),
        "low": float(b["low"]),
        "close": float(b["close"]),
        "volume": float(b.get("volume", 0))
    } for b in bars]

# Load W1
w1_bars = load_w1()
print(f"W1 bars loaded: {len(w1_bars)}")

# Save fresh W1
with open(f"{DATA_DIR}/W1.json", "w") as f:
    json.dump({"meta": {"source": "cached", "timeframe": "W1"}, "bars": w1_bars}, f)

# ============================================================
# 2. Save D1 and H4 from MCP results
# ============================================================

# D1 bars from the MCP response
d1_bars_raw = [
    {"time": 1743112800, "open": 19800.3, "high": 19819.1, "low": 19180.8, "close": 19182.4, "volume": 354172},
    {"time": 1743372000, "open": 19137.3, "high": 19305.9, "low": 18793.9, "close": 19226.4, "volume": 431734},
    {"time": 1743458400, "open": 19225.2, "high": 19461.9, "low": 19080.4, "close": 19416.2, "volume": 409444},
]
# ... (truncated - we have 300 D1 bars from MCP)

# Since we can't embed all 300 bars here, let's write a script that 
# takes the MCP output as input. Actually, let me just use the data 
# directly from the MCP calls above.

# I'll write the data to files first, then run analysis
print("Data will be saved by the main script")
