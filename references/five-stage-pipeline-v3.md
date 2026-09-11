# Five-Stage Pipeline v3 — Cross-System Multi-Agent Trading Model

**Status:** Draft v3.0 (2026-09-11) — pending agent inventory responses
**Supersedes:** War Room v2.4 two-phase workflow (still operating; v3 extends, not replaces)
**Source:** AC's five-stage agent pipeline article + full skill audit of all agents

---

## 1. Design Principles (from article + our operating history)

1. **Separation of duties** — hypothesis generation, verification, risk, compliance, and execution are never the same agent.
2. **LLMs propose, scripts dispose** — agents (LLMs) write analysis and JSON theses; deterministic Python gates (`quant_gate.py`, `compliance_gate.py`) and Carson-side hard checks have veto power that cannot be argued with.
3. **Mac has zero trade authority** — Mac agents hold market-data + analysis tokens only. All credentials that can move money live on Windows (Carson). Even total hallucination on Mac cannot place an order.
4. **Every execution is traceable** — each order payload carries a `decision_id` pointing to a committed `decisions/{date}.json`. Carson refuses orders without a valid GO decision.
5. **Known pitfalls are encoded, not remembered** — the v2.4 lessons (Alfred WAIT ≠ block, ORB null crash, Discord 2000-char limit, MT5-offline mandatory veto) are baked into gate code.

---

## 2. Role Mapping: Article → Our Agents

| Article stage | Our implementation | Machine | LLM or script | Status |
|---|---|---|---|---|
| 1. @researcher | **Merlin** (macro + thesis) | Mac | LLM | ✅ Exists (cron 19:00 + webhook mode) |
| 2. @quant | **Alfred (stats half) + `quant_gate.py`** | Windows (data) / Mac (gate) | Script reads Alfred's JSON | 🔶 Half-exists as Alfred's statistical validation; needs deterministic gate |
| 3. @risk | **Alfred** (account risk + veto) | Windows | LLM + scripted lot calc | ✅ Exists (v2 veto rules); lot sizing moves to script |
| 4. @compliance | **`compliance_gate.py`** (event filter, kill zones, rate limits) | Mac | Script (NOT an agent) | ❌ New — currently scattered in Merlin's prompt |
| 5. @execution | **Carson** (ZMQ server + MT5 terminal) | Windows | Script only | 🔌 Bridge v2.4 exists for data; `order` action NOT yet implemented |

**Walker** sits alongside as the technical-entry specialist feeding Stage 1-2 (his 0-40 pt scoring and screenshot remain part of the decision matrix).

### Why compliance and quant are scripts, not agents
The article models compliance as a fifth LLM agent. Our operating history says otherwise:
- News blackouts (FOMC/NFP/CPI ±30 min), kill-zone windows, daily loss caps, and API rate limits are **rules, not judgments**.
- Three LLM agents agreeing does not override a hard rule. A script cannot be talked into a trade.
- Precedent: the 3-layer monitor already runs Layer 1/Layer 2 as `no_agent` scripts — this model generalizes that pattern.

---

## 3. Agent Capability Inventory (from skill audit)

### 🧙 Merlin — Mac — Research + Orchestration (Stages 1, 4, 6)
- **Skills:** `trading-war-room-orchestration` (v2.4), `ict-crt-pipeline` (v3.0), `nas100-daily-bias-analysis`, `dealing-range-analysis`, `smt-divergence-analysis`, `ict-weekly-profile`, `unicorn-entry-model`, `qnt-gex-analysis`, `inversion-fvg-analysis`, `merlin-portal` (FastAPI dashboard port 8501), `alfred-mt5-data` (client)
- **Infrastructure:** cron `e3421cd4fc71` (Mon–Fri 19:00 HKT), webhook gateway (tv-monday-range), 3-layer monitor scripts (`~/.hermes/scripts/3-layer-monitor/`), git repo `adanteuk/trading-war-room`
- **Data access:** Carson ZMQ (192.168.11.173 / .211:5555, v2.4 pagination), TradingView MCP (CDP port 9222), Barchart/Yahoo fallbacks (−10–15 pts confidence)
- **Proposed v3 additions:** run `quant_gate.py` + `compliance_gate.py` before decision matrix; emit execution payload JSON; never hold broker trade tokens

