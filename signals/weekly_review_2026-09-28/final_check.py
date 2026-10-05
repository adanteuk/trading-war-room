#!/usr/bin/env python3
"""Stability check: is Friday's NAS100 CFD close final? Check for post-close bars + Friday bar finality."""
import zmq, json, datetime

HOSTS = ["tcp://192.168.11.173:5555", "tcp://192.168.11.172:5555"]

ctx = zmq.Context()
sock = None
for host in HOSTS:
    try:
        s = ctx.socket(zmq.REQ)
        s.setsockopt(zmq.CONNECT_TIMEOUT, 4000)
        s.setsockopt(zmq.RCVTIMEO, 6000)
        s.linger = 0
        s.connect(host)
        s.send_json({"action": "ping"})
        resp = s.recv_json()
        print(f"PING OK via {host}: {resp}")
        sock = s
        break
    except Exception as e:
        print(f"PING FAIL {host}: {e}")

def get_rates(symbol, timeframe, count):
    sock.send_json({"action": "get_rates", "symbol": symbol, "timeframe": timeframe, "count": count})
    resp = sock.recv_json()
    return resp.get("data", resp.get("bars", []))

# M15 for the finest view of session end + last ticks
m15 = get_rates("NAS100", "M15", 60)
print("\n=== Last 12 M15 bars (UTC stamps) ===")
for b in m15[-12:]:
    print(f"  {b['time_utc']}  O={b['open']:.1f} H={b['high']:.1f} L={b['low']:.1f} C={b['close']:.1f} vol={b.get('volume')}")

d1 = get_rates("NAS100", "D1", 5)
print("\n=== Last 5 D1 bars (UTC stamps = session OPEN, +1 day = session date) ===")
for b in d1:
    print(f"  {b['time_utc']}  O={b['open']:.1f} H={b['high']:.1f} L={b['low']:.1f} C={b['close']:.1f}")

h4 = get_rates("NAS100", "H4", 10)
print("\n=== Last 10 H4 bars ===")
for b in h4:
    print(f"  {b['time_utc']}  O={b['open']:.1f} H={b['high']:.1f} L={b['low']:.1f} C={b['close']:.1f}")

# Final Friday session numbers
fri = d1[-1]
prev = d1[-2]
print(f"\nFriday session (stamp {fri['time_utc']}): O={fri['open']} H={fri['high']} L={fri['low']} C={fri['close']}")
print(f"Thursday close={prev['close']}  Fri c2c={fri['close']-prev['close']:+.1f} ({(fri['close']/prev['close']-1)*100:+.3f}%)")
print(f"Week c2c (Fri 9/25 close 30650.5 -> Fri final): {(fri['close']/30650.5-1)*100:+.2f}%")

# metadata
sock.send_json({"action": "get_rates", "symbol": "NAS100", "timeframe": "D1", "count": 2})
r = sock.recv_json()
for k in ["server_time_utc", "server_time_ny", "last_price", "last_date", "first_date"]:
    if k in r:
        print(f"meta {k}: {r[k]}")
