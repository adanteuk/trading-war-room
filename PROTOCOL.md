# Trading War Room — Multi-Agent Protocol (v2: Merlin Orchestrator)

## Architecture

Three Hermes agents collaborate on NAS100 trading decisions. **Merlin orchestrates**, Alfred has hard veto.

| Agent | Machine | Role | Discord Bot |
|-------|---------|------|-------------|
| **Alfred** 🦇 | WSL (your PC) | Risk Manager | `alfred-bot` |
| **Walker** 🤖 | Ubuntu VM | Technical Analyst | `walker-bot` |
| **Merlin** 🧙 | Mac | **Orchestrator** + Researcher | `merlin-bot` |

## Communication Channels

### Discord Server: "Trading War Room"

| Channel | Purpose | Who Posts | Channel ID |
|---------|---------|-----------|------------|
| `#daily-briefing` | Morning analysis summaries | All three | `1505601530575716372` |
| `#research-context` | Merlin's macro/fundamental thesis | Merlin | `1505601583444918423` |
| `#technical-setup` | Walker's chart analysis | Walker | `1505601621839843418` |
| `#risk-check` | Alfred's risk assessment | Alfred | `1505601652470583506` |
| `#debate-thread` | Structured debate (thread per day) | All three | `1505601691666354402` |
| `#final-call` | **Merlin posts final decision** | Merlin only | `1505601720439406732` |
| `#trade-log` | Executed trades with outcomes | Alfred | `1505601751519199382` |
| `#weekly-review` | Saturday retrospective | All three | `1505601783416754298` |
| `#ops` | Agent health, config, alerts | All three | `1505601804178690211` |

### Shared Git Repo: `~/.hermes/trading-war-room/`

```
signals/YYYY-MM-DD/
├── walker_ta.json       ← Technical analysis
├── merlin_research.json ← Research findings
└── alfred_risk.json     ← Risk assessment (with veto flag)

debate/YYYY-MM-DD/
├── transcript.md        ← Full debate log

decisions/YYYY-MM-DD.json ← Merlin's final call

trade-log.json              ← All trades with P/L (Alfred maintains)
merlin_orchestrator.py      ← Orchestrator script (Mac)
alfred_risk_agent.py        ← Risk agent script (WSL)
```

## Daily Schedule (HKT)

| Time | Event | Actor |
|------|-------|-------|
| **18:30** | Walker starts technical analysis | Walker cron |
| **18:30** | Merlin starts research + orchestrator wakes up | Merlin cron |
| **18:30** | Alfred runs MT5 balance check | Alfred cron |
| **18:50** | Alfred posts risk assessment to `#risk-check` + git | Alfred |
| **18:55** | Walker posts TA to `#technical-setup` + git | Walker |
| **18:55** | Merlin posts research to `#research-context` + git | Merlin |
| **19:00** | **Merlin orchestrates debate** — creates thread, pulls all inputs | Merlin |
| **19:00-19:30** | Round 1: Opening arguments (TA + Risk + Research) | All three |
| **19:30-19:40** | Round 2: Rebuttals, Alfred confirms or vetoes | All three |
| **19:40-19:45** | **Merlin makes final call** → posts to `#final-call` | Merlin |
| **Next day 21:30+** | Trade execution window (NY session) | Alfred monitors |
| **Post-session** | Alfred logs trade results to `#trade-log` | Alfred |

## Alfred's HARD VETO Protocol

Alfred is NOT the orchestrator but retains **absolute veto power** on risk grounds:

