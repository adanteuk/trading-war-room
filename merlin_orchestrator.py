#!/usr/bin/env python3
"""
Merlin Orchestrator — Research-Driven Multi-Agent Trading Coordinator
Merlin (Mac) orchestrates the daily debate between Walker (Technical Analyst)
and Alfred (Risk Manager). Makes the final go/no-go decision.

DECISION TIERS (v2):
- GO:             conf ≥ 65 AND ORB ≥ 55 AND no Alfred veto → full position
- CONDITIONAL_GO: conf ≥ 55 AND ORB ≥ 50 AND no Alfred veto → reduced position
- NO_GO:          everything else

Alfred HARD VETO (only veto=true blocks, WAIT just reduces size):
- Alfred GO   → lot_multiplier = 1.0 (full size)
- Alfred WAIT → lot_multiplier = 0.5 (50% size)
- Alfred NO_GO → lot_multiplier = 0.25 (25% size)
- Alfred VETO → automatic NO_GO regardless of TA

Run daily at 7:00 PM HKT on trading days from the Mac.
"""

import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────
REPO_DIR = Path(os.path.expanduser("~/.hermes/trading-war-room"))
SIGNALS_DIR = REPO_DIR / "signals"
DEBATE_DIR = REPO_DIR / "debate"
DECISIONS_DIR = REPO_DIR / "decisions"

# Discord channel IDs
DISCORD_CHANNELS = {
    "daily-briefing": "1505601530575716372",
    "research-context": "1505601583444918423",
    "technical-setup": "1505601621839843418",
    "risk-check": "1505601652470583506",
    "debate-thread": "1505601691666354402",
    "final-call": "1505601720439406732",
    "trade-log": "1505601751519199382",
    "weekly-review": "1505601783416754298",
    "ops": "1505601804178690211",
}

# Wait times (seconds)
WAIT_FOR_INPUTS = 30  # 30 sec max wait (temporarily reduced)
CHECK_INTERVAL = 60     # Check every 60 seconds

# US Market Holidays (2026)
US_HOLIDAYS = [
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
    "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07",
    "2026-11-26", "2026-12-25",
]


def is_trading_day() -> bool:
    now_hk = datetime.now(timezone(timedelta(hours=8)))
    if now_hk.weekday() >= 5:
        return False
    if now_hk.strftime("%Y-%m-%d") in US_HOLIDAYS:
        return False
    return True


def git_pull():
    """Pull latest from shared repo."""
    os.chdir(REPO_DIR)
    result = subprocess.run(["git", "pull", "--rebase"], capture_output=True, text=True)
    return result.returncode == 0


def git_push(message: str):
    """Commit and push changes."""
    os.chdir(REPO_DIR)
    subprocess.run(["git", "add", "."], capture_output=True)
    subprocess.run(["git", "commit", "-m", message], capture_output=True)
    subprocess.run(["git", "push"], capture_output=True)


def check_input_ready(date_str: str) -> dict:
    """Check if Walker and Alfred have posted their analysis."""
    today_dir = SIGNALS_DIR / date_str
    status = {
        "walker": False,
        "alfred": False,
        "walker_data": None,
        "alfred_data": None,
    }

    walker_file = today_dir / "walker_ta.json"
    alfred_file = today_dir / "alfred_risk.json"

    if walker_file.exists():
        status["walker"] = True
        with open(walker_file) as f:
            status["walker_data"] = json.load(f)

    if alfred_file.exists():
        status["alfred"] = True
        with open(alfred_file) as f:
            status["alfred_data"] = json.load(f)

    return status