### 🐺 Walker — TA + Screenshot (feeds Stages 1–2)
- **Skills:** `war-room-agent-prompts` (Walker Mode A/B), `key-level-analysis`, `orb-bias-filter`, `double-top-bottom-detection`, `winnie-chart-annotation`, `tv-draw-key-levels`, `tradingview-mcp`
- **Output:** `signals/{date}/walker_ta.json` (bias, confidence, orb_score, entry/SL/TP TBD fields, three_layer_analysis) + annotated screenshot
- **VETO:** ORB < 40 → automatic SKIP
- **v3 additions:** entry/SL/TP fields become mandatory concrete numbers (they feed lot calc); null numerics must be omitted, never `null` (orchestrator `or default` defense stays)

### 🦇 Alfred — Windows — Statistical Validation + Risk (Stages 2–3)
- **Skills:** `war-room-agent-prompts` (Alfred Mode A/B), `alfred-mt5-data`, `day-of-week-range-analysis`, `strategy-backtest-verify`, `double-top-bottom-detection` (statistical view)
- **Data:** own MT5 instance via Carson server; SOP v2.0 backtest lookups; false-breakout rates by asset/event-week/session
- **Output:** `signals/{date}/alfred_risk.json` (go_no_go, veto, accounts, factors, lot multiplier inputs)
- **VETO (hard):** false-breakout >85%, range >200% ATR, sample <5, event-week false-breakout >90%, DD ≥5%, daily DD ≥2%, 3+ consecutive losses, positions ≥3, news <15 min, MT5 disconnected
- **v3 changes:** WAIT = 0.5× size (not block — v1 lesson); lot size computed by script, not by Alfred's LLM; Alfred outputs veto flags + risk parameters only

