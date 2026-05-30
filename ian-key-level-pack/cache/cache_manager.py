#!/usr/bin/env python3
"""
Key Level Cache Manager

Manages persistent caching of MT5 OHLCV data and analysis results
for key level analysis. Avoids redundant data downloads by checking
data freshness per timeframe.

Cache Directory: ~/.hermes/data/key-level-cache/
├── data/
│   └── {SYMBOL}/
│       ├── W1.json  (raw OHLCV + metadata)
│       ├── D1.json
│       └── H4.json
└── results/
    └── {SYMBOL}.json  (analysis results)

TTL Policy:
  H4: 6 hours  (intraday — changes frequently)
  D1: 24 hours (daily bar closes once per day)
  W1: 7 days   (weekly bar changes slowly)
Results: Valid if ALL underlying data is still fresh

Usage:
  from cache_manager import CacheManager
  cache = CacheManager()

  # Check what needs updating
  expired = cache.check_freshness("NAS100")
  # Returns: {"W1": False, "D1": True, "H4": False}  (only D1 expired)

  # Save downloaded data
  cache.save_data("NAS100", "D1", bars, last_price, source="alfred-mt5")

  # Check if cached results are valid
  result = cache.get_cached_result("NAS100")
  # Returns None if expired/not found, or the result dict

  # Save analysis results
  cache.save_result("NAS100", result_dict)

  # Quick check: get results or determine what to fetch
  status = cache.get_status("NAS100")
  # Returns: {"has_result": True, "all_fresh": True, "expired_tfs": [], "result": {...}}
  #       or: {"has_result": False, "all_fresh": False, "expired_tfs": ["W1","D1","H4"], "result": None}
"""

import json
import os
import time
from datetime import datetime, timezone

CACHE_DIR = os.path.expanduser("~/.hermes/data/key-level-cache")
DATA_DIR = os.path.join(CACHE_DIR, "data")
RESULTS_DIR = os.path.join(CACHE_DIR, "results")

# TTL in seconds per timeframe
TTL = {
    "W1": 7 * 24 * 3600,       # 7 days
    "D1": 24 * 3600,            # 24 hours
    "H4": 6 * 3600,             # 6 hours
}

# Required bar counts for valid analysis
MIN_BARS = {
    "W1": 200,
    "D1": 500,
    "H4": 2000,
}


