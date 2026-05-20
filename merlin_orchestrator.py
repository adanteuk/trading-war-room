#!/usr/bin/env python3
"""
Merlin Orchestrator — Research-Driven Multi-Agent Trading Coordinator
Merlin (Mac) orchestrates the daily debate between Walker (Technical Analyst)
and Alfred (Risk Manager). Makes the final go/no-go decision.

CRITICAL: Alfred retains HARD VETO power on risk grounds.
If Alfred posts a veto, the trade is automatically NO-GO.

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

    The orchestrator (Merlin) weighs:
    1. Walker's TA confidence and ORB score
    2. Alfred's risk limits and account status
    3. Merlin's own research context (already known to self)
    4. Any veto from Alfred

    Alfred has HARD VETO — if his risk assessment says NO, it's NO.
    """
    decision = {
        "date": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "orchestrator": "Merlin",
        "walker_position": "NO_INPUT",
        "alfred_risk_status": "NO_INPUT",
        "merlin_thesis": "",  # Merlin fills this from own research
        "final_decision": "NO_GO",
        "trade_params": {},
        "reasoning": "",
        "alfred_veto": False,
        "veto_reason": "",
    }

    # Check for Alfred veto
    if alfred_data:
        decision["alfred_risk_status"] = alfred_data.get("go_no_go", "UNKNOWN")
        if alfred_data.get("veto", False):
            decision["alfred_veto"] = True
            decision["veto_reason"] = alfred_data.get("veto_reason", "Risk limits exceeded")
            decision["final_decision"] = "NO_GO — VETOED BY ALFRED"
            decision["reasoning"] = f"Alfred vetoed: {decision['veto_reason']}"
            return decision

    # No veto — Merlin makes the call
    if walker_data:
        decision["walker_position"] = walker_data.get("bias", "unknown")

        # If both TA and risk say GO, Merlin confirms
        walker_confidence = walker_data.get("confidence", 50)
        walker_orb = walker_data.get("orb_score", 50)
        alfred_risk = alfred_data.get("go_no_go", "NO_GO") if alfred_data else "NO_GO"

        # Decision matrix
        if walker_confidence >= 70 and walker_orb >= 60 and alfred_risk == "GO":
            decision["final_decision"] = "GO"
            bias = walker_data.get("bias", "neutral")
            direction = "LONG" if bias == "bullish" else "SHORT" if bias == "bearish" else "NONE"

            # Merlin adjusts parameters based on research context
            entry = walker_data.get("entry", "TBD")
            sl = walker_data.get("sl", "TBD")
            tp = walker_data.get("tp", "TBD")

            # Check if Merlin's research suggests wider SL (event risk)
            sl_adjustment = "Standard"
            lot_multiplier = 1.0

            if alfred_data:
                lot_size = alfred_data.get("recommended_lot_size", "TBD")
            else:
                lot_size = "TBD"

            decision["trade_params"] = {
                "direction": direction,
                "instrument": "NAS100",
                "entry": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "sl_adjustment": sl_adjustment,
                "lot_size": lot_size,
                "risk_pct": alfred_data.get("max_daily_loss_pct", 2.0) if alfred_data else 2.0,
                "session_window": "09:30-11:00 ET",
                "close_before": "13:30 ET (pre-news)",
            }

            decision["reasoning"] = (
                f"TA: {walker_data.get('reasoning', 'N/A')}\n"
                f"Risk: {'; '.join(alfred_data.get('factors', [])) if alfred_data else 'N/A'}\n"
                f"Merlin: {decision['merlin_thesis']}"
            )

        elif walker_confidence < 40 or walker_orb < 40:
            decision["final_decision"] = "NO_GO"
            decision["reasoning"] = f"TA confidence too low (conf={walker_confidence}, orb={walker_orb})"

        elif alfred_risk == "NO_GO":
            decision["final_decision"] = "NO_GO"
            decision["reasoning"] = "Risk parameters not met per Alfred's assessment"

        else:
            decision["final_decision"] = "NO_GO"
            decision["reasoning"] = "Mixed signals — standing aside"
    else:
        decision["reasoning"] = "No TA input received from Walker"

    return decision