### Auto-Veto Triggers
| Condition | Action |
|-----------|--------|
| Any account DD > 8% | 🛑 VETO |
| Any account DD > 10% | 🛑 VETO (hard breach) |
| Daily loss exceeds 2% limit | 🛑 VETO |
| 5+ consecutive losses | 🛑 VETO (cooling off) |
| MT5 connection/API error | 🛑 VETO (safety first — can't verify risk) |

### Veto Format
When Alfred vetoes, he posts to both `#risk-check` and the debate thread:
```
🛑 ALFRED VETO — [specific reason]
Account: FTMO
DD: 8.5% (threshold: 8.0%)
Action: ALL trades blocked until DD reduced
```

**Merlin MUST respect the veto.** The final call becomes:
```
🎯 FINAL CALL: NO GO — VETOED BY ALFRED
```

The veto cannot be overridden by Merlin or Walker. Only Alfred can lift it.

## Debate Protocol

### Round 1: Opening Arguments
Each agent posts their position:

**🤖 Walker format:**
```
WALKER — Technical Analysis
Profile: Classic Tuesday Low
ORB Score: 82/100
Bias: BULLISH
Key Levels: PDH=21,500 | PDL=21,320 | ONH=21,480 | ONL=21,350
Reasoning: Price in D1 Discount, London SSL sweep
Confidence: 80/100
```

**🦇 Alfred format:**
```
ALFRED — Risk Check
FTMO: DD 4.2% | Pepperstone: DD 0%
Daily budget: 2%
Lot multiplier: 1.0x
Consecutive losses: 1
Status: GO (no veto)
```

**🧙 Merlin format (Orchestrator):**
```
MERLIN — Research Thesis
Economic Calendar: FOMC minutes tomorrow 2pm ET
Sentiment: VIX 22 | Fear/Greed 45
Cross-market: DXY bullish, bonds yielding up
Events: NVDA earnings Thursday (high impact)
Thesis: Morning setup likely intact but reduce size for afternoon risk
```

### Round 2: Rebuttals
Merlin synthesizes and asks questions:
```
MERLIN — Rebuttal Round
@Walker: Does 2pm FOMC invalidate the morning ORB setup?
@Alfred: With 4.2% DD, are we comfortable with 0.5 lot?

Walker: Setup is NY AM only. FOMC is 2pm. We'd be done before then.
Alfred: 0.5 lot = 0.35% risk. Acceptable.
```

### Round 3: Merlin's Final Decision
```
MERLIN — FINAL CALL
Decision: GO LONG NAS100
Entry: ORB breakout > 21,450
SL: 21,380
TP: 21,590 (1:2 R:R)
Size: 0.5 lot (reduced due to FOMC + DD proximity)
Risk: 0.35% of FTMO equity
Window: 09:30-11:00 ET only
Close all before: 13:30 ET
Alfred veto: No
```

## Data Format Standards

### walker_ta.json
```json
{
  "timestamp": "2026-05-18T18:55:00+08:00",
  "bias": "bullish",
  "confidence": 80,
  "orb_score": 82,
  "ict_profile": "Classic Tuesday Low",
  "key_levels": {"pdh": 21500, "pdl": 21320, "onh": 21480, "onl": 21350},
  "entry": 21450, "sl": 21380, "tp": 21590,
  "reasoning": "D1 Discount, SSL sweep in London"
}
```

### merlin_research.json
```json
{
  "timestamp": "2026-05-18T18:55:00+08:00",
  "economic_calendar": [{"time": "14:00 ET", "event": "FOMC Minutes", "impact": "high"}],
  "sentiment": {"vix": 22, "fear_greed": 45},
  "cross_market": {"dxy": "bullish", "bonds": "yields up"},
  "risks": [{"event": "NVDA earnings", "date": "2026-05-20", "impact": "high"}],
  "summary": "Morning setup intact but reduce size for afternoon event risk"
}
```

### alfred_risk.json
```json
{
  "timestamp": "2026-05-18T18:50:00+08:00",
  "go_no_go": "GO",
  "veto": false,
  "veto_reason": "",
  "accounts": {
    "FTMO": {"balance": 200000, "equity": 191600, "dd_pct": 4.2, "status": "ok"},
    "Pepperstone-HKD": {"balance": 50000, "equity": 50200, "dd_pct": 0, "status": "ok"}
  },
  "recommended_lot_size": 1.0,
  "max_daily_loss_pct": 2.0,
  "consecutive_losses": 1,
  "factors": ["FTMO DD 4.2% within limits", "Pepperstone OK"]
}
```

## Git Workflow

### Rules:
1. **Always pull before writing**: `git pull --rebase`
2. **One commit per agent per day**
3. **Never edit another agent's files**
4. **Push immediately after writing**

### File ownership:
| File | Owner | Who can edit |
|------|-------|-------------|
| `signals/*/walker_ta.json` | Walker | Walker only |
| `signals/*/merlin_research.json` | Merlin | Merlin only |
| `signals/*/alfred_risk.json` | Alfred | Alfred only |
| `debate/*/transcript.md` | Merlin | Merlin only |
| `decisions/*.json` | Merlin | Merlin only |
| `trade-log.json` | Alfred | Alfred only |
| `merlin_orchestrator.py` | Merlin | Merlin only |
| `alfred_risk_agent.py` | Alfred | Alfred only |

## Saturday Weekly Review (08:00 HKT)

Merlin leads the retrospective:

1. **Merlin** pulls all data, calculates week accuracy
2. **Walker** reviews TA signal accuracy (ORB score vs outcomes)
3. **Alfred** reviews risk compliance and account performance
4. **Merlin** synthesizes and posts to `#weekly-review` with:
   - Weekly P/L per account
   - Win rate and accuracy by agent
   - Protocol improvements for next week

## Mac-Specific Requirements for Merlin

Since Merlin runs on a Mac and serves as orchestrator:

1. **Disable sleep during trading hours:**
   ```bash
   # Prevent sleep from 6:00 PM to 12:00 AM HKT
   sudo pmset -c sleep 0  # While on power, never sleep
   sudo pmset -b sleep 30  # On battery, 30 min OK
   ```

2. **Ensure gateway stays running:**
   ```bash
   # Add to crontab: restart gateway if dead
   */5 * * * * pgrep -f "hermes" || hermes gateway start
   ```

3. **Power source:** Keep plugged in during the orchestration window.

## Anti-Loop Safeguards

1. **Each bot ignores other bots' messages** except in `#debate-thread`
2. **In debate thread**, agents only respond to @mentions from Merlin
3. **Merlin controls the debate flow** — only Merlin triggers Round 2 and final call
4. **Max 3 rounds per day** — enforced by Merlin's orchestrator
5. **Cooldown:** No agent posts twice within 5 minutes in any channel
6. **Veto is instant:** If Alfred posts a veto, debate ends immediately

## Emergency Stop

If any agent detects anomalous behavior:
- Post `🚨 EMERGENCY STOP — [reason]` to `#ops`
- All agents halt trading activities
- Alfred notifies AC via Telegram DM
- Manual review required before resuming

## Cron Job Setup

### Alfred (WSL) — 18:30 HKT
```
30 18 * * 1-5 python3 ~/.hermes/trading-war-room/alfred_risk_agent.py
```

### Walker (Ubuntu VM) — 18:30 HKT
```
30 18 * * 1-5 [Walker's TA analysis script that writes to signals/ + Discord]
```

### Merlin (Mac) — 19:00 HKT
```
0 19 * * 1-5 python3 ~/.hermes/trading-war-room/merlin_orchestrator.py
```
