# Trading War Room 🎯

Multi-agent trading collaboration. **Merlin orchestrates**, Walker analyzes, Alfred manages risk with veto power.

## Architecture

```
Merlin 🧙 (Mac)          Walker 🤖 (Ubuntu VM)       Alfred 🦇 (WSL)
Orchestrator              Technical Analyst            Risk Manager
+ Researcher              Chart analysis               MT5 account monitoring
                          ICT + ORB                    HARD VETO power
```

## Setup

```bash
# Clone this repo on ALL THREE machines:
git clone https://github.com/YOU/trading-war-room.git ~/.hermes/trading-war-room/
```

## How It Works (Daily Flow)

```
18:30 HKT  ── Walker starts TA | Merlin starts research | Alfred checks MT5
18:50 HKT  ── Alfred posts risk assessment to Discord + git
18:55 HKT  ── Walker posts TA to Discord + git
18:55 HKT  ── Merlin posts research to Discord + git
19:00 HKT  ── Merlin orchestrates debate (creates thread, pulls all inputs)
19:00-19:30 ── Round 1: Opening arguments
19:30-19:40 ── Round 2: Rebuttals, Alfred confirms or VETOs
19:40-19:45 ── Merlin makes final GO/NO-GO call → #final-call
Next day   ── Trade executes during NY session (Alfred monitors)
```

## Key Rule: Alfred's Hard Veto

Even though Merlin orchestrates, **Alfred has absolute veto power** on risk grounds:
- DD > 8% on any account → 🛑 VETO
- Daily loss > 2% → 🛑 VETO
- 5+ consecutive losses → 🛑 VETO
- MT5 connection error → 🛑 VETO

Merlin cannot override a veto. This is by design.

## Protocol

See [PROTOCOL.md](./PROTOCOL.md) for full debate format, data standards, and Discord channel structure.

## Files

```
signals/YYYY-MM-DD/     ← Each agent's analysis (daily)
debate/YYYY-MM-DD/      ← Debate transcripts
decisions/YYYY-MM-DD.json ← Merlin's final decisions
trade-log.json          ← All trades (Alfred maintains)
merlin_orchestrator.py  ← Orchestrator script (runs on Mac)
alfred_risk_agent.py    ← Risk agent script (runs on WSL)
```

## Saturday Review

Every Saturday 08:00 HKT — Merlin leads the weekly retrospective.
