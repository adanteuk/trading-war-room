#!/usr/bin/env python3
"""
AUDUSD Key Level Validation Script
Uses Ian's ICT/CRT Key Level Methodology
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime

# Initialize MT5
if not mt5.initialize():
    print(f"MT5 initialization failed: {mt5.last_error()}")
    exit(1)

print("MT5 initialized successfully")

# Key levels to validate
LEVELS = {
    "0.70298": 0.70298,
    "0.69673": 0.69673
}

# Download D1 bars (999 bars like previous analyses)
symbol = "AUDUSD"
timeframe = mt5.TIMEFRAME_D1
bars = 999

print(f"\nDownloading {bars} D1 bars for {symbol}...")
rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)

if rates is None or len(rates) == 0:
    print(f"Failed to download data: {mt5.last_error()}")
    mt5.shutdown()
    exit(1)

df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')
print(f"Data range: {df['time'].min()} to {df['time'].max()}")
print(f"Total bars: {len(df)}")

# Analysis parameters (from validated methodology)
TOLERANCE = 0.0005  # ±5 pips for forex (adjusted from stock indices)
MIN_INTERACTIONS = 2
WICK_PRECISION_THRESHOLD = 0.70  # 70%

def analyze_level(df, level, tolerance=TOLERANCE):
    """Analyze a single key level"""
    print(f"\n{'='*60}")
    print(f"LEVEL: {level}")
    print(f"{'='*60}")
    
    lower_bound = level - tolerance
    upper_bound = level + tolerance
    
    interactions = []
    
    for idx, row in df.iterrows():
        high = row['high']
        low = row['low']
        close = row['close']
        open_price = row['open']
        
        # Check if price interacted with the level zone
        if low <= upper_bound and high >= lower_bound:
            # Determine interaction type
            if high <= upper_bound and low >= lower_bound:
                # Candle body within zone
                interaction_type = "BODY"
            elif high > upper_bound and low < lower_bound:
                # Candle engulfed the zone
                interaction_type = "ENGULF"
            elif high > upper_bound:
                # Wick rejection from below
                interaction_type = "WICK_HIGH"
            else:
                # Wick rejection from above
                interaction_type = "WICK_LOW"
            
            # Calculate distance from exact level
            if high >= level >= low:
                distance = 0
                precision = "EXACT"
            else:
                distance = min(abs(high - level), abs(low - level))
                precision = f"{distance:.5f}"
            
            # Calculate wick size
            candle_range = high - low
            upper_wick = high - max(open_price, close)
            lower_wick = min(open_price, close) - low
            
            # Determine if rejection occurred
            rejection = False
            rejection_strength = 0
            
            if interaction_type == "WICK_HIGH":
                # Bullish rejection (price came from below, rejected higher)
                if close > open_price:
                    rejection = True
                    rejection_strength = upper_wick / candle_range if candle_range > 0 else 0
            elif interaction_type == "WICK_LOW":
                # Bearish rejection (price came from above, rejected lower)
                if close < open_price:
                    rejection = True
                    rejection_strength = lower_wick / candle_range if candle_range > 0 else 0
            elif interaction_type == "ENGULF":
                # Strong rejection if close is far from level
                mid = (high + low) / 2
                if (level > mid and close < open_price) or (level < mid and close > open_price):
                    rejection = True
                    rejection_strength = 0.5  # Moderate confidence
            
            interactions.append({
                'date': row['time'],
                'type': interaction_type,
                'high': high,
                'low': low,
                'open': open_price,
                'close': close,
                'distance': distance,
                'precision': precision,
                'rejection': rejection,
                'rejection_strength': rejection_strength,
                'upper_wick': upper_wick,
                'lower_wick': lower_wick,
                'candle_range': candle_range
            })
    
    # Analyze results
    total_interactions = len(interactions)
    wick_interactions = [i for i in interactions if i['type'].startswith('WICK')]
    wick_rejections = [i for i in wick_interactions if i['rejection']]
    
    # Calculate wick precision (percentage of wick interactions that were rejections)
    wick_precision = len(wick_rejections) / len(wick_interactions) if wick_interactions else 0
    
    # Calculate average rejection strength
    avg_rejection_strength = np.mean([i['rejection_strength'] for i in wick_rejections]) if wick_rejections else 0
    
    # Determine if level qualifies as "Ian's Key Level"
    qualifies = (
        total_interactions >= MIN_INTERACTIONS and
        wick_precision >= WICK_PRECISION_THRESHOLD
    )
    
    # Print results
    print(f"\n[ANALYSIS RESULTS]")
    print(f"   Total Interactions: {total_interactions}")
    print(f"   Wick Interactions: {len(wick_interactions)}")
    print(f"   Confirmed Rejections: {len(wick_rejections)}")
    print(f"   Wick Precision: {wick_precision:.1%}")
    print(f"   Avg Rejection Strength: {avg_rejection_strength:.1%}")
    
    print(f"\n[VALIDATION]")
    print(f"   Min Interactions (>={MIN_INTERACTIONS}): {'PASS' if total_interactions >= MIN_INTERACTIONS else 'FAIL'} ({total_interactions})")
    print(f"   Wick Precision (>={WICK_PRECISION_THRESHOLD:.0%}): {'PASS' if wick_precision >= WICK_PRECISION_THRESHOLD else 'FAIL'} ({wick_precision:.1%})")
    
    print(f"\n{'QUALIFIED' if qualifies else 'NOT QUALIFIED'} as Ian's Key Level")
    
    # Show interaction details
    if interactions:
        print(f"\n[INTERACTION HISTORY]")
        for i, interaction in enumerate(interactions[-10:], 1):  # Show last 10
            rejection_marker = "[R]" if interaction['rejection'] else "   "
            print(f"   {rejection_marker} {interaction['date'].strftime('%Y-%m-%d')} | {interaction['type']:8} | H:{interaction['high']:.5f} L:{interaction['low']:.5f} | Dist: {interaction['precision']}")
    
    return {
        'level': level,
        'total_interactions': total_interactions,
        'wick_interactions': len(wick_interactions),
        'wick_rejections': len(wick_rejections),
        'wick_precision': wick_precision,
        'avg_rejection_strength': avg_rejection_strength,
        'qualifies': qualifies,
        'interactions': interactions
    }

# Analyze all levels
results = {}
for level_name, level_value in LEVELS.items():
    results[level_name] = analyze_level(df, level_value)

# Summary
print(f"\n{'='*60}")
print(f"SUMMARY")
print(f"{'='*60}")

for level_name, result in results.items():
    status = "QUALIFIED" if result['qualifies'] else "NOT QUALIFIED"
    print(f"\n{level_name}: {status}")
    print(f"   Interactions: {result['total_interactions']} | Wick Precision: {result['wick_precision']:.1%}")

mt5.shutdown()
print(f"\nMT5 connection closed.")