def calculate_final_decision(walker_data: dict, alfred_data: dict) -> dict:
    """
    Merlin synthesizes TA + Risk into a final decision.

    Decision tiers (v2 — relaxed from impossible thresholds):
    - GO:             conf ≥ 65 AND ORB ≥ 55 AND no Alfred veto
    - CONDITIONAL_GO: conf ≥ 55 AND ORB ≥ 50 AND no Alfred veto (reduced size)
    - NO_GO:          everything else

    Alfred HARD VETO overrides everything.
    Alfred WAIT no longer blocks — it only reduces position size.
    """
    decision = {
        "date": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "orchestrator": "Merlin",
        "walker_position": "NO_INPUT",
        "alfred_risk_status": "NO_INPUT",
        "merlin_thesis": "",
        "final_decision": "NO_GO",
        "trade_params": {},
        "reasoning": "",
        "alfred_veto": False,
        "veto_reason": "",
    }

    # ── Alfred HARD VETO check (only this blocks, not WAIT) ──
    if alfred_data:
        decision["alfred_risk_status"] = alfred_data.get("go_no_go", "UNKNOWN")
        if alfred_data.get("veto", False):
            decision["alfred_veto"] = True
            decision["veto_reason"] = alfred_data.get("veto_reason", "Risk limits exceeded")
            decision["final_decision"] = "NO_GO — VETOED BY ALFRED"
            decision["reasoning"] = f"Alfred vetoed: {decision['veto_reason']}"
            return decision

    # ── Merlin makes the call ──
    if walker_data:
        decision["walker_position"] = walker_data.get("bias", "unknown")

        walker_confidence = walker_data.get("confidence", 50)
        walker_orb = walker_data.get("orb_score", 50)
        alfred_risk = alfred_data.get("go_no_go", "WAIT") if alfred_data else "WAIT"

        # Determine tier and lot multiplier
        # Alfred GO = full size, WAIT = 50% size, NO_GO = 25% size
        if alfred_risk == "GO":
            lot_multiplier = 1.0
            alfred_note = "Alfred: full size approved"
        elif alfred_risk == "WAIT":
            lot_multiplier = 0.5
            alfred_note = "Alfred: WAIT — reduced to 50% size"
        else:
            lot_multiplier = 0.25
            alfred_note = "Alfred: NO_GO — minimum 25% size"

        # ── Tier 1: GO (high conviction) ──
        if walker_confidence >= 65 and walker_orb >= 55:
            decision["final_decision"] = "GO"
            bias = walker_data.get("bias", "neutral")
            direction = "LONG" if bias == "bullish" else "SHORT" if bias == "bearish" else "NONE"

            entry = walker_data.get("entry", "TBD")
            sl = walker_data.get("sl", "TBD")
            tp = walker_data.get("tp", "TBD")

            base_lot = alfred_data.get("recommended_lot_size", "TBD") if alfred_data else "TBD"
            # Apply multiplier to lot size
            if isinstance(base_lot, (int, float)):
                adjusted_lot = round(base_lot * lot_multiplier, 2)
            else:
                adjusted_lot = f"{base_lot} x {lot_multiplier}"

            decision["trade_params"] = {
                "direction": direction,
                "instrument": "NAS100",
                "entry": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "tier": "GO",
                "lot_size": adjusted_lot,
                "lot_multiplier": lot_multiplier,
                "risk_pct": alfred_data.get("max_daily_loss_pct", 2.0) if alfred_data else 2.0,
                "session_window": "09:30-11:00 ET",
                "close_before": "13:30 ET (pre-news)",
            }

            decision["reasoning"] = (
                f"TA: conf={walker_confidence}, ORB={walker_orb} → HIGH CONVICTION\n"
                f"{alfred_note}\n"
                f"Risk: {'; '.join(alfred_data.get('factors', [])) if alfred_data else 'N/A'}\n"
                f"Merlin: {decision['merlin_thesis']}"
            )

        # ── Tier 2: CONDITIONAL_GO (moderate conviction, reduced size) ──
        elif walker_confidence >= 55 and walker_orb >= 50:
            decision["final_decision"] = "CONDITIONAL_GO"
            bias = walker_data.get("bias", "neutral")
            direction = "LONG" if bias == "bullish" else "SHORT" if bias == "bearish" else "NONE"

            entry = walker_data.get("entry", "TBD")
            sl = walker_data.get("sl", "TBD")
            tp = walker_data.get("tp", "TBD")

            base_lot = alfred_data.get("recommended_lot_size", "TBD") if alfred_data else "TBD"
            if isinstance(base_lot, (int, float)):
                adjusted_lot = round(base_lot * lot_multiplier, 2)
            else:
                adjusted_lot = f"{base_lot} x {lot_multiplier}"

            decision["trade_params"] = {
                "direction": direction,
                "instrument": "NAS100",
                "entry": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "tier": "CONDITIONAL_GO",
                "lot_size": adjusted_lot,
                "lot_multiplier": lot_multiplier,
                "risk_pct": alfred_data.get("max_daily_loss_pct", 1.0) if alfred_data else 1.0,
                "session_window": "09:30-11:00 ET",
                "close_before": "13:30 ET (pre-news)",
                "note": "Reduced conviction — half size, tighter risk",
            }

            decision["reasoning"] = (
                f"TA: conf={walker_confidence}, ORB={walker_orb} → MODERATE CONVICTION\n"
                f"{alfred_note}\n"
                f"Risk: {'; '.join(alfred_data.get('factors', [])) if alfred_data else 'N/A'}\n"
                f"Merlin: {decision['merlin_thesis']}"
            )

        # ── Tier 3: NO_GO (below all thresholds) ──
        else:
            decision["final_decision"] = "NO_GO"
            if walker_confidence < 45 and walker_orb < 45:
                decision["reasoning"] = f"TA confidence too low (conf={walker_confidence}, orb={walker_orb}) — both below 45"
            elif walker_confidence < 55:
                decision["reasoning"] = f"TA confidence below GO threshold (conf={walker_confidence} < 55, orb={walker_orb})"
            elif walker_orb < 50:
                decision["reasoning"] = f"ORB score below GO threshold (conf={walker_confidence}, orb={walker_orb} < 50)"
            else:
                decision["reasoning"] = f"Mixed signals — standing aside (conf={walker_confidence}, orb={walker_orb})"
    else:
        decision["reasoning"] = "No TA input received from Walker"

    return decision


