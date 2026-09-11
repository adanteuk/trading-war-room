# Phase 4 Installation Prompt for Carson

**Send this to Carson via his Hermes session.**

---

## Context

The v3 trading pipeline is ready for Phase 4: Carson's order execution system. All Mac-side work is complete (Phases 1-3). Merlin has built the 9-check order handler and committed it to the shared repo.

Your job: Install the order handler on your Windows machine, generate the authentication key, test all 9 checks, and confirm end-to-end functionality.

**Time estimate**: 30-45 minutes  
**Risk level**: LOW (paper mode, no real trades yet)

---

## What You're Installing

### 1. Order Handler (`carson_order_handler.py`)
A Python module that implements 9 security checks before any order executes:
1. **Auth key** - Validates Merlin's request signature
2. **IP whitelist** - Only accepts from Merlin's Mac (192.168.11.173)
3. **Decision verification** - Confirms the decision_id exists and is GO
4. **SL present** - Rejects orders without stop loss
5. **Risk ≤ 1%** - Validates position size vs account equity
6. **Lot ≤ 2.0** - Hard cap on position size
7. **Symbol verified** - Only allows pre-approved symbols
8. **Expiry check** - Rejects stale orders
9. **MT5 execution** - Sends order to MT5 terminal

All checks are deterministic (no LLM judgment). Any failure = order rejected and logged.

### 2. Authentication Key (`.order_key`)
A 32-character hex string that Merlin uses to sign requests. You'll generate this and store it at `C:\Users\hkvid\zmq\.order_key`.

### 3. Execution Logging
Successful orders → `signals/{date}/execution_log.json`  
Rejected orders → `rejected_orders.log`

---

## Installation Steps

### Step 1: Pull Latest Code
```powershell
cd C:\Users\hkvid\trading-war-room
git pull origin main
```

Verify these files exist:
- `carson_order_handler.py`
- `carson_install_guide.md`

### Step 2: Generate Order Key
```powershell
cd C:\Users\hkvid\zmq
python -c "import secrets; key=secrets.token_hex(16); open('.order_key','w').write(key); print(f'Generated: {key}')"
```

**⚠️ Critical**: Add `.order_key` to `.gitignore` if not already there:
```powershell
cd C:\Users\hkvid\trading-war-room
echo ".order_key" >> .gitignore
git add .gitignore
git commit -m "Add .order_key to gitignore"
```

### Step 3: Test Handler (No MT5)
```powershell
cd C:\Users\hkvid\zmq
python carson_order_handler.py
```

Expected: `✅ All 9 checks passed (unit test mode)`

If any check fails, stop and review the error.

### Step 4: Patch MT5_server.py

Open `C:\Users\hkvid\zmq\MT5_server.py` and make these changes:

#### 4a. Add import (top of file, after existing imports)
```python
import sys
sys.path.insert(0, r"C:\Users\hkvid\trading-war-room")
import carson_order_handler
```

#### 4b. Add order action handler (in the `handle_command` function, after the `get_positions` case)
```python
elif action == "order":
    # Extract client IP from ZMQ socket
    client_ip = socket.getsockopt(zmq.LAST_ENDPOINT).decode().split("//")[-1].split(":")[0]
    
    # Run the 9-check handler
    result = carson_order_handler.handle_order(payload, client_ip, mt5)
    
    # Log to execution_log.json
    carson_order_handler.log_execution(payload, result)
    
    return result
```

#### 4c. Restart the server
```powershell
# Stop existing server
taskkill /F /IM python.exe /FI "WINDOWTITLE eq MT5_server"

# Start new server
cd C:\Users\hkvid\zmq
python MT5_server.py
```

### Step 5: Verify Security Hardening

Test that the IP whitelist works (send from a blocked IP):
```python
import zmq
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://192.168.11.173:5555")
socket.send_json({
    "action": "order",
    "auth": "test",
    "decision_id": "2026-09-14-NAS100-1",
    "symbol": "NAS100",
    "direction": "long",
    "entry": 26700.0,
    "sl": 26665.0,
    "tp": 26805.0,
    "lot": 1.0,
    "valid_until": "2026-09-14T20:00:00Z"
})
response = socket.recv_json()
print(response)
```

Expected: `{"status": "error", "msg": "IP_NOT_ALLOWED: ..."}`

### Step 6: End-to-End Test (Paper Mode)

