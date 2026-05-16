# Trading War Room — Multi-Agent Protocol

## Architecture

Three Hermes agents collaborate on NAS100 trading decisions:

| Agent | Machine | Role | Bot Name |
|-------|---------|------|----------|
| **Alfred** 🦇 | WSL (your PC) | Risk Manager + Orchestrator | `alfred-bot` |
| **Walker** 🤖 | Ubuntu VM | Technical Analyst | `walker-bot` |
| **Merlin** 🧙 | Mac | Researcher | `merlin-bot` |

## Communication Channels

### Discord Server: "Trading War Room"

| Channel | Purpose | Who Posts |
|---------|---------|-----------|
| `#daily-briefing` | Morning analysis summaries | Walker + Merlin |
| `#debate-thread` | Structured debate (thread per day) | All three |
| `#risk-dashboard` | Real-time risk metrics | Alfred |
| `#final-call` | Go/no-go decisions | Alfred only |
| `#trade-log` | Executed trades with outcomes | Alfred |
| `#weekly-review` | Saturday retrospective | All three |
| `#ops` | Agent health, config, alerts | All three |

### Shared Git Repo: `~/.hermes/trading-war-room/`

```
signals/YYYY-MM-DD/
├── walker_ta.json       ← Technical analysis
├── merlin_research.json ← Research findings
└── alfred_risk.json     ← Risk assessment

debate/YYYY-MM-DD/
├── round1.md            ← Opening arguments
├── round2.md            ← Rebuttals
└── transcript.md        ← Full debate log

decisions/YYYY-MM-DD.json ← Final go/no-go + trade params
trade-log.json              ← All trades with P/L
```

## Daily Schedule (HKT)

| Time | Event | Actor |
|------|-------|-------|
| **18:30** | Walker starts technical analysis | Walker cron |
| **18:30** | Merlin starts research | Merlin cron |
| **18:55** | Walker posts analysis to Discord + git | Walker cron |
| **18:55** | Merlin posts research to Discord + git | Merlin cron |
| **19:00** | Alfred orchestrator starts | Alfred cron |
| **19:00** | Alfred checks MT5 accounts | Alfred |
| **19:00-19:30** | Alfred waits for inputs (30 min timeout) | Alfred |
| **19:30** | Debate Round 1: Opening arguments | All three |
| **19:35** | Debate Round 2: Rebuttals | All three |
| **19:40** | Alfred makes final call | Alfred |
| **19:45** | Decision posted to `#final-call` | Alfred |
| **20:00+** | Trade execution window begins | Alfred monitors |

## Debate Protocol

### Round 1: Opening Arguments
Each agent posts their position with evidence:

**Walker format:**
```
🤖 WALKER — Technical Analysis
Profile: Classic Tuesday Low
ORB Score: 82/100
Bias: 🟢 BULLISH
Key Levels: PDH=21,500 | PDL=21,320 | ONH=21,480 | ONL=21,350
Reasoning: Price in D1 Discount, London session forming SSL sweep
Confidence: 80/100
```

**Merlin format:**
```
🧙 MERLIN — Research
Economic Calendar: FOMC minutes tomorrow 2pm ET
Sentiment: VIX 22 (elevated) | Fear/Greed 45 (neutral)
Cross-market: DXY bullish, bonds yielding up
Risks: 🟡 NVDA earnings Thursday
Summary: Caution warranted due to event risk
Confidence in risk assessment: 70/100
```

### Round 2: Rebuttals
Alfred reads both and asks clarifying questions:

**Alfred format:**
```
🦇 ALFRED — Risk Check
Accounts: FTMO DD 4.2% | Pepperstone OK
Budget: 2% daily max remaining

Question to Walker: Does 2pm FOMC invalidate your morning setup?
Question to Merlin: Is the VIX level high enough to skip entirely?
```

### Round 3: Final Decision
Alfred synthesizes and decides:

**Alfred format:**
```
🎯 ALFRED — FINAL CALL
Decision: ✅ GO LONG
Instrument: NAS100
Entry: ORB breakout > 21,450
SL: 21,380 (widened per Merlin's risk input)
TP: 21,590 (1:2 R:R)
Size: 0.5 lot (reduced from 1.0 due to FOMC)
Risk: 0.35% of FTMO equity
Window: 09:30-11:00 ET only
Close all before: 13:30 ET
```

## Data Format Standards

