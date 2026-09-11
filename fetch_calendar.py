#!/usr/bin/env python3
"""
fetch_calendar.py — v3 Phase 3: economic calendar feed for compliance_gate.py

Fetches the day's high-impact economic events and writes normalized JSON:
  ~/.hermes/trading-war-room/calendar/YYYY-MM-DD.json (HKT date)
Format: [{"time_utc": "...", "currency": "USD", "impact": "high", "name": "..."}]

Strategy (fallback ladder — never silent, source recorded in output):
  1. investing.com economic calendar via web_extract stack (curl gets 403)
  2. Cache reuse: if today's file exists and is fresh (<12h), keep it
  3. HKT date spans two UTC days — fetch both (HKT morning = UTC prev day)

KNOWN LIMITATION (2026-09-14): web_extract drops the per-row time cells, so
events carry names/dates but NOT times. The ±30min news blackout needs exact
times — until a timezone-preserving source is wired (Phase 3 continuation),
compliance_gate treats a time-less calendar as "names only" and logs a
warning instead of enforcing blackout. Do NOT rely on this for pre-news
exits yet.

Usage:
  python3 fetch_calendar.py [--date YYYY-MM-DD] [--force]
Run: cron 06:30 HKT + 17:30 HKT
"""
import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CAL_DIR = Path.home() / ".hermes/trading-war-room/calendar"

# investing.com 2-letter country → currency tracked by compliance gate
CURRENCY_MAP = {"US": "USD", "EU": "EUR", "DE": "EUR", "FR": "EUR", "ES": "EUR",
                "IT": "EUR", "GB": "GBP", "JP": "JPY", "HK": "HKD", "CN": "CNY"}

# Event names that qualify as high-impact (match from start of clean name)
HIGH_IMPACT_NAME = re.compile(
    r"^(cpi \(m|cpi \(y|core cpi|fomc|fomc statement|federal funds|nonfarm|non-farm|"
    r"initial jobless|unemployment claims|unemployment rate|"
    r"interest rate decision|rate decision|gdp \(m|gdp \(y|ppi \(m|ppi \(y|core ppi|"
    r"ism manufacturing pmi|ism services pmi|ecb (monetary|press|rate))", re.I)


def fetch_day_via_webextract(utc_day: datetime) -> list | None:
    """Returns list of high-impact tracked events, or None on fetch failure."""
    from hermes_tools import web_extract
    url = f"https://www.investing.com/economic-calendar/?day={utc_day.strftime('%Y-%m-%d')}"
    try:
        r = web_extract([url], char_limit=50000)
        content = r["results"][0].get("content", "")
    except Exception:
        return None
    if not content:
        return None
    events = []
    # Row: | CC |  | CC | [Name](url) Act: ... (empty cell between the two codes)
    row_pat = re.compile(
        r"\|\s*([A-Z]{2})\s*\|[^|]*\|\s*([A-Z]{2})\s*\|\s*\[([^\]]+)\]", re.M)
    for cc1, cc2, name in row_pat.findall(content):
        cur = CURRENCY_MAP.get(cc2)
        if not cur:
            continue
        clean = re.sub(r"\s+", " ", name.split(" Act:")[0]).strip()
        if HIGH_IMPACT_NAME.match(clean):
            events.append({"utc_date": utc_day.strftime("%Y-%m-%d"),
                           "currency": cur, "impact": "high",
                           "name": clean[:80], "time_site": None})
    return events


def cache_fresh(path: Path, max_age_h: float = 12.0) -> bool:
    if not path.exists():
        return False
    age_h = (datetime.now().timestamp() - path.stat().st_mtime) / 3600
    return age_h < max_age_h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="HKT date YYYY-MM-DD (default: today)")
    ap.add_argument("--force", action="store_true", help="refetch even if cache fresh")
    args = ap.parse_args()

    now_hk = datetime.now(timezone(timedelta(hours=8)))
    hkt_date = args.date or now_hk.strftime("%Y-%m-%d")
    CAL_DIR.mkdir(parents=True, exist_ok=True)
    out = CAL_DIR / f"{hkt_date}.json"

    if not args.force and cache_fresh(out):
        with open(out) as f:
            existing = json.load(f)
        print(f"Cache fresh ({existing.get('fetched_at', '?')}): {out} — "
              f"{len(existing.get('events', []))} events")
        sys.exit(0)

    now_utc = datetime.now(timezone.utc)
    hkt_dt = datetime.strptime(hkt_date, "%Y-%m-%d")
    utc_day1 = hkt_dt - timedelta(days=1)   # HKT morning = UTC previous day
    utc_day2 = hkt_dt                        # HKT evening = UTC same day

    all_events, sources, failures = [], [], 0
    for utc_day in (utc_day1, utc_day2):
        events = fetch_day_via_webextract(utc_day)
        if events is None:
            failures += 1
            sources.append(f"{utc_day.date()}:none")
            print(f"  {utc_day.date()}: fetch FAILED")
            continue
        sources.append(f"{utc_day.date()}:investing.com")
        all_events.extend(events)
        print(f"  {utc_day.date()}: {len(events)} high-impact tracked events")

    result = {
        "hkt_date": hkt_date,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "event_count": len(all_events),
        "times_available": False,   # see KNOWN LIMITATION above
        "events": sorted(all_events, key=lambda e: (e["utc_date"], e["name"])),
    }
    with open(out, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    if failures == 2 and not all_events:
        print(f"❌ Both UTC days failed to fetch — calendar unusable today. "
              f"compliance_gate will log explicit warning. Manual fallback needed.")
        sys.exit(1)
    if not all_events:
        print(f"⚠️ Fetched but 0 matching events (quiet day or filter gap) — file written.")
        sys.exit(0)
    print(f"✅ {out}: {len(all_events)} events (names only — times pending, "
          f"see KNOWN LIMITATION)")
    sys.exit(0)


if __name__ == "__main__":
    main()
