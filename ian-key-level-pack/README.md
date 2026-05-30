# Ian's Key Levels — Complete Pack (v1.9.0)

## 📁 Package Contents

### Core Skills (4)
```
skills/
├── ian-key-level/              # Core methodology — Wick Precision scoring, caching, multi-TF analysis
│   ├── SKILL.md                # Full methodology documentation
│   ├── README.md
│   ├── scripts/analyze_key_levels.py   # Standalone analysis script
│   ├── analyze_nas100.py               # NAS100-specific analysis
│   └── audusd_analysis.py              # AUDUSD-specific analysis
├── mt5-key-levels-pipeline/    # MT5 data → Key Level pipeline
│   ├── SKILL.md
│   └── scripts/mt5_key_levels_pipeline.py
├── tradingview-key-levels-pine/ # Pine Script indicators for TradingView
│   ├── SKILL.md
│   └── references/
│       ├── walker_key_levels_v4.pine   # TradingView overlay indicator
│       └── walker_key_levels_v4.txt
└── key-level-analysis/         # Key Level analysis framework
    ├── SKILL.md
    └── scripts/key_level_analysis.py
```

### Cache System
```
cache/
├── cache_manager.py            # Persistent TTL cache (W1/D1/H4)
├── analyze.py                  # General analysis helper
├── hk50_analysis.py            # HK50 analysis example
├── hk50_mt5_analysis.py        # HK50 MT5 pipeline example
├── gbpusd_mt5_analysis.py      # GBPUSD MT5 analysis example
└── twn_analysis.py             # TWN (Taiwan) analysis example
```

## 🔑 Methodology Summary

- **Wick Precision Scoring:** 0-100 scale based on wick rejections at key levels
- **Multi-TF Weighting:** W1=50%, D1=30%, H4=20%
- **Tolerance Scaling:** Instrument-specific (indices ±5-50, BTC ±100-1000, forex ±5-50 pips)
- **Zone Clustering:** Fixed-dollar range clustering (NOT percentage-based)
- **Score Threshold:** ≥90 = HIGH CONFIDENCE (only levels ≥90 are reported)
- **Cache System:** TTL-based persistent cache (W1=7d, D1=24h, H4=6h)

## ⚙️ Data Sources (Priority Order)
1. **Alfred MT5 Bridge** — ZeroMQ TCP (192.168.11.211:5555), deepest historical data
2. **TradingView MCP** — CDP bridge to TradingView Desktop (~300 bars limit)
3. **TradingView Browser** — JavaScript extraction (~300 bars limit)
4. **Yahoo Finance** — Forex pairs only (indices CFD ≠ index prices)

## 📊 Validated Instruments
- HK50, GER40, NAS100, JPN225, XAUUSD, GBPUSD, AUDJPY, US Stocks

---

*Packed by Walker — 2026-05-30*
*Based on 999+ D1 bars, 5000+ H4 bars, 300+ W1 bars per instrument*