class CacheManager:
    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.data_dir = os.path.join(self.cache_dir, "data")
        self.results_dir = os.path.join(self.cache_dir, "results")
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)

    def _data_path(self, symbol, tf):
        return os.path.join(self.data_dir, symbol, f"{tf}.json")

    def _result_path(self, symbol):
        return os.path.join(self.results_dir, f"{symbol}.json")

    def _symbol_data_dir(self, symbol):
        return os.path.join(self.data_dir, symbol)

    def check_freshness(self, symbol):
        """
        Check which timeframes have expired data.
        Returns dict: {"W1": bool_expired, "D1": bool_expired, "H4": bool_expired}
        True = data is expired or missing (needs download)
        False = data is still fresh
        """
        result = {}
        for tf in ["W1", "D1", "H4"]:
            path = self._data_path(symbol, tf)
            if not os.path.exists(path):
                result[tf] = True  # Missing = needs download
                continue

            try:
                with open(path) as f:
                    data = json.load(f)
                meta = data.get("meta", {})
                cached_at = meta.get("cached_at", 0)
                bar_count = meta.get("bar_count", 0)

                # Check age
                age = time.time() - cached_at
                if age > TTL[tf]:
                    result[tf] = True
                    continue

                # Check bar count sufficiency
                if bar_count < MIN_BARS[tf]:
                    result[tf] = True
                    continue

                result[tf] = False  # Fresh and sufficient
            except (json.JSONDecodeError, KeyError, IndexError):
                result[tf] = True  # Corrupted = needs re-download

        return result

    def get_cached_data(self, symbol, tf):
        """
        Load cached OHLCV data for a symbol/timeframe.
        Returns (bars, last_price) or (None, None) if not found/expired.
        """
        path = self._data_path(symbol, tf)
        if not os.path.exists(path):
            return None, None

        try:
            with open(path) as f:
                data = json.load(f)
            bars = data.get("data", [])
            last_price = data.get("last_price", bars[-1]["close"] if bars else 0)
            return bars, last_price
        except (json.JSONDecodeError, KeyError, IndexError):
            return None, None

    def save_data(self, symbol, tf, bars, last_price, source="alfred-mt5"):
        """
        Save OHLCV data with metadata for cache freshness tracking.
        bars: list of dicts with keys: time, open, high, low, close, tick_volume
        last_price: current/latest price
        source: data source identifier (e.g., "alfred-mt5", "tradingview")
        """
        symbol_dir = self._symbol_data_dir(symbol)
        os.makedirs(symbol_dir, exist_ok=True)

        path = self._data_path(symbol, tf)
        cache_entry = {
            "meta": {
                "symbol": symbol,
                "timeframe": tf,
                "cached_at": time.time(),
                "cached_at_iso": datetime.now(timezone.utc).isoformat(),
                "bar_count": len(bars),
                "source": source,
                "ttl_seconds": TTL[tf],
            },
            "last_price": last_price,
            "data": bars,
        }

        with open(path, "w") as f:
            json.dump(cache_entry, f)

        print(f"  Cached {symbol}/{tf}: {len(bars)} bars saved")

    def get_cached_result(self, symbol):
        """
        Get cached analysis result if it exists and all underlying data is fresh.
        Returns the result dict, or None if expired/not found.
        """
        path = self._result_path(symbol)
        if not os.path.exists(path):
            return None

        # Check if all underlying data is still fresh
        freshness = self.check_freshness(symbol)
        if any(freshness.values()):
            return None  # Some data expired, result is stale

        try:
            with open(path) as f:
                result = json.load(f)

            # Double-check: was this result generated with all 3 TFs?
            tfs_used = result.get("meta", {}).get("tfs_used", [])
            if len(tfs_used) < 3:
                return None  # Incomplete analysis

            return result
        except (json.JSONDecodeError, KeyError):
            return None

    def save_result(self, symbol, result_dict, tfs_used=None):
        """
        Save analysis results with metadata.
        result_dict: the analysis output (levels, scores, etc.)
        tfs_used: list of timeframes used in analysis (e.g., ["W1", "D1", "H4"])
        """
        if tfs_used is None:
            tfs_used = ["W1", "D1", "H4"]

        # Wrap with metadata
        wrapped = {
            "meta": {
                "symbol": symbol,
                "analyzed_at": time.time(),
                "analyzed_at_iso": datetime.now(timezone.utc).isoformat(),
                "tfs_used": tfs_used,
            },
            **result_dict,
        }

        path = self._result_path(symbol)
        with open(path, "w") as f:
            json.dump(wrapped, f)

        print(f"  Cached result for {symbol}")

    def get_status(self, symbol):
        """
        Get full cache status for a symbol.
        Returns:
          - {"has_cached_result": True, "all_data_fresh": True, "expired_tfs": [], "result": {...}}
          - {"has_cached_result": False, "all_data_fresh": False, "expired_tfs": ["W1","D1","H4"], "result": None}
        """
        freshness = self.check_freshness(symbol)
        expired_tfs = [tf for tf, is_expired in freshness.items() if is_expired]
        all_fresh = len(expired_tfs) == 0

        cached_result = None
        if all_fresh:
            cached_result = self.get_cached_result(symbol)

        return {
            "has_cached_result": cached_result is not None,
            "all_data_fresh": all_fresh,
            "expired_tfs": expired_tfs,
            "result": cached_result,
        }

    def list_cached_symbols(self):
        """List all symbols with cached data."""
        if not os.path.exists(self.data_dir):
            return []
        return [d for d in os.listdir(self.data_dir)
                if os.path.isdir(os.path.join(self.data_dir, d))]

    def clear_symbol_cache(self, symbol):
        """Remove all cached data and results for a symbol."""
        import shutil
        sym_dir = self._symbol_data_dir(symbol)
        if os.path.exists(sym_dir):
            shutil.rmtree(sym_dir)
        result_path = self._result_path(symbol)
        if os.path.exists(result_path):
            os.remove(result_path)
        print(f"  Cleared cache for {symbol}")

    def clear_all_cache(self):
        """Remove all cached data and results."""
        import shutil
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        print("  Cleared all cache")


if __name__ == "__main__":
    # Quick test
    cache = CacheManager()
    symbols = cache.list_cached_symbols()
    if symbols:
        for sym in symbols:
            status = cache.get_status(sym)
            print(f"{sym}: fresh={status['all_data_fresh']}, "
                  f"expired={status['expired_tfs']}, "
                  f"has_result={status['has_cached_result']}")
    else:
        print("No cached symbols yet.")
