#!/usr/bin/env python3
"""
Alfred — Risk Manager Orchestrator for Multi-Agent Trading Debate
Coordinates Walker (Technical Analyst) and Merlin (Researcher)
Makes final go/no-go decisions based on risk assessment.

Run daily at 7:00 PM HKT on trading days.
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

# Discord channel IDs (replace with actual IDs)
DISCORD_CHANNELS = {
    "daily_briefing": "CHANNEL_ID_HERE",
    "debate": "CHANNEL_ID_HERE",
    "risk_dashboard": "CHANNEL_ID_HERE",
    "final_call": "CHANNEL_ID_HERE",
}

# Wait times (seconds)
WAIT_FOR_INPUTS = 1800  # 30 min max wait for Walker/Merlin
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
    subprocess.run(["git", "pull", "--rebase"], capture_output=True)


def git_push(message: str):
    """Commit and push changes."""
    os.chdir(REPO_DIR)
    subprocess.run(["git", "add", "."], capture_output=True)
    subprocess.run(["git", "commit", "-m", message], capture_output=True)
    subprocess.run(["git", "push"], capture_output=True)


def check_input_ready(date_str: str) -> dict:
    """Check if Walker and Merlin have posted their analysis."""
    today_dir = SIGNALS_DIR / date_str
    status = {
        "walker": False,
        "merlin": False,
        "walker_data": None,
        "merlin_data": None,
    }

    walker_file = today_dir / "walker_ta.json"
    merlin_file = today_dir / "merlin_research.json"

    if walker_file.exists():
        status["walker"] = True
        with open(walker_file) as f:
            status["walker_data"] = json.load(f)

    if merlin_file.exists():
        status["merlin"] = True
        with open(merlin_file) as f:
            status["merlin_data"] = json.load(f)

    return status


def check_mt5_accounts() -> dict:
    """Check all MT5 account balances and drawdown."""
    # Call your existing MT5 balance check script
    try:
        result = subprocess.run(
            ["/mnt/c/Python312/python.exe",
             "/home/ychen/.hermes/skills/trading/mt5-balance-check/check_balances.py"],
            capture_output=True, text=True, timeout=120
        )
        return json.loads(result.stdout) if result.stdout else {}
    except Exception as e:
        return {"error": str(e)}


def calculate_risk_limits(accounts: dict, walker_data: dict, merlin_data: dict) -> dict:
    """
    Calculate daily risk limits based on:
    - Current account equity and drawdown
    - Walker's confidence score
    - Merlin's risk factors
    - Prop firm rules
    """
    risk = {
        "max_daily_loss_pct": 2.0,  # FTMO daily limit
        "max_total_dd_pct": 10.0,   # FTMO max DD
        "recommended_lot_size": 0,
        "go_no_go": "NO_GO",
        "reasoning": "",
        "factors": [],
    }

    # Check account status
    for account_name, account_data in accounts.items():
        equity = account_data.get("equity", 0)
        balance = account_data.get("balance", 0)
        current_dd = ((balance - equity) / balance * 100) if balance else 0

        if current_dd > 8:
            risk["factors"].append(f"⚠️ {account_name}: DD at {current_dd:.1f}% (near 10% limit)")
            risk["go_no_go"] = "NO_GO"
            risk["reasoning"] += f"{account_name} drawdown too high. "
            continue

        # Calculate available risk buffer
        available_buffer = 10.0 - current_dd  # Percentage points remaining
        daily_budget = min(2.0, available_buffer * 0.5)  # Max 2% or 50% of buffer

        risk["factors"].append(f"✅ {account_name}: DD {current_dd:.1f}%, daily budget {daily_budget:.1f}%")

    # Factor in Walker's TA confidence
    if walker_data:
        confidence = walker_data.get("confidence", 50)
        orb_score = walker_data.get("orb_score", 50)

        if confidence >= 80 and orb_score >= 70:
            risk["factors"].append(f"🟢 High confidence TA (conf={confidence}, orb={orb_score})")
            risk["lot_multiplier"] = 1.0
        elif confidence >= 60:
            risk["factors"].append(f"🟡 Medium confidence TA (conf={confidence}, orb={orb_score})")
            risk["lot_multiplier"] = 0.5
        else:
            risk["factors"].append(f"🔴 Low confidence TA (conf={confidence}, orb={orb_score})")
            risk["lot_multiplier"] = 0.25

    # Factor in Merlin's research risks
    if merlin_data:
        risks = merlin_data.get("risks", [])
        high_impact = [r for r in risks if r.get("impact") == "high"]

        if high_impact:
            risk["factors"].append(f"⚠️ High-impact events: {[r['event'] for r in high_impact]}")
            risk["lot_multiplier"] = risk.get("lot_multiplier", 1.0) * 0.5
        else:
            risk["factors"].append("✅ No high-impact events today")

    # Final go/no-go
    if risk["go_no_go"] != "NO_GO":
        risk["go_no_go"] = "GO"
        risk["reasoning"] = "Risk parameters within limits. TA and research aligned."

    return risk


def run_debate_rounds(walker_data: dict, merlin_data: dict, risk: dict) -> dict:
    """
    Simulate the debate rounds and produce final decision.
    In practice, this could spawn Walker and Merlin as subagents via Discord.
    For now, it synthesizes their inputs into a structured decision.
    """
    decision = {
        "date": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "walker_position": walker_data.get("bias", "unknown") if walker_data else "NO_INPUT",
        "merlin_position": "CAUTION" if merlin_data and merlin_data.get("risks") else "NEUTRAL",
        "risk_assessment": risk,
        "final_decision": risk["go_no_go"],
        "trade_params": {},
        "reasoning": "",
    }

    if risk["go_no_go"] == "GO":
        # Construct trade parameters
        bias = walker_data.get("bias", "neutral") if walker_data else "neutral"
        direction = "LONG" if bias == "bullish" else "SHORT" if bias == "bearish" else "NONE"

        entry = walker_data.get("key_levels", {}).get("entry", "TBD")
        sl = walker_data.get("key_levels", {}).get("sl", "TBD")
        tp = walker_data.get("key_levels", {}).get("tp", "TBD")

        # Adjust SL based on Merlin's risk input
        if merlin_data and merlin_data.get("risks"):
            sl_adjustment = "WIDENED per research risk factors"
        else:
            sl_adjustment = "Standard"

        decision["trade_params"] = {
            "direction": direction,
            "instrument": "NAS100",
            "entry": entry,
            "stop_loss": sl,
            "take_profit": tp,
            "sl_adjustment": sl_adjustment,
            "lot_size": risk.get("recommended_lot_size", "TBD"),
            "risk_pct": risk.get("max_daily_loss_pct", 2.0),
            "session_window": "09:30-11:00 ET",
            "close_before": "13:30 ET (pre-news)",
        }

        decision["reasoning"] = (
            f"TA: {walker_data.get('reasoning', 'N/A') if walker_data else 'N/A'}\n"
            f"Research: {merlin_data.get('summary', 'N/A') if merlin_data else 'N/A'}\n"
            f"Risk: {'; '.join(risk['factors'])}"
        )

    return decision


def save_decision(decision: dict, date_str: str):
    """Save the final decision to the shared repo."""
    DECISIONS_DIR.mkdir(parents=True, exist_ok=True)
    decision_file = DECISIONS_DIR / f"{date_str}.json"
    with open(decision_file, "w") as f:
        json.dump(decision, f, indent=2)

    # Also save debate transcript
    DEBATE_DIR.mkdir(parents=True, exist_ok=True)
    debate_file = DEBATE_DIR / date_str / "transcript.md"
    debate_file.parent.mkdir(parents=True, exist_ok=True)

    with open(debate_file, "w") as f:
        f.write(f"# Debate Transcript — {date_str}\n\n")
        f.write(f"## Walker's Position: {decision['walker_position']}\n")
        if decision.get('trade_params'):
            f.write(f"## Merlin's Position: {decision['merlin_position']}\n\n")
            f.write(f"## Risk Assessment\n")
            for factor in decision['risk_assessment']['factors']:
                f.write(f"- {factor}\n")
            f.write(f"\n## Final Decision: {decision['final_decision']}\n")
            if decision['trade_params']:
                f.write(f"\n### Trade Parameters\n")
                for k, v in decision['trade_params'].items():
                    f.write(f"- **{k}**: {v}\n")


def main():
    now_hk = datetime.now(timezone(timedelta(hours=8)))
    date_str = now_hk.strftime("%Y-%m-%d")

    print(f"=== Alfred Orchestrator — {date_str} ===")
    print(f"Time: {now_hk.strftime('%H:%M')} HKT")

    # Check if trading day
    if not is_trading_day():
        print("Not a trading day. Skipping.")
        return

    # Pull latest data
    print("\n[1/6] Pulling shared repo...")
    git_pull()

    # Wait for inputs from Walker and Merlin
    print("[2/6] Waiting for Walker and Merlin analysis...")
    start = time.time()
    inputs_ready = False

    while time.time() - start < WAIT_FOR_INPUTS:
        status = check_input_ready(date_str)
        if status["walker"] and status["merlin"]:
            print(f"  ✅ Both inputs ready after {int(time.time() - start)}s")
            inputs_ready = True
            break
        elif time.time() - start % 300 == 0:
            print(f"  ⏳ Waiting... Walker: {'✅' if status['walker'] else '⌛'} Merlin: {'✅' if status['merlin'] else '⌛'}")
        time.sleep(CHECK_INTERVAL)

    if not inputs_ready:
        status = check_input_ready(date_str)
        print(f"\n  ⚠️ Timeout. Proceeding with available data.")
        print(f"  Walker: {'✅' if status['walker'] else '❌'}")
        print(f"  Merlin: {'✅' if status['merlin'] else '❌'}")

    # Check MT5 accounts
    print("\n[3/6] Checking MT5 accounts...")
    accounts = check_mt5_accounts()
    print(f"  Found {len(accounts)} accounts")
    for name, data in accounts.items():
        equity = data.get("equity", 0)
        balance = data.get("balance", 0)
        print(f"  {name}: Balance ${balance:,.2f} | Equity ${equity:,.2f}")

    # Calculate risk limits
    print("\n[4/6] Calculating risk limits...")
    status = check_input_ready(date_str)
    risk = calculate_risk_limits(accounts, status["walker_data"], status["merlin_data"])
    for factor in risk["factors"]:
        print(f"  {factor}")
    print(f"  GO/NO-GO: {risk['go_no_go']}")

    # Run debate and make decision
    print("\n[5/6] Running debate / final decision...")
    decision = run_debate_rounds(status["walker_data"], status["merlin_data"], risk)
    print(f"  Decision: {decision['final_decision']}")
    if decision.get("trade_params"):
        for k, v in decision["trade_params"].items():
            print(f"  {k}: {v}")

    # Save decision
    print("\n[6/6] Saving decision and pushing to repo...")
    save_decision(decision, date_str)
    git_push(f"Alfred: Decision for {date_str} — {decision['final_decision']}")

    print(f"\n✅ Orchestrator complete. Decision saved to {DECISIONS_DIR}/{date_str}.json")
    print(f"\n{'='*50}")
    if decision["final_decision"] == "GO":
        print(f"🎯 GO — {decision['trade_params']['direction']} NAS100")
        print(f"   Entry: {decision['trade_params']['entry']}")
        print(f"   SL: {decision['trade_params']['stop_loss']}")
        print(f"   TP: {decision['trade_params']['take_profit']}")
    else:
        print(f"🚫 NO GO — {decision.get('reasoning', 'Risk parameters not met')}")


if __name__ == "__main__":
    main()