def run_debate_rounds(walker_data: dict, alfred_data: dict, decision: dict) -> str:
    """
    Generate the debate transcript for the day.
    In practice, this would be coordinated via Discord messages.
    This function produces the structured transcript for the repo.
    """
    transcript = f"# Debate Transcript — {decision['date']}\n"
    transcript += f"# Orchestrator: Merlin 🧙\n\n"

    # Round 1
    transcript += "## Round 1: Opening Arguments\n\n"
    transcript += "### 🤖 Walker (Technical Analyst)\n"
    if walker_data:
        transcript += f"- **Bias**: {walker_data.get('bias', 'N/A')}\n"
        transcript += f"- **ICT Profile**: {walker_data.get('ict_profile', 'N/A')}\n"
        transcript += f"- **ORB Score**: {walker_data.get('orb_score', 'N/A')}/100\n"
        transcript += f"- **Confidence**: {walker_data.get('confidence', 'N/A')}/100\n"
        transcript += f"- **Reasoning**: {walker_data.get('reasoning', 'N/A')}\n"
    else:
        transcript += "- No input received\n"

    transcript += "\n### 🦇 Alfred (Risk Manager)\n"
    if alfred_data:
        transcript += f"- **Risk Status**: {alfred_data.get('go_no_go', 'N/A')}\n"
        for factor in alfred_data.get('factors', []):
            transcript += f"- {factor}\n"
    else:
        transcript += "- No input received\n"

    transcript += "\n### 🧙 Merlin (Orchestrator — Research Thesis)\n"
    transcript += f"- {decision['merlin_thesis']}\n"

    # Round 2
    transcript += "\n## Round 2: Rebuttals & Risk Check\n\n"
    if alfred_data and alfred_data.get("veto", False):
        transcript += f"🛑 **ALFRED VETO**: {alfred_data.get('veto_reason', 'N/A')}\n"
    else:
        transcript += "No veto from Alfred. Risk parameters within limits.\n"

    # Final
    transcript += f"\n## Final Decision by Merlin\n\n"
    transcript += f"**{decision['final_decision']}**\n\n"
    transcript += f"### Reasoning\n{decision['reasoning']}\n"

    if decision.get("trade_params"):
        transcript += "\n### Trade Parameters\n"
        for k, v in decision["trade_params"].items():
            transcript += f"- **{k}**: {v}\n"

    return transcript


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
    """Post message to Discord channel.
    Replace with actual Discord API call using Merlin's bot token.
    """
    # TODO: Implement with discord.py or HTTP API
    # bot_token = os.getenv("DISCORD_BOT_TOKEN")
    # channel_id = DISCORD_CHANNELS[channel]
    # requests.post(f"https://discord.com/api/channels/{channel_id}/messages",
    #               headers={"Authorization": f"Bot {bot_token}"},
    #               json={"content": message})
    print(f"[DISCORD #{channel}] {message}")


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

    # Generate debate transcript
    print("\n[5/7] Generating debate transcript...")
    transcript = run_debate_rounds(status["walker_data"], status["alfred_data"], decision)

    # Save everything
    print("\n[6/7] Saving to shared repo...")
    save_all(decision, transcript, date_str)

    # Post to Discord
    print("\n[7/7] Posting to Discord channels...")
    post_to_discord("final-call",
                    f"🎯 **FINAL CALL — {date_str}**\n"
                    f"Decision: {decision['final_decision']}\n"
                    f"Reasoning: {decision['reasoning']}")

    if decision.get("trade_params"):
        params = decision["trade_params"]
        post_to_discord("final-call",
                        f"📊 Trade Parameters:\n"
                        f"Direction: {params['direction']}\n"
                        f"Entry: {params['entry']}\n"
                        f"SL: {params['stop_loss']}\n"
                        f"TP: {params['take_profit']}\n"
                        f"Size: {params['lot_size']}\n"
                        f"Window: {params['session_window']}")

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
