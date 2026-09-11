# Five-Stage Pipeline v3 — Implementation Plan

**Version:** 1.0 (2026-09-14) · **Owner:** Merlin (Mac) · **Approved decisions:** see v3 doc §7b
**Companion chart:** `references/warroom-v3-pipeline.png` (source: `warroom-v3-pipeline.mmd`)
**Companion doc:** `references/five-stage-pipeline-v3.md`

---

## Guiding constraints (from AC + operating history)

1. AC decisions are FINAL: 1% Carson cap · 60% FB veto · ORB breakdown contract ·
   Walker 18:30 · Carson hardening approved.
2. LLMs propose, scripts dispose — every veto threshold lives in Python, never a prompt.
3. Mac holds zero trade credentials, forever.
4. No real-money order until: Carson hardened + paper-trade validation passed.
5. Every change must degrade safely: missing data → NO_GO, never a silent pass.

---

## Phase 0 — Current state (DONE)

| Item | Status |
|---|---|
| v3 architecture doc (`five-stage-pipeline-v3.md`) | ✅ v3.2 |
| Agent inventories (Walker, Alfred, Carson) collected & analyzed | ✅ §8 |
| `quant_gate.py` built + veto paths tested | ✅ commit 816bed2 |
| `compliance_gate.py` built + veto paths tested + live Carson ping OK | ✅ commit 816bed2 |
| Mermaid workflow chart | ✅ this delivery |

---

## Phase 1 — Orchestrator integration (Mac, Merlin) · ~1 session

**Goal:** gates run inside the existing 19:00 pipeline; vetoes force NO_GO.

1. Edit `merlin_orchestrator.py`:
   - After `git pull --rebase` and signal load, run in order:
     `quant_gate.py --date {TODAY}` then
     `compliance_gate.py --date {TODAY} --symbol {SYMBOL} --calendar {calendar.json}`
     via `subprocess` with the **venv python** (`hermes-agent/venv/bin/python3` — zmq ABI).
   - Read both exit codes + JSON outputs. Any VETO → decision = NO_GO with
     `veto_source: "quant_gate"|"compliance_gate"`, veto reasons copied into
     `decisions/{date}.json`.
   - **Alfred-missing rule (v2.4 compat):** quant gate currently vetoes on missing
     `alfred_risk.json` — for the transition period this is CORRECT (conservative),
     but add `--allow-missing-alfred` flag so we can soften it consciously, not silently.
2. Lot-size function (script, replaces Alfred prompt calc):
   `lot = (equity × 0.005) / (SL_points × point_value)`; cap output at
   Carson max 2.0 lots; refuse to emit payload if SL missing.
