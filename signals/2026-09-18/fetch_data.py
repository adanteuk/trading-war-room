#!/usr/bin/env python3
"""Fetch NAS100 (+US500 for SMT) data from Carson MT5 bridge for Walker TA analysis — 2026-09-18."""
import zmq, json, sys, datetime, os

HOSTS = ["tcp://192.168.11.173:5555", "tcp://192.168.11.172:5555"]
OUT_DIR = "/Users/ychen/.hermes/trading-war-room/signals/2026-09-18"
os.makedirs(OUT_DIR, exist_ok=True)

def try_ping():
    for host in HOSTS:
        try:
            ctx = zmq.Context()
            sock = ctx.socket(zmq.REQ)
            sock.setsockopt(zmq.CONNECT_TIMEOUT, 4000)
            sock.setsockopt(zmq.RCVTIMEO, 6000)
            sock.setsockopt(zmq.SNDTIMEO, 6000)
            sock.linger = 0
            sock.connect(host)
            sock.send_json({"action": "ping"})
            resp = sock.recv_json()
            print(f"PING OK via {host}: {resp}")
            return host, ctx, sock
        except Exception as e:
            print(f"PING FAIL {host}: {e}")
    return None, None, None

def get_rates(sock, symbol, timeframe, count):
    sock.send_json({"action": "get_rates", "symbol": symbol, "timeframe": timeframe, "count": count})
    resp = sock.recv_json()
    bars = resp.get("data", resp.get("bars", []))
    return resp, bars

def main():
    host, ctx, sock = try_ping()
    if not host:
        print("RESULT: CARSON_UNREACHABLE")
        sys.exit(0)
    datasets = {
        "NAS100_D1": ("NAS100", "D1", 200),
        "NAS100_H4": ("NAS100", "H4", 500),
        "NAS100_M15": ("NAS100", "M15", 200),
        "US500_D1": ("US500", "D1", 60),
        "US500_H4": ("US500", "H4", 200),
    }
    summary = {}
    for key, (sym, tf, cnt) in datasets.items():
        try:
            resp, bars = get_rates(sock, sym, tf, cnt)
            status = resp.get("status")
            if status != "ok" or not bars:
                print(f"{key}: status={status} msg={resp.get('msg')} bars={len(bars) if bars else 0}")
                summary[key] = {"ok": False, "msg": resp.get("msg", "")}
            else:
                out = os.path.join(OUT_DIR, f"raw_{key}.json")
                with open(out, "w") as f:
                    json.dump(bars, f)
                last = bars[-1]
                summary[key] = {"ok": True, "n": len(bars), "last_close": last.get("close"), "last_bar": last.get("time_utc") or last.get("time_epoch")}
                print(f"{key}: OK {len(bars)} bars, last close={last.get('close')}, last_bar={last.get('time_utc') or last.get('time_epoch')}")
        except Exception as e:
            print(f"{key}: ERROR {e}")
            summary[key] = {"ok": False, "err": str(e)}
    with open(os.path.join(OUT_DIR, "fetch_summary.json"), "w") as f:
        json.dump({"host": host, "summary": summary, "fetched_at_utc": datetime.datetime.utcnow().isoformat()}, f, indent=2)
    all_ok = all(v.get("ok") for v in summary.values())
    print("RESULT:", "ALL_OK" if all_ok else "PARTIAL")

if __name__ == "__main__":
    main()