### walker_ta.json
```json
{
  "timestamp": "2026-05-18T18:55:00+08:00",
  "date": "2026-05-18",
  "bias": "bullish",
  "confidence": 80,
  "orb_score": 82,
  "ict_profile": "Classic Tuesday Low",
  "key_levels": {
    "pdh": 21500,
    "pdl": 21320,
    "onh": 21480,
    "onl": 21350,
    "weekly_open": 21400
  },
  "entry": 21450,
  "sl": 21380,
  "tp": 21590,
  "reasoning": "D1 Discount, SSL sweep in London"
}
```

### merlin_research.json
```json
{
  "timestamp": "2026-05-18T18:55:00+08:00",
  "date": "2026-05-18",
  "economic_calendar": [
    {"time": "14:00 ET", "event": "FOMC Minutes", "impact": "high"}
  ],
  "sentiment": {
    "vix": 22,
    "fear_greed": 45
  },
  "cross_market": {
    "dxy": "bullish",
    "bonds": "yields up"
  },
  "risks": [
    {"event": "NVDA earnings", "date": "2026-05-20", "impact": "high"}
  ],
  "summary": "Caution warranted"
}
```

### alfred_risk.json
```json
{
  "timestamp": "2026-05-18T19:30:00+08:00",
  "date": "2026-05-18",
  "accounts": {
    "FTMO": {"balance": 200000, "equity": 191600, "dd_pct": 4.2},
    "Pepperstone-HKD": {"balance": 50000, "equity": 50200, "dd_pct": 0}
  },
  "go_no_go": "GO",
  "max_daily_loss_pct": 2.0,
  "lot_size": 0.5,
  "factors": ["FTMO DD within limits", "FOMC risk reduces size"]
}
```

## Git Workflow

### Rules:
1. **Always pull before writing**: `git pull --rebase`
2. **One commit per agent per day**: `git commit -m "[Walker] TA for 2026-05-18"`
3. **Never edit another agent's files**
4. **Push immediately after writing**
5. **Resolve conflicts with `git checkout --theirs` for your own files**

### Alfred's orchestrator handles sync automatically:
```bash
# Pre-analysis:
git pull --rebase

# Post-decision:
git add . && git commit -m "Alfred: Decision for YYYY-MM-DD" && git push
```

## Saturday Weekly Review (08:00 HKT)

All three agents participate in a coordinated review:

1. **Alfred** pulls trade-log.json and calculates:
   - Weekly P/L per account
   - Win rate
   - Max drawdown
   - Risk compliance (any rule violations?)

2. **Walker** reviews:
   - Which TA signals were correct/incorrect
   - ORB score accuracy vs actual outcomes
   - ICT profile classification accuracy

3. **Merlin** reviews:
   - Which risk factors were predictive
   - Missed events that impacted trades
   - Sentiment indicator accuracy

4. **Alfred** synthesizes and posts to `#weekly-review`

## Setup Checklist

### For Alfred (WSL):
- [ ] Discord bot token in config.yaml
- [ ] Clone shared repo to ~/.hermes/trading-war-room/
- [ ] Git SSH key configured
- [ ] MT5 balance check script verified
- [ ] Orchestrator cron job: `30 19 * * 1-5`

### For Walker (Ubuntu):
- [ ] Discord bot token in config.yaml
- [ ] Clone shared repo
- [ ] Git SSH key configured
- [ ] TA analysis cron job: `30 18 * * 1-5`
- [ ] Skills loaded: ict-weekly-profile, orb-bias-filter

### For Merlin (Mac):
- [ ] Discord bot token in config.yaml
- [ ] Clone shared repo
- [ ] Git SSH key configured
- [ ] Research cron job: `30 18 * * 1-5`
- [ ] Web search tools enabled

## Anti-Loop Safeguards

To prevent infinite reply chains in Discord:

1. **Each bot ignores other bots' messages** except in `#debate-thread`
2. **In debate thread**, agents only respond to @mentions from Alfred
3. **Alfred controls the debate flow** — only he can trigger Round 2 and Round 3
4. **Max 3 rounds per day** — enforced by Alfred's orchestrator
5. **Cooldown period** — no agent can post twice within 5 minutes in any channel

## Emergency Stop

If any agent detects anomalous behavior:
- Post `🚨 EMERGENCY STOP — [reason]` to `#ops`
- All agents halt trading activities
- Alfred notifies AC via Telegram DM
- Manual review required before resuming