def run_debate_rounds(walker_data: dict, alfred_data: dict, decision: dict, merlin_data: dict = None) -> list:
    """
    Generate debate messages for Discord channels.
    Returns a list of (channel, message) tuples to post.
    """
    messages = []

    # ─── Message 1: Research Context ───
    research_msg = f"🧙 **MERLIN RESEARCH — {decision['date']}**\n\n"
    if merlin_data:
        bias = merlin_data.get("bias", "N/A")
        conf = merlin_data.get("confidence", "N/A")
        summary = merlin_data.get("summary", "N/A")
        ict = merlin_data.get("ict_analysis", {})

        research_msg += f"**Bias**: {bias} | **Confidence**: {conf}/100\n\n"
        research_msg += f"**Thesis**: {summary}\n\n"
        research_msg += f"📊 **3-Layer ICT/CRT Pipeline Analysis**:\n"
        research_msg += f"• **L1 (D1)**: {ict.get('daily_bias', 'N/A')}\n"
        research_msg += f"• **L2 (H4)**: {ict.get('h4_context', 'N/A')}\n"
        research_msg += f"• **L3 (M15)**: {ict.get('m15_status', 'N/A')}\n\n"

        risks = merlin_data.get("risks", [])
        if risks:
            research_msg += f"⚠️ **Today's Risks**:\n"
            for r in risks:
                research_msg += f"• {r.get('event', '')} @ {r.get('time', '')} [{r.get('impact', '')}]\n"
            research_msg += "\n"

        research_msg += f"💡 **Recommendation**: {merlin_data.get('recommendation', 'N/A')}"
    else:
        research_msg += f"*Research thesis not available.*"

    messages.append(("research-context", research_msg))

    # ─── Message 2: Technical Setup ───
    ta_msg = f"🤖 **WALKER TA ANALYSIS — {decision['date']}**\n\n"
    if walker_data:
        ta_msg += f"**Bias**: {walker_data.get('bias', 'N/A')}\n"
        ta_msg += f"**ICT Profile**: {walker_data.get('ict_profile', 'N/A')}\n"
        ta_msg += f"**ORB Score**: {walker_data.get('orb_score', 'N/A')}/100\n"
        ta_msg += f"**Confidence**: {walker_data.get('confidence', 'N/A')}/100\n\n"
        ta_msg += f"**Analysis**: {walker_data.get('reasoning', 'N/A')}"
    else:
        ta_msg += f"*No TA input received.*"

    messages.append(("technical-setup", ta_msg))

    # ─── Message 3: Risk Check ───
    risk_msg = f"🦇 **ALFRED RISK ASSESSMENT — {decision['date']}**\n\n"
    if alfred_data:
        risk_msg += f"**Status**: {alfred_data.get('go_no_go', 'N/A')}\n"
        risk_msg += f"**Veto**: {'🛑 YES' if alfred_data.get('veto') else '✅ No'}\n"
        for factor in alfred_data.get('factors', []):
            risk_msg += f"• {factor}\n"
        risk_msg += f"\n**Lot Size**: {alfred_data.get('recommended_lot_size', 'TBD')}\n"
        risk_msg += f"**Max Daily Loss**: {alfred_data.get('max_daily_loss_pct', 'N/A')}%\n"
        risk_msg += f"**Consecutive Losses**: {alfred_data.get('consecutive_losses', 'N/A')}"
    else:
        risk_msg += f"*No risk input received.*"

    messages.append(("risk-check", risk_msg))

    # ─── Message 4: Debate Thread (Round 1) ───
    debate_r1 = f"🎙️ **DEBATE ROUND 1 — {decision['date']}**\n\n"
    debate_r1 += f"**The Floor**:\n\n"

    if walker_data:
        debate_r1 += f"🤖 **Walker** says: {walker_data.get('bias', 'N/A')} setup, ORB {walker_data.get('orb_score', '?')}/100, Conf {walker_data.get('confidence', '?')}/100. {walker_data.get('reasoning', '')[:200]}\n\n"

    if alfred_data:
        debate_r1 += f"🦇 **Alfred** says: Risk {alfred_data.get('go_no_go', '?')}. DD safe, lot size {alfred_data.get('recommended_lot_size', '?')}. {'VETO issued.' if alfred_data.get('veto') else 'Green light.'}\n\n"

    if merlin_data:
        debate_r1 += f"🧙 **Merlin** says: {merlin_data.get('summary', 'N/A')}\n\n"

    debate_r1 += f"*Waiting for Round 2 rebuttals...*"

    messages.append(("debate-thread", debate_r1))

    # ─── Message 5: Debate Thread (Round 2 + Advice) ───
    debate_r2 = f"🎙️ **DEBATE ROUND 2 + MERLIN ADVICE — {decision['date']}**\n\n"

    # Merlin's 3-layer synthesis and advice
    if merlin_data and walker_data:
        debate_r2 += f"🧙 **Merlin's 3-Layer Synthesis & Advice**:\n\n"

        ict = merlin_data.get("ict_analysis", {})
        w_conf = walker_data.get("confidence", 50)
        w_orb = walker_data.get("orb_score", 50)
        a_go = alfred_data.get("go_no_go", "NO_GO") if alfred_data else "NO_GO"

        # Build advice based on 3-layer analysis
        advice_parts = []

        # Layer 1 advice
        daily_bias = merlin_data.get("bias", "Neutral").lower()
        if "bearish" in daily_bias:
            advice_parts.append("1️⃣ **L1 (D1)** confirms bearish direction → Only look for SHORT setups today")
        elif "bullish" in daily_bias:
            advice_parts.append("1️⃣ **L1 (D1)** confirms bullish direction → Only look for LONG setups today")
        else:
            advice_parts.append("1️⃣ **L1 (D1)** is NEUTRAL → Stand aside or reduce size significantly")

        # Layer 2 advice
        h4_ctx = ict.get("h4_context", "")
        if "fvg" in h4_ctx.lower() or "premium" in h4_ctx.lower():
            advice_parts.append("2️⃣ **L2 (H4)** shows active FVG/Premium → Wait for price to reach key level before entry")
        elif "discount" in h4_ctx.lower():
            advice_parts.append("2️⃣ **L2 (H4)** in Discount → Look for buy-side reaction for long entries")

        # Layer 3 advice
        m15_status = ict.get("m15_status", "")
        if "compression" in m15_status.lower():
            advice_parts.append("3️⃣ **L3 (M15)** compression detected → Expansion imminent, but wait for Kill Zone confirmation")
        elif "kill zone" in m15_status.lower() or "ob" in m15_status.lower():
            advice_parts.append("3️⃣ **L3 (M15)** OB + Kill Zone setup forming → High probability if confirmed")

        # Scoring advice
        debate_r2 += "**3-Layer ICT/CRT Pipeline Assessment**:\n"
        for a in advice_parts:
            debate_r2 += f"{a}\n\n"

        debate_r2 += f"**Scoring Gap Analysis**:\n"
        debate_r2 += f"• Walker Confidence: {w_conf}/100 (GO ≥65 | CONDITIONAL ≥55)\n"
        debate_r2 += f"• Walker ORB Score: {w_orb}/100 (GO ≥55 | CONDITIONAL ≥50)\n"
        debate_r2 += f"• Alfred Risk: {a_go} (GO=full | WAIT=50% | VETO=block)\n\n"

        # Specific advice based on new thresholds
        if w_conf >= 65 and w_orb >= 55:
            debate_r2 += f"💡 **Advice**: All metrics met for GO. Execute with discipline. Target 3R, respect SL.\n"
        elif w_conf >= 55 and w_orb >= 50:
            debate_r2 += f"💡 **Advice**: CONDITIONAL GO — moderate conviction. Half size, tighter risk. Still tradeable.\n"
        elif w_conf < 55 and w_orb >= 50:
            debate_r2 += f"💡 **Advice**: ORB structure is OK but confidence low. Check SMT divergence and Dealing Range confluence to boost confidence.\n"
        elif w_conf >= 55 and w_orb < 50:
            debate_r2 += f"💡 **Advice**: Confidence acceptable but ORB quality low. Wait for clearer candle close and volume confirmation.\n"
        else:
            debate_r2 += f"💡 **Advice**: Both metrics below threshold. **STAND ASIDE** — no trade today is better than a bad trade.\n"

        risks = merlin_data.get("risks", [])
        if risks:
            high_risks = [r for r in risks if r.get("impact") == "high"]
            if high_risks:
                debate_r2 += f"\n⚠️ **High-Impact Events**: "
                debate_r2 += ", ".join([f"{r['event']} @ {r['time']}" for r in high_risks])
                debate_r2 += " → Consider closing positions before these times."
    else:
        debate_r2 += f"*Insufficient data for debate.*"

    messages.append(("debate-thread", debate_r2))

    # ─── Message 6: Final Call ───
    final_msg = f"🎯 **FINAL CALL — {decision['date']}**\n\n"
    
    fd = decision['final_decision']
    if fd == "GO":
        final_msg += f"Decision: **🟢 GO**\n\n"
    elif fd == "CONDITIONAL_GO":
        final_msg += f"Decision: **🟡 CONDITIONAL GO** (reduced size)\n\n"
    elif "VETOED" in fd:
        final_msg += f"Decision: **🔴 NO GO — VETOED**\n\n"
    else:
        final_msg += f"Decision: **🔴 NO GO**\n\n"
    
    final_msg += f"### Reasoning\n{decision.get('reasoning', 'N/A')}\n"

    if decision.get("trade_params"):
        final_msg += f"\n### Trade Parameters\n"
        for k, v in decision["trade_params"].items():
            final_msg += f"• **{k}**: {v}\n"

    messages.append(("final-call", final_msg))

    return messages