### ⚙️ Carson — Windows — Execution Hub (Stage 5)
- **Current:** `alfred_server.py` v2.4 (`C:/user/angus/zmq/`), actions: ping / get_rates / get_account_info / get_positions, pagination supported
- **Missing for v3:**
  1. `order` action (submit / modify / close)
  2. Source IP whitelist (Merlin's Mac only)
  3. `decision_id` verification — load `decisions/{date}.json` from synced repo, confirm status GO and payload matches before executing
  4. Hard-coded final checks server-side: SL present, risk ≤ 0.5% equity, lot ≤ script-computed max, no SL → reject
  5. `execution_log.json` write-back (fill price, slippage, timestamps) + git push
- **Tokens:** MT5 login + broker credentials live here and nowhere else

---

## 4. The v3 Pipeline

```
TRIGGER: cron 19:00 HKT | TV webhook | manual
   │
   ├─① MERLIN (Mac)          → merlin_research.json   (thesis, bias, conf, risks)
   ├─② WALKER                → walker_ta.json         (TA, ORB, entry/SL/TP, screenshot)
   ├─③ ALFRED (Windows)      → alfred_risk.json       (veto flags, account state, stats)
   │
   ├─④ QUANT_GATE.PY (Mac)   deterministic: SOP lookup, sample size, false-breakout,
   │                          ATR regime, TF-ratio check, stale-DR detection
   │                          → pass | veto(reason)
   ├─⑤ COMPLIANCE_GATE.PY    deterministic: economic calendar (FOMC/NFP/CPI ±30min),
   │                          kill-zone window, daily trade count, cooldown,
   │                          daily/weekly loss caps, broker rate limits
   │                          → pass | veto(reason)
   │
   ├─⑥ MERLIN_ORCHESTRATOR   decision matrix (unchanged thresholds):
   │                          GO (≥75, full) / CONDITIONAL_GO (60-74, 0.5×) / NO_GO
   │                          + lot = (equity × 0.5%) / (SL pts × point value)  [script]
   │                          → decisions/{date}.json  (git push)
   │
   ├─⑦ EXECUTION PAYLOAD     {decision_id, symbol, direction, entry, sl, tp, lot, expiry}
   │                          → ZMQ POST → Carson (Windows)
   │
   ├─⑧ CARSON                verify whitelist → verify decision_id GO → verify hard limits
   │                          → MT5 order → execution_log.json (fill, slippage) → git push
   │
   └─⑨ FEEDBACK LOOP         execution results → Alfred's next-day stats
                              weekly review updates SOP v2.0 lookup tables
```

**Any gate veto = trade terminated.** Gate vetoes are logged with reasons in `decisions/{date}.json` so the weekly review can measure gate quality.

### JSON Contract: Execution Payload (Stage 7)
```json
{
  "decision_id": "2026-09-11-NAS100-1",
  "decision_file": "decisions/2026-09-11.json",
  "symbol": "NAS100",
  "direction": "long",
  "entry_type": "limit",
  "entry": 26700.0,
  "sl": 26665.0,
  "tp": 26805.0,
  "lot": 0.5,
  "risk_pct": 0.5,
  "risk_amount": 175.0,
  "valid_until": "2026-09-11T16:00:00Z",
  "issued_by": "merlin_orchestrator",
  "gates": {"quant": "pass", "compliance": "pass", "alfred": "GO"}
}
```

### Carson-side server checks (Stage 8, in order)
1. Source IP ∈ whitelist
2. `decision_id` exists in synced repo AND `decisions/{date}.json` status == GO
3. Payload fields match decision file (symbol/direction/SL/TP)
4. SL present; SL distance > 0; risk_pct ≤ 0.5
5. lot ≤ script-computed max
6. `valid_until` not expired
7. MT5 terminal connected
→ Any failure: reject, log to `rejected_orders.log`, notify Discord `#risk-check`

---

## 5. Communication Topology

| Channel | Use | Notes |
|---|---|---|
| **ZMQ REQ/REP** (5555) | Execution payload, fills, data fetch | Direct, sub-second. Execution traffic only. |
| **Git repo** | Analysis reports, decisions, execution logs | Sync layer. Push failures are non-fatal (known cron credential issue). Alfred's signal files authoritative on conflict (`--theirs`). |
| **Discord** | Human-readable debate, final call, execution alerts | Channel map unchanged from v2.4. Add `#executions`. |
| **Webhook gateway** | TV alerts → Merlin | Single-agent mode retained; webhook thesis must still pass gates ④⑤ — no shortcut because event-triggered. |

---

## 6. What Changes vs Today (delta list)

1. `quant_gate.py` — new, runs before orchestrator (extracts Alfred Mode B checks into code)
2. `compliance_gate.py` — new, deterministic event/killzone/limit checks
3. Lot sizing — moves from Alfred's LLM to script in orchestrator
4. Carson `order` action + 6 server-side checks + execution logging
5. Walker entry/SL/TP become concrete mandatory numbers
6. `#executions` Discord channel for fill/slippage reporting
7. Paper-trading mode: GO decisions logged but not executed, for 2–4 weeks of validation
8. Economic calendar data feed for compliance gate (source TBD — candidate: investing.com scrape already used by portal)

---

## 7. Open Questions — RESOLVED by agent inventories (2026-09-12/13)

Inventories received: `signals/2026-09-12/agent_inventory_walker.json`,
`signals/2026-09-13/walker_followup.json`, Alfred + Carson JSONs (via AC, 2026-09-13).
Detailed findings: Section 8.

- [x] Alfred SOP data: CSV at `C:/Users/angus/.hermes/research/fomc-late-reversal/data/`
  (`backtest_recommended_transactions.csv`, `nas100_d1_full.json`) — Mac-readable via sync
- [x] Alfred git push: 98% success (rare credential timeouts, occasional network retries)
- [x] Carson symbols: verified NAS100, US500, XAUUSD, EURUSD, GBPUSD, USDJPY;
      NEED VERIFY: BTCUSD, HK50, JPN225, GER40
- [x] Carson auto-restart: currently manual startup — must convert to auto-start
      (watchdog cron exists every 12h but server start itself is manual)
- [x] Economic calendar source: still open — Carson also flagged it (`新聞黑窗API endpoint`)
- [x] Risk budget: Alfred agrees 0.5%/trade sizing; **CONFLICT on Carson hard cap** —
      Carson proposes 1%, Alfred proposes 2% → AC decision required
- [x] Single vs multiple accounts: Alfred runs FTMO prop-firm account(s) —
      prop-firm rules (DD≥5%, daily≥2%) are already hard-coded in his veto list

## 7b. AC Decisions (2026-09-14) — FINAL

1. **Carson-side max risk cap: 1%** per trade (Carson's proposal adopted; sizing target remains 0.5%)
2. **Alfred's new vetoes: adopt at 60%** — event-week false-breakout > 60% → VETO (stricter than v2.4's 85%); VIX > 35 → VETO (VIX data via web fallback, checked in quant gate)
3. **ORB breakdown contract: YES** — walker_ta.json must include the 6-category breakdown summing to 100; quant gate validates arithmetic; missing/invalid breakdown → gate warning, 3+ consecutive failures → gate veto
4. **Timing: Option A** — Walker cron moves to 18:30 HKT (action: Walker), Alfred stays 18:45, Merlin orchestrator stays 19:00
5. **Carson security hardening: APPROVED** — restricted bind + API-key layer + source-IP check are prerequisites for the `order` action; no execution until deployed

---

## Appendix A — Agent Inventory Prompts

Send each prompt to the corresponding agent's own session. Responses get appended to Section 7 and refine the model.

### A1. → Walker
```
Model refinement exercise. We are upgrading the War Room to a five-stage pipeline
(research → quant → risk → compliance → execution) where your TA output feeds a
deterministic quant gate and, eventually, automated execution via Carson.
Answer precisely — this defines your JSON contract going forward:

1. SKILLS: List every trading skill you currently have loaded/available, and which
   you actually use in a daily analysis run.
2. OUTPUT FIELDS: Paste your last walker_ta.json. Which fields are always populated?
   Which are sometimes null/missing (e.g. orb_score before market open)?
3. ENTRY PARAMETERS: How confident are you in producing concrete entry/SL/TP numbers
   every run (required for automated lot sizing)? What would make you NOT produce them?
4. DATA DEPENDENCIES: Which data sources do you need (MT5 bridge, TradingView MCP,
   screenshots)? What are their failure modes and your fallbacks?
5. TIMING: Your slot is 18:30 HKT. How long does a full run take, and what is the
   latest you could still deliver reliably before Merlin's 19:00 orchestrator?
6. VETO: Confirm ORB<40 veto rule. Any other conditions where you would want a hard
   NO_GO that isn't currently encoded?
7. GAPS: What information do you NOT receive today that would most improve your TA?
```

### A2. → Alfred
```
Model refinement exercise. We are upgrading the War Room to a five-stage pipeline.
Your statistical validation moves into a deterministic script (quant_gate.py) and
your risk veto stays as the account-level authority. Lot sizing moves from your
prompt to a script. Answer precisely:

1. SKILLS: List every skill loaded on your Windows Hermes instance, and which you
   actually use for (a) statistical validation and (b) account risk checks.
2. BACKTEST DATA: Where does your SOP v2.0 lookup data live (exact path on Windows)?
   What is its format (JSON/CSV/SQLite)? Which fields: asset, event week, session,
   false-breakout rate, sample size, win rate? Can the Mac quant gate read a synced
   copy, or must you compute and publish alfred_stats.json?
3. ACCOUNT DATA: Confirm you read account state via Carson ZMQ (get_account_info /
   get_positions). What refresh rate do you need for intraday DD monitoring?
4. OUTPUT FIELDS: Paste your last alfred_risk.json. Which fields does the
   orchestrator actually need vs nice-to-have?
5. LOT SIZING: Currently lot = (Balance × 2%) / (SL points × $10). The v3 proposal
   is risk 0.5%/trade computed in the orchestrator script with your veto unchanged.
   Do you agree? What maximum-risk rule do you want hard-coded on Carson's side?
6. VETO LIST: Confirm the current veto conditions (DD≥5%, daily DD≥2%, 3+ consecutive
   losses, positions≥3, news<15min, MT5 disconnected). Additions/removals?
7. GIT SYNC: Do you push alfred_risk.json via git from Windows? Any credential or
   timing failures we should design around?
8. GAPS: What information do you NOT receive today that would most improve your
   statistical validation?
```

### A3. → Carson (if reachable as an agent; otherwise AC runs these checks on Windows)
```
Model refinement exercise. Your ZMQ server (alfred_server.py v2.4) will become the
sole execution point in a five-stage pipeline. The `order` action needs to be added
with hard safety checks. Answer precisely:

1. ENVIRONMENT: Confirm MT5 terminal + broker (Pepperstone?), Python version, and
   whether alfred_server.py runs as a scheduled task / manual / auto-start.
2. SYMBOLS: List exact MT5 symbol names available for: NAS100, US500, HK50, JPN225,
   GER40, XAUUSD, EURUSD, GBPUSD, USDJPY, BTCUSD. Any naming variations?
3. MT5 ORDER API: Which MetaTrader5 Python functions are available — order_send with
   ORDER_TYPE_BUY/SELL_LIMIT? Is the broker hedging or netting mode?
4. SECURITY: Can the server bind/check client IP (whitelist Merlin's Mac)? Is port
   5555 firewalled to LAN only, or internet-exposed?
5. STATE: Where could you read the synced decisions/{date}.json on Windows (git repo
   clone path)? Could you verify a decision_id before accepting an order?
6. HARD LIMITS: Propose the server-side rejection rules you can enforce locally
   (SL required, max risk %, max lot, expiry). What account metadata do you need
   (equity, balance) to compute them?
7. LOGGING: Can you write execution_log.json (order ticket, fill price, slippage,
   timestamps) and git push from Windows?
8. RECOVERY: Current restart procedure when the server hangs (known REQ-REP deadlock).
   Would you accept a watchdog/scheduled-task auto-restart?
```

### A4. → Merlin (self-inventory, for completeness)
```
Self-inventory for the five-stage pipeline refinement:
1. Skills + scripts actually used per cron run (19:00) vs occasionally.
2. cron/webhook/3-layer-monitor failure rates observed in the last 60 days.
3. What Stage-1 thesis fields the quant gate can consume mechanically.
4. Economic calendar source options for compliance_gate.py (FOMC/NFP/CPI ±30min),
   with reliability notes.
5. Orchestrator changes required: gate sequencing, lot-size function, execution
   payload emission, decision_id scheme.
6. Which current steps I do that should become deterministic scripts instead.
```

---

## 8. Agent Inventory Findings (2026-09-12/13) — verified refinements

### 8.1 Walker (inventory + follow-up)

**Role resolution — Stage 1.5 "Technical + Event Context":**
Walker's follow-up clarifies his macro work is **event awareness only** (FOMC blackout
windows, calendar volatility expectations) — NOT narrative/yields/DXY/COT analysis.
His own verdict: *"Walker is NOT doing macro analysis beyond event awareness.
Merlin should own macro."* → Macro/narrative stays with Merlin; Walker keeps technical
analysis + event-risk context. No role migration needed; the Stage 1.5 label is
formalized as: technical analysis + event-aware conditioning + machine-readable triggers.

