# Trading War Room 🎯

Multi-agent trading collaboration between Alfred (Risk Manager), Walker (Technical Analyst), and Merlin (Researcher).

## Setup

```bash
# Clone this repo on ALL THREE machines:
git clone https://github.com/YOU/trading-war-room.git ~/.hermes/trading-war-room/

# Verify setup:
ls ~/.hermes/trading-war-room/
# Should see: PROTOCOL.md, orchestrator.py, .gitignore, signals/, debate/, decisions/
```

## Roles

| Agent | Machine | Role |
|-------|---------|------|
| 🦇 Alfred | WSL | Risk Manager + Orchestrator |
| 🤖 Walker | Ubuntu VM | Technical Analyst |
| 🧙 Merlin | Mac | Researcher |

## How It Works

1. **6:30 PM HKT** — Walker and Merlin run analysis independently
2. **6:55 PM HKT** — Both post results to Discord + commit to this repo
3. **7:00 PM HKT** — Alfred's orchestrator pulls, checks accounts, and coordinates debate
4. **7:00-7:45 PM HKT** — 3-round debate via Discord
5. **7:45 PM HKT** — Alfred posts final go/no-go decision
6. **Next day** — Trades execute during NY session, results logged

## Protocol

See [PROTOCOL.md](./PROTOCOL.md) for full debate format, data standards, and Discord channel structure.

## Daily Files

```
signals/YYYY-MM-DD/     ← Each agent's analysis
debate/YYYY-MM-DD/      ← Debate transcripts
decisions/YYYY-MM-DD.json ← Final decisions
trade-log.json          ← All trades
```

## Saturday Review

Every Saturday 08:00 HKT — all three agents review the week's performance and refine the protocol.