Create a test decision:
```python
import json
from pathlib import Path

decision = {
    "decision_id": "2026-09-14-NAS100-1",
    "final_decision": "GO",
    "trade_params": {
        "symbol": "NAS100",
        "direction": "long",
        "entry": 26700.0,
        "stop_loss": 26665.0,
        "take_profit": 26805.0
    }
}

Path(r"C:\Users\hkvid\trading-war-room\decisions").mkdir(exist_ok=True)
with open(r"C:\Users\hkvid\trading-war-room\decisions\2026-09-14.json", "w") as f:
    json.dump(decision, f, indent=2)
```

Send a valid order:
```python
import zmq
from datetime import datetime, timedelta, timezone

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://192.168.11.173:5555")

with open(r"C:\Users\hkvid\zmq\.order_key") as f:
    auth_key = f.read().strip()

payload = {
    "action": "order",
    "auth": auth_key,
    "decision_id": "2026-09-14-NAS100-1",
    "symbol": "NAS100",
    "direction": "long",
    "entry": 26700.0,
    "sl": 26665.0,
    "tp": 26805.0,
    "lot": 1.0,
    "valid_until": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
}

socket.send_json(payload)
response = socket.recv_json()
print(response)
```

Expected:
```json
{
  "status": "ok",
  "ticket": 123456789,
  "fill_price": 26700.0,
  "slippage": 0.0,
  "volume": 1.0
}
```

Verify execution log:
```powershell
type C:\Users\hkvid\trading-war-room\signals\2026-09-14\execution_log.json
```

### Step 7: Verify Rejection Logging

Send an invalid order (missing SL):
```python
payload["action"] = "order"
del payload["sl"]
socket.send_json(payload)
response = socket.recv_json()
print(response)  # Should be SL_MISSING error
```

Verify rejection log:
```powershell
type C:\Users\hkvid\trading-war-room\rejected_orders.log
```

### Step 8: Notify Merlin

Once all tests pass:
```powershell
cd C:\Users\hkvid\trading-war-room
git add .
git commit -m "Carson: Phase 4 order handler installed and tested"
git push
```

Then message me (AC):
> Carson Phase 4 complete. Order handler installed, all 9 checks verified, end-to-end test passed. Ready for paper trading.

---

## Troubleshooting

### `ORDER_KEY_MISSING`
- File not created: `dir C:\Users\hkvid\zmq\.order_key`
- Wrong path: Check `carson_order_handler.py` line 14

### `DECISION_FILE_MISSING`
- Repo not synced: `git pull`
- Wrong decision_id format: Must be `YYYY-MM-DD-SYMBOL-N` (e.g., `2026-09-14-NAS100-1`)

### `RISK_EXCEEDS_1PCT`
- Lot too large for SL distance
- Formula: `lot * (entry - sl) * 10 / equity <= 0.01`
- Example: 1.0 lot * 35 pts * $10/pt / $100,000 equity = 0.35% ✅

### `SYMBOL_NOT_VERIFIED`
- Only these symbols allowed: NAS100, US500, XAUUSD, EURUSD, GBPUSD, USDJPY
- To add more: Edit `VERIFIED_SYMBOLS` in `carson_order_handler.py` line 16

---

## Security Checklist

Before notifying Merlin, verify:
- [ ] `.order_key` file created (32-char hex)
- [ ] `.order_key` in `.gitignore`
- [ ] IP whitelist working (test with blocked IP)
- [ ] All 9 checks tested and passing
- [ ] Execution log writing correctly
- [ ] Rejection log writing correctly
- [ ] MT5_server.py patched and restarted
- [ ] End-to-end test passed (paper mode)

---

## Questions?

If anything is unclear or you hit an error, message me (AC) immediately. Don't guess — the security model depends on these checks working correctly.

**Reference docs**:
- Full design: `references/five-stage-pipeline-v3.md`
- Install guide: `carson_install_guide.md`
- Handler code: `carson_order_handler.py`

---

## What Happens Next

After you confirm Phase 4 is complete:
1. I'll update Merlin's orchestrator to send real order requests (currently paper mode)
2. We'll run 2-4 weeks of paper trading to validate gate precision
3. Once validated, we'll flip `PAPER_MODE = False` for live trading

**You're the last line of defense.** These 9 checks are what prevent a hallucinating LLM from blowing up the account. Test them thoroughly.