**Regime filter (verified deterministic):**
- Transformer per-asset (64-bar, 3-layer encoder, 4-head), 25 features, 77-80% accuracy
- Thresholds: TREND = ADX≥25, RANGE = ADX≤20, HIGH_VOL = ATR pct ≥ 0.80
- Script: `~/trading-ml/scripts/walker_regime_filter.py` on Walker's Mac (192.168.64.12),
  models at `~/trading-ml/models/regime_transformer_{SYMBOL}.pt`
- Merlin CAN run directly (Python 3.11 + torch + numpy + pandas + zmq)
- → `ml_regime`, `regime_confidence`, `regime_probs` become **required** walker_ta.json fields

**ORB scoring — key discovery:**
- Still uses orb-bias-filter 6-category checklist, but the score is **LLM-judged**,
  no deterministic script, and the breakdown is not machine-readable
- v2.4 decision-matrix thresholds (60/55) were backtested on this scoring → thresholds
  remain valid only if scoring stays consistent → quant gate should validate a
  machine-readable per-category breakdown (sums to 100) going forward

**Conditional triggers — ACCEPTED as contract:**
```json
"conditional_triggers": [
  {"condition": "close_below", "timeframe": "M15/H1", "level": 29215.0,
   "action": "bearish_active", "targets": [28953.9, 28882.0], "invalidates": null},
  {"condition": "reclaim_above", "timeframe": "H1", "level": 29482.5,
   "action": "bearish_invalidated", "targets": [29607.6, 29734.2], "invalidates": "bearish_active"}
]
```
Exact floats, explicit timeframes, 2-4 triggers per analysis. Consumed by
compliance_gate.py and Carson.

