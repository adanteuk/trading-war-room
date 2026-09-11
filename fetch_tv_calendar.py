#!/usr/bin/env python3
"""
fetch_tv_calendar.py — v3 Phase 3 (TradingView MCP edition)

Fetches economic calendar events WITH exact UTC timestamps from TradingView's
internal calendar API (economic-calendar.tradingview.com/events), accessed via
the TradingView Desktop CDP bridge (tradingview-mcp). Replaces the investing.com
scraper whose extracted rows lack event times.

Flow:
  1. Inject fetch-JS into the TV page via `ui eval` (page has TV context)
  2. Chunk-retrieve the JSON via `ui eval` substring calls (~15KB each)
  3. Filter: tracked countries, importance==1 or rate/CPI/GDP keyword fallback
  4. Write ~/.hermes/trading-war-room/calendar/{HKT-date}.json with
     times_available: true

Requires: TradingView Desktop running with CDP port 9222 (launchd autostart
`local.tradingview-cdp.plist` normally keeps this alive).

Usage:
  python3 fetch_tv_calendar.py [--date YYYY-MM-DD (HKT)] [--force]
Cron: replaces the web_extract version — Hermes cron 60119eaf17af should run
  this script via terminal (no LLM web tools needed), or keep no_agent script mode.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

TV_CLI = ["node", str(Path.home() / "projects/tradingview-mcp/src/cli/index.js")]
CAL_DIR = Path.home() / ".hermes/trading-war-room/calendar"
CHUNK = 15000

TRACKED_COUNTRIES = {"US", "EU", "DE", "FR", "GB", "JP", "HK", "CN"}
COUNTRY_TO_CCY = {"US": "USD", "EU": "EUR", "DE": "EUR", "FR": "EUR",
                  "GB": "GBP", "JP": "JPY", "HK": "HKD", "CN": "CNY"}
KEYWORD_FALLBACK = re.compile(
    r"(interest rate|cpi|inflation rate|nonfarm|non-farm|payroll|fomc|"
    r"gdp monthly|producer price inflation|core inflation)", re.I)


def tv_eval(expr: str, timeout: int = 40) -> str:
    """Run ui eval, return the JSON-parsed result string."""
    r = subprocess.run(TV_CLI + ["ui", "eval", "--expression", expr],
                       capture_output=True, text=True, timeout=timeout)
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"tv eval bad output: {r.stdout[:200]} {r.stderr[:200]}") from e
    if not out.get("success"):
        raise RuntimeError(f"tv eval failed: {out.get('error')}")
    return out.get("result", "")


def inject_fetch(from_iso: str, to_iso: str) -> str:
    """Fire the calendar fetch inside the TV page; returns the URL."""
    js = f"""(function(){{
  var base = window.ECONOMIC_CALENDAR_URL || "https://economic-calendar.tradingview.com/";
  var url = base + "events?from=" + encodeURIComponent("{from_iso}") + "&to=" + encodeURIComponent("{to_iso}");
  window.__calFull = "pending";
  fetch(url).then(function(r){{ return r.text(); }})
    .then(function(t){{ window.__calFull = t; }})
    .catch(function(e){{ window.__calFull = "ERR:" + e.message; }});
  return url;
}})()"""
    return tv_eval(js)


def wait_and_pull(max_wait_s: int = 20) -> str:
    """Poll until the fetch lands, then chunk-retrieve the full JSON."""
    import time
    deadline = time.time() + max_wait_s
    while time.time() < deadline:
        head = tv_eval('(window.__calFull||"pending").substring(0,30)')
        if head.startswith("ERR:"):
            raise RuntimeError(f"TV calendar fetch error: {head}")
        if not head.startswith("pending"):
            break
        time.sleep(2)
    else:
        raise RuntimeError("TV calendar fetch timed out")

    total = int(tv_eval('(window.__calFull||"").length'))
    chunks = []
    for start in range(0, total, CHUNK):
        chunks.append(tv_eval(f'window.__calFull.substring({start}, {start + CHUNK})'))
    raw = "".join(chunks)
    if len(raw) != total:
        raise RuntimeError(f"chunk reassembly mismatch: {len(raw)} != {total}")
    return raw


def normalize(events: list) -> list:
    kept = []
    for e in events:
        c = e.get("country")
        if c not in TRACKED_COUNTRIES:
            continue
        name = (e.get("indicator") or e.get("title") or "")[:80]
        if e.get("importance") == 1 or KEYWORD_FALLBACK.search(name):
            kept.append({
                "time_utc": e["date"],          # exact ISO timestamp
                "currency": COUNTRY_TO_CCY[c],
                "impact": "high",
                "name": name,
                "importance": e.get("importance"),
                "country": c,
            })
    return sorted(kept, key=lambda x: x["time_utc"])


def cache_fresh(path: Path, max_age_h: float = 10.0) -> bool:
    if not path.exists():
        return False
    return (datetime.now().timestamp() - path.stat().st_mtime) / 3600 < max_age_h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="HKT date YYYY-MM-DD (default today)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    now_hk = datetime.now(timezone(timedelta(hours=8)))
    hkt_date = args.date or now_hk.strftime("%Y-%m-%d")
    CAL_DIR.mkdir(parents=True, exist_ok=True)
    out = CAL_DIR / f"{hkt_date}.json"

    if not args.force and cache_fresh(out):
        with open(out) as f:
            print(f"Cache fresh: {out} ({json.load(f).get('event_count')} events)")
        sys.exit(0)

    hkt_dt = datetime.strptime(hkt_date, "%Y-%m-%d")
    # HKT day spans UTC prev-day 16:00 → HKT-day 15:59; use UTC prev day 00:00 → HKT day 23:59 UTC for full coverage
    from_dt = hkt_dt - timedelta(days=1)
    to_dt = hkt_dt
    from_iso = from_dt.strftime("%Y-%m-%dT00:00:00Z")
    to_iso = to_dt.strftime("%Y-%m-%dT23:59:59Z")

    url = inject_fetch(from_iso, to_iso)
    raw = wait_and_pull()
    data = json.loads(raw)
    if data.get("status") != "ok":
        print(f"❌ TV calendar API error: {raw[:200]}")
        sys.exit(1)

    kept = normalize(data.get("result", []))
    result = {
        "hkt_date": hkt_date,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sources": [f"tradingview-internal:{url[:80]}"],
        "times_available": True,
        "event_count": len(kept),
        "events": kept,
    }
    with open(out, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    if not kept:
        print(f"⚠️ {out}: 0 matching events (quiet day or filter gap)")
        sys.exit(0)
    print(f"✅ {out}: {len(kept)} high-impact tracked events with exact UTC times")
    for e in kept[:6]:
        print(f"   {e['time_utc']} {e['currency']} {e['name'][:50]}")


if __name__ == "__main__":
    main()