def save_all(decision: dict, transcript: str, date_str: str):
    """Save decision and transcript to shared repo."""
    DECISIONS_DIR.mkdir(parents=True, exist_ok=True)
    decision_file = DECISIONS_DIR / f"{date_str}.json"
    with open(decision_file, "w") as f:
        json.dump(decision, f, indent=2)

    DEBATE_DIR.mkdir(parents=True, exist_ok=True)
    debate_file = DEBATE_DIR / date_str / "transcript.md"
    debate_file.parent.mkdir(parents=True, exist_ok=True)
    with open(debate_file, "w") as f:
        f.write(transcript)


def post_to_discord(channel: str, message: str):
    """Post message to Discord channel using bot API."""
    import requests

    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        # Fallback: try loading from .env
        env_path = Path.home() / ".hermes" / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if line.startswith("DISCORD_BOT_TOKEN="):
                        token = line.split("=", 1)[1].strip()
                        break

    channel_id = DISCORD_CHANNELS.get(channel)
    if not token or not channel_id:
        print(f"[DISCORD ⚠️] Missing token or channel ({channel}): token={'✅' if token else '❌'}, id={'✅' if channel_id else '❌'}")
        print(f"  Content preview: {message[:80]}...")
        return

    resp = requests.post(
        f"https://discord.com/api/channels/{channel_id}/messages",
        headers={"Authorization": f"Bot {token}"},
        json={"content": message}
    )
    if resp.status_code == 200:
        print(f"[DISCORD ✅] Posted to #{channel}")
    else:
        print(f"[DISCORD ❌] Failed to post to #{channel}: {resp.status_code} {resp.text[:200]}")