**Timing:** cannot deliver by 18:45 (runtime 15-20 min; verification subagent 3-5 min
is the bottleneck). Recommends: Walker 18:30 → delivery 18:45-50 → Merlin 19:00 unchanged.

**Veto re-allocation (Walker agreed):**
- Move to compliance_gate.py: FOMC blackout <15min, MT5 bridge offline
- Walker keeps: ORB<40, regime HIGH_VOL conf>70%, D1 structure ambiguous,
  price at extreme (<10%/>90% of range) — all require LLM/transformer judgment

### 8.2 Alfred

**Environment surprise:** WSL2 (Ubuntu 24.04) on Windows 10 host, IP 172.18.98.212 —
not native Windows. ZMQ to Carson had WSL2 namespace issues (fixed in his v2.3).

**Stack:** `nas100-daily-bias`, `nas-orb-retest` v2.0, `carson-zmq-server` v2.3,
`multi-agent-trading-war-room`, `prop-firm-risk-manager`, `options-pricing`,
`mql5-ea-development` / `mt5-ea-trade-tracking` (occasional).

**SOP data (resolves open question):** CSV at
`C:/Users/angus/.hermes/research/fomc-late-reversal/data/` —
`backtest_recommended_transactions.csv` + `nas100_d1_full.json`; fields include
ticket/entry/exit/symbol/direction/prices/SL/TP/pnl/bars_held/exit_reason.
Mac-readable via git sync → **quant_gate.py can consume a synced copy directly.**

