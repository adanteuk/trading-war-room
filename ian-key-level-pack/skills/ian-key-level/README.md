# Ian's Key Level Skill

**ICT/CRT Key Level Methodology for JPN225**

---

## 🚀 Quick Start

### **Record a Confirmed Level**
```
"Please record 52663.2 as JPN225 key level"
```

### **Validate a Proposed Level**
```
"Is 52364.2 a valid key level for JPN225?"
```

### **Analyze All Confirmed Levels**
```
"Run key level analysis on JPN225"
```

---

## 📊 Analysis Results Summary

Based on 999 daily bars of JPN225 data (2022-2026):

| Metric | Finding | Recommendation |
|--------|---------|----------------|
| **Decimal Precision** | 100% wick precision at 1 decimal | ✅ Maintain 1 decimal place |
| **Optimal Tolerance** | ±5 points | ✅ Use tight tolerance |
| **Zone Threshold** | < 50 points spread | ✅ Cluster levels into zones |
| **Min Tests** | 2+ interactions | ✅ Require multiple tests |
| **Wick Precision** | > 70% for confirmation | ✅ Wick-based validation |

---

## 🎯 Current Confirmed Levels

| Level | Date | Type | Status |
|-------|------|------|--------|
| **52663.2** | 2026-03-27 | Resistance | ✅ Active |
| 52644.1 | 2026-03-24 | Resistance | 📝 Historical |

**Zone:** 52644.1 - 52663.2 (19.1 point thickness)

---

## 🔧 Files

- `SKILL.md` - Full methodology and usage guide
- `README.md` - This quick reference
- `../../data/market-data/analyze_key_levels.py` - Analysis script
- `../../data/market-data/key_level_analysis.md` - Latest analysis output

---

## 📈 Methodology Validation

**Data Source:** MT5 export (999 D1 bars, 2022-05-16 to 2026-03-27)

**Key Findings:**

1. **Wick Precision Score: 100%**
   - All 5 interactions at 52663.2 were wick-based
   - All 5 interactions at 52644.1 were wick-based
   - Confirms ICT principle: "Wicks show true rejection"

2. **Tight Clustering (19.1 points)**
   - Two levels form a single resistance zone
   - Institutions defend zones, not single prices
   - Trading implication: Enter on zone touch, not exact level

3. **Optimal Tolerance: ±5 points**
   - Price respects levels with high accuracy
   - Wider tolerance dilutes level significance
   - Use ±5 for entry triggers, ±10 for stop placement

---

## 💡 Trading Implications

### **For Resistance Zone (52644 - 52663)**

```
Entry: 52644 - 52663 zone
Stop Loss: 52670+ (zone + 7pt buffer)
Target: Next support level below
Risk/Reward: 1:2 minimum

Confirmation Signals:
- Bearish engulfing on H4/D1
- Long upper wicks (rejection)
- Decreasing volume on tests
```

### **Level Refinement**

When a level is adjusted (e.g., 52644.1 → 52663.2):
- **Reason:** Newer wick data carries more weight
- **Action:** Update active level, keep historical for context
- **Validation:** Re-run analysis with new level

---

## 🔄 Update Workflow

1. **User confirms new level** → Record in MEMORY.md
2. **Run analysis** → `python3 analyze_key_levels.py`
3. **Review metrics** → Wick precision, tolerance, zone clustering
4. **Update skill parameters** → If analysis suggests changes
5. **Document findings** → Update key_level_analysis.md

---

## 📞 Support

**Creator:** Walker (ICT/CRT Specialist)
**Based on:** Ian's confirmed key levels
**Validated:** 2026-03-27

For questions or updates, mention in the Walker group chat.