3. Decision matrix unchanged: GO ≥75 (full) / CONDITIONAL_GO 60-74 (0.5×) / NO_GO.
4. Emit `decision_id = {date}-{SYMBOL}-{seq}` and write `decisions/{date}.json` with
   full gate results (this is Carson's later verification source).
5. Add Discord `#executions` posting for decisions carrying payloads (paper mode:
   "would execute" message instead of order).
6. **Test:** run full pipeline on next trading day; verify decision file contains
   gate results; verify a forced veto (e.g., fake calendar event) produces NO_GO.

**Exit criteria:** one clean full-pipeline run logged end-to-end.

## Phase 2 — Signal contract updates (agents) · parallel, ~1 week

1. **Walker cron 18:30 (AC decision #4):** message Walker to move his cron and add:
   - `orb_breakdown` (6 categories, exact ints, sum = orb_score)
   - `ml_regime`, `regime_confidence`, `regime_probs` (mandatory)
   - `conditional_triggers` (machine-readable, exact floats — schema in v3 doc §8.1)
   - keep entry/SL/TP as concrete numbers (already doing)
2. **Alfred:** no prompt change needed for sizing (script owns it now); ask him to
   add `sample_size`, `fb_event_week_rate` (or keep existing field names — map in
   quant gate), and `range_atr_ratio` if he computes it; confirm his proposed vetoes
   VIX>35 + FB>60% are covered by quant gate (FB done; VIX check add to quant gate).
3. **Contract test script** (`validate_signals.py`, Mac): schema-checks all three
   signal JSONs each run; failures logged as gate warnings. Prevents another
   `orb_score: null` class of bug.

**Exit criteria:** 5 consecutive trading days of contract-valid signals from all agents.

## Phase 3 — Economic calendar feed (Mac) · ~2 sessions

1. Choose source: portal's investing.com scrape (proven) → normalized JSON
   `{time_utc, currency, impact, name}` cached at
   `~/.hermes/trading-war-room/calendar/{date}.json`.
2. Cron/refresh: pull day's calendar at 06:30 HKT + refresh 17:30 HKT.
3. Compliance gate consumes via `--calendar` (already implemented).
4. Fallback ladder: investing.com → ForexFactory (rate-limited, Alfred noted CF
   challenges) → manual JSON by Merlin at 19:00 (logged as warning).

**Exit criteria:** 7 consecutive days with calendar auto-loaded before 19:00.

## Phase 4 — Carson hardening + order action (Windows, Carson) · ~2-3 sessions

**Order matters: security BEFORE execution code.**

1. **Auto-start:** convert `MT5_server.py` manual start → Windows Task Scheduler
   at logon + the existing 12h watchdog gains "start if no listener" logic.
2. **Network security (AC decision #5 prerequisite):**
   - Bind `tcp://192.168.11.173:5555` (specific interface, not 0.0.0.0) or keep
     0.0.0.0 + Windows Firewall rule restricting 5555 to Mac's IP(s).
   - Add API-key layer: `order`-class actions require `{"auth": <key>}` matching
     key stored in `C:\Users\hkvid\zmq\.order_key` (never in repo).
   - Read actions (ping/get_rates/etc.) unchanged — no key needed.
3. **`order` action** (new, in `MT5_server.py`):
   - Input: execution payload JSON (v3 doc §Stage-7 contract).
   - Server-side checks IN ORDER (all must pass): auth key → source IP whitelist →
     `git pull` in `C:\Users\hkvid\trading-war-room` → decision_id exists in
     `decisions/{date}.json` AND status GO AND payload fields match → SL present →
     risk ≤1% equity → lot ≤2.0 → symbol ∈ verified list → `valid_until` not expired →
     MT5 connected. Any failure → reject + log + notify.
   - Order type: LIMIT/STOP only (no market — Carson's rule), hedging account OK.
   - Respond with `{ticket, requested_price, fill_price, slippage, timestamps}`.
4. **`execution_log.json`** append per fill + git push from Windows; also
   `rejected_orders.log` for denials.
5. **Symbol verification:** verify BTCUSD, HK50, JPN225, GER40 via `symbol_info_tick`
   test; update verified list (Carson §13).
6. **Time sync:** enable Windows time service w/ NTP pool; note drift in health ping.

**Exit criteria:** order action passes a simulated full flow against MT5 **demo**
account; every reject rule demonstrated firing at least once.

## Phase 5 — Paper-trading validation (all) · 2-4 weeks

1. Orchestrator emits payloads; Carson logs "would-execute" (no live order) OR
   routes to MT5 **demo** account — AC to pick one (default: demo).
2. Daily: `execution_log.json` reviewed; slippage vs Alfred's backtest assumptions.
3. Weekly (Sat review cron): measure — gate veto quality (did vetoes avoid losers?),
   ORB breakdown consistency, Alfred FTMO login failure rate, timing slippage
   (18:30/18:45/19:00 chain).
4. Success criteria for go-live (all must hold across the window):
   - 0 execution failures caused by contract/payload bugs
   - Gate veto precision ≥ 60% (vetoed trades would have lost or broken even)
   - Signal chain on-time rate ≥ 95%
   - Carson server uptime ≥ 95% (current level) with auto-restart proven
5. AC sign-off → flip `paper_mode: false` in orchestrator config.

## Phase 6 — Live + feedback loop · ongoing

1. Live routing with 1% Carson cap active; start at 0.5× intended size for first
   2 weeks (extra conservatism during cutover).
2. Weekly review updates: SOP lookups (Alfred), gate threshold tuning proposals
   (Merlin → AC approval), ORB threshold recalibration if breakdown data shows drift.
3. Quarterly: re-run agent inventory prompts (Appendix A) to catch stack drift —
   Walker's skills already diverged once.

---

## Dependency graph & schedule

```
Phase 1 (orchestrator) ──┐
Phase 2 (contracts)  ────┼──► Phase 3 (calendar) ──► Phase 4 (Carson) ──► Phase 5 (paper) ──► Phase 6 (live)
```
- P1+P2 can run in parallel; P3 needs only Merlin; P4 is the long pole (Windows side,
  AC/Carson hands-on) and must complete before P5 ends; P5 gates P6.
- Earliest realistic live date: ~4-6 weeks from 2026-09-14.

## Risk register

| Risk | Mitigation |
|---|---|
| Alfred FTMO login failures (observed 2026-09-10) | Health-check + retry in his run; pipeline treats NO_GO as safe default |
| Git push credential failures (cron context) | Non-fatal by design; decisions still local + Discord; SSH remote switch backlog |
| Walker signal timing slip | 18:30 move + orchestrator wait window; quant gate warns on stale timestamps |
| ORB score drift breaks backtested thresholds | Breakdown contract + weekly consistency check |
| REQ-REP deadlock on Carson | Watchdog auto-restart; client `or default` null defense |
| Time drift across agents | NTP on all 3 machines; timestamps in every JSON |
| Silent calendar gap | Warning (not silent) when calendar missing; manual fallback path |

---

*Next action: AC approves plan → Merlin executes Phase 1 on next trading day.*
