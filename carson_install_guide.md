# Carson Phase 4 Installation Guide

**Purpose**: Install the v3 order execution system on Carson's Windows machine.
**Prerequisites**: Carson's MT5 ZMQ server already running (v2.4 with pagination).
**Estimated time**: 30-45 minutes.

---

## Step 1: Pull Latest Code

```bash
cd C:\Users\hkvid\trading-war-room
git pull origin main
```

Verify you have these new files:
- `carson_order_handler.py` (the 9-check order handler)
- `carson_install_guide.md` (this file)

---

## Step 2: Generate Order Key

The order key authenticates Merlin's requests. Generate a random 32-char hex string:

```powershell
# PowerShell
$key = -join ((48..57) + (97..102) | Get-Random -Count 32 | % {[char]$_})
Set-Content -Path "C:\Users\hkvid\zmq\.order_key" -Value $key -NoNewline
Write-Host "Generated key: $key"
```

Or use Python:
```python
import secrets
key = secrets.token_hex(16)  # 32 hex chars
with open(r"C:\Users\hkvid\zmq\.order_key", "w") as f:
    f.write(key)
print(f"Generated key: {key}")
```

**⚠️ Security**: This key file must NOT be committed to git. Verify `.gitignore` includes `.order_key`.

---

## Step 3: Test the Handler (No MT5)

Run the unit tests to verify all 9 checks work:

```bash
cd C:\Users\hkvid\zmq
python carson_order_handler.py
```

Expected output:
```
✅ All 9 checks passed (unit test mode)
```

If any check fails, review the error message. Common issues:
- `ORDER_KEY_MISSING`: Key file not created or wrong path
- `DECISION_FILE_MISSING`: Repo not synced or decision_id format wrong

---

## Step 4: Patch MT5_server.py

Add the `order` action to your existing ZMQ server. Open `C:\Users\hkvid\zmq\MT5_server.py` and add:

### 4a. Import the handler (top of file)

```python
import sys
sys.path.insert(0, r"C:\Users\hkvid\trading-war-room")
import carson_order_handler
```

### 4b. Add the order action handler (in the `handle_command` function)

Find the `handle_command` function and add this case:

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

### 4c. Restart the server

```bash
# Stop the existing server
taskkill /F /IM python.exe /FI "WINDOWTITLE eq MT5_server"

# Start the new server
cd C:\Users\hkvid\zmq
python MT5_server.py
```

---

## Step 5: Verify Security Hardening

### 5a. Check IP whitelist

The handler only accepts requests from Merlin's Mac IPs:
- `192.168.11.173`
- `192.168.11.211`

Test with a blocked IP:
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
print(response)  # Should be IP_NOT_ALLOWED error
```

### 5b. Check order key authentication

Test with wrong key:
```python
socket.send_json({
    "action": "order",
    "auth": "wrong-key",
    # ... rest of payload
})
response = socket.recv_json()
print(response)  # Should be AUTH_FAILED error
```

---

## Step 6: Test End-to-End (Paper Mode)

Create a test decision file:

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

Send a valid order request:
```python
import zmq
from datetime import datetime, timedelta, timezone

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://192.168.11.173:5555")

# Read the order key
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

Expected response:
```json
{
  "status": "ok",
  "ticket": 123456789,
  "fill_price": 26700.0,
  "slippage": 0.0,
  "volume": 1.0
}
```

Check the execution log:
```bash
type C:\Users\hkvid\trading-war-room\signals\2026-09-14\execution_log.json
```

---

## Step 7: Verify Rejection Logging

Send an invalid order (e.g., missing SL):
```python
payload["action"] = "order"
del payload["sl"]  # Remove stop loss
socket.send_json(payload)
response = socket.recv_json()
print(response)  # Should be SL_MISSING error
```

Check the rejection log:
```bash
type C:\Users\hkvid\trading-war-room\rejected_orders.log
```

---

## Step 8: Notify Merlin

Once all tests pass, notify Merlin (Mac) that Carson is ready:

```bash
cd C:\Users\hkvid\trading-war-room
git add .
git commit -m "Carson: Phase 4 order handler installed and tested"
git push
```

Then message Merlin:
> Carson Phase 4 complete. Order handler installed, all 9 checks verified, end-to-end test passed. Ready for paper trading.

---

## Troubleshooting

### Issue: `ORDER_KEY_MISSING`
- Check file exists: `dir C:\Users\hkvid\zmq\.order_key`
- Check permissions: file must be readable by the Python process

### Issue: `DECISION_FILE_MISSING`
- Verify repo is synced: `git pull`
- Check decision_id format: must be `YYYY-MM-DD-SYMBOL-N` (e.g., `2026-09-14-NAS100-1`)

### Issue: `RISK_EXCEEDS_1PCT`
- Lot size too large for the SL distance
- Formula: `lot * (entry - sl) * 10 / equity <= 0.01`
- Example: 1.0 lot * 35 pts * $10/pt / $100,000 equity = 0.35% ✅

### Issue: `SYMBOL_NOT_VERIFIED`
- Only these symbols are allowed: NAS100, US500, XAUUSD, EURUSD, GBPUSD, USDJPY
- To add more, edit `VERIFIED_SYMBOLS` in `carson_order_handler.py`

---

## Security Checklist

- [ ] `.order_key` file created with 32-char hex string
- [ ] `.order_key` in `.gitignore`
- [ ] IP whitelist configured (192.168.11.173, 192.168.11.211)
- [ ] All 9 checks tested and passing
- [ ] Execution log writing to `signals/{date}/execution_log.json`
- [ ] Rejection log writing to `rejected_orders.log`
- [ ] MT5_server.py patched and restarted
- [ ] End-to-end test passed (paper mode)

---

## Next Steps

After Carson confirms Phase 4 is complete:
1. Merlin will update the orchestrator to send real order requests (currently paper mode)
2. We'll run 2-4 weeks of paper trading to validate gate precision
3. Once validated, we'll flip `PAPER_MODE = False` in the orchestrator for live trading

**Questions?** Message Merlin or check the v3 design doc: `references/five-stage-pipeline-v3.md`