def main():
    now_hk = datetime.now(timezone(timedelta(hours=8)))
    date_str = now_hk.strftime("%Y-%m-%d")

    print(f"=== Merlin Orchestrator — {date_str} ===")
    print(f"Time: {now_hk.strftime('%H:%M')} HKT")

    # Check if trading day
    if not is_trading_day():
        print("Not a trading day. Skipping.")
        return

    # Pull latest data
    print("\n[1/7] Pulling shared repo...")
    if not git_pull():
        print("  ⚠️ Git pull failed, proceeding with local data")

    # Wait for inputs from Walker and Alfred
    print("[2/7] Waiting for Walker (TA) and Alfred (Risk) analysis...")
    start = time.time()
    inputs_ready = False

    while time.time() - start < WAIT_FOR_INPUTS:
        status = check_input_ready(date_str)
        if status["walker"] and status["alfred"]:
            print(f"  ✅ Both inputs ready after {int(time.time() - start)}s")
            inputs_ready = True
            break
        elif int(time.time() - start) % 300 == 0:
            print(f"  ⏳ Waiting... Walker: {'✅' if status['walker'] else '⌛'} Alfred: {'✅' if status['alfred'] else '⌛'}")
        time.sleep(CHECK_INTERVAL)

    if not inputs_ready:
        status = check_input_ready(date_str)
        print(f"\n  ⚠️ Timeout. Proceeding with available data.")
        print(f"  Walker: {'✅' if status['walker'] else '❌'}")
        print(f"  Alfred: {'✅' if status['alfred'] else '❌'}")

    # Load research context (Merlin already has this from own analysis)
    print("\n[3/7] Loading Merlin's research thesis...")
    # Merlin should have already written their research to the signals dir
    merlin_file = SIGNALS_DIR / date_str / "merlin_research.json"
    merlin_data = None
    if merlin_file.exists():
        with open(merlin_file) as f:
            merlin_data = json.load(f)
        print(f"  Research loaded: {merlin_data.get('summary', 'N/A')}")
    else:
        print("  ⚠️ Merlin research file not found")

    # Calculate final decision
    print("\n[4/7] Synthesizing final decision...")
    decision = calculate_final_decision(status["walker_data"], status["alfred_data"])

    # Add Merlin's thesis
    if merlin_data:
        decision["merlin_thesis"] = merlin_data.get("summary", "Research context available")
        # Re-check decision with thesis
        if decision["final_decision"] == "GO" and merlin_data.get("risks"):
            high_risk = [r for r in merlin_data["risks"] if r.get("impact") == "high"]
            if high_risk:
                decision["reasoning"] += f"\nMerlin note: High-impact events today: {[r['event'] for r in high_risk]}"

    print(f"  Decision: {decision['final_decision']}")
    if decision.get("trade_params"):
        for k, v in decision["trade_params"].items():
            print(f"  {k}: {v}")

    # Generate debate messages for Discord
    print("\n[5/7] Generating debate messages for Discord...")
    debate_messages = run_debate_rounds(status["walker_data"], status["alfred_data"], decision, merlin_data)

    # Generate local transcript for repo
    transcript = f"# Debate Transcript — {decision['date']}\n"
    transcript += f"# Orchestrator: Merlin 🧙\n\n"
    for channel, msg in debate_messages:
        transcript += f"## #{channel}\n\n```txt\n{msg}\n```\n\n"

    # Save everything
    print("\n[6/7] Saving to shared repo...")
    save_all(decision, transcript, date_str)

    # Post to Discord channels with 2-second delays to avoid rate limits
    print("\n[7/7] Posting to Discord channels...")
    for i, (channel, message) in enumerate(debate_messages):
        post_to_discord(channel, message)
        if i < len(debate_messages) - 1:
            time.sleep(2)

    # Commit and push
    git_push(f"Merlin: Decision for {date_str} — {decision['final_decision']}")

    print(f"\n✅ Orchestrator complete.")
    print(f"{'='*50}")
    if decision["final_decision"] == "GO":
        print(f"🎯 GO — {decision['trade_params'].get('direction', 'N/A')} NAS100")
    elif "VETO" in decision["final_decision"]:
        print(f"🛑 VETOED BY ALFRED — {decision.get('veto_reason', 'N/A')}")
    else:
        print(f"🚫 NO GO — {decision.get('reasoning', 'Conditions not met')}")


if __name__ == "__main__":
    main()