**Latest output reality-check:** his 2026-09-10 run was `NO_GO / veto: "Cannot verify
account status — MT5/ZMQ connection error for FTMO"` — the "cannot verify → default
NO_GO" safety rule works as designed, but shows FTMO login failures are live risk.
Field reliability: timestamp/go_no_go/veto/recommended_lot_size always present;
factors and account balances sometimes null (orchestrator `or default` defense required).

**Veto list:** confirmed 6 existing (all hard-coded); proposes adding VIX>35 and
event-week false-breakout >60% (vs current 85% — stricter, more blocked trades).
No removals.

**Position sizing:** agrees 0.5%/trade deterministic script; veto power unchanged;
wants Carson hard cap at 2.0% (CONFLICT with Carson's 1% — see 7b).

**Git:** 98% success from WSL2.

**Alfred's own LLM/script split (mirrors v3 design):** migrate DD checks, news blackout,
consecutive-loss counter, ORB threshold check, decision_id validation to scripts;
keep LLM for unstructured-news impact judgment, sanity-checking Walker's TA,
and human-readable veto_reason. This is an independent endorsement of the
"LLMs propose, scripts dispose" principle.

**Information gap reported:** wants Walker's ORB + entry/SL/TP as inputs —
confirms signal-file ordering matters (Walker before Alfred).

### 8.3 Carson

**Environment:** Windows 11, hostname Carson, 192.168.11.173, Hermes profile default.
Server: `C:\Users\hkvid\zmq\MT5_server.py` (venv Python), port 5555. **Startup is
MANUAL** — must convert to auto-start/scheduled task; watchdog (12h cron) exists but
restart requires manual steps.

**Execution capability (confirms feasibility):**
- `order_send` supports MARKET + LIMIT + STOP; account is **hedging** mode
- API available: positions_get, history_deals_get, symbol_info_tick, account_info
- Current bridge is read-only — `order` action must be added

**Symbols:** verified NAS100, US500, XAUUSD, EURUSD, GBPUSD, USDJPY;
need verification: BTCUSD, HK50, JPN225, GER40 (verify before routing any order).

**Security (gap):** binds `0.0.0.0`, no whitelist implemented, LAN-only in practice.
Carson proposes: restricted bind, API-key layer, source-IP check. Required before
`order` goes live.

**decision_id validation — ACCEPTED:** repo clone at `C:\Users\hkvid\trading-war-room`;
process: git pull → read decisions/{date}.json → verify GO → else reject.

**Carson's proposed hard reject rules:** SL mandatory; max risk 1%/trade (CONFLICT
with Alfred's 2.0% — AC decision); max lot 2.0; no market orders (GTC/limit only);
symbol must be in verified list.

**Carson's requested info (must be provided by v3 build):**
1. Mac-side research JSON formats (walker_ta.json / merlin_research.json / alfred_risk.json schemas)
2. decision_id generation rule + timestamp format
3. News-blackout API endpoint (economic calendar source — shared open question)
4. Cross-agent time sync (NTP) — server timestamps have shown drift before

**Carson's script-migration list:** decision validation, risk→max-lot calculator,
standardized order payload builder, position monitor — all consistent with v3 Stage 5+8.

### 8.4 Cross-agent synthesis — what changed in the model

1. **Walker stays Stage 1.5, no role migration** (event awareness ≠ macro analysis).
2. **Regime filter is shareable infrastructure** — Merlin can run it directly; make
   its outputs mandatory fields.
3. **ORB score is the weakest link in automation** — LLM-judged with no breakdown.
   Mitigation: machine-readable category breakdown validated by quant gate.
4. **Signal ordering fix**: Walker (18:30) → Alfred (18:45) → Merlin (19:00) — Alfred
   explicitly needs Walker's numbers as risk-gate inputs.
5. **Alfred independently endorsed the script/LLM split** — design validated by
   the agent who operates the risk gate.
6. **Carson side is feasible today** (order_send LIMIT + hedging + repo validation),
   gated only on: security hardening, auto-start, symbol verification, and the
   risk-cap decision.
7. **Open items now shared**: economic calendar/news-blackout endpoint (Merlin
   compliance gate + Carson both need it); NTP/time-sync discipline.
8. **FTMO login fragility** is a live operational risk — Alfred's account-verification
   path needs a retry/health-check before the pipeline trusts his GO signals.

---

*Document owner: Merlin (Mac). v3.1 — updated 2026-09-13 with all three agent inventory findings (Section 8). Next: AC decisions (7b) → build quant_gate.py + compliance_gate.py → Carson order action.*
