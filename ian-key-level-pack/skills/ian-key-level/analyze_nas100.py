#!/usr/bin/env python3
"""
Ian's Key Level Analysis for NAS100
Applies ICT/CRT methodology to identify and validate key levels
"""

import pandas as pd
import numpy as np
from datetime import datetime

def load_data(filepath):
    """Load MT5 data"""
    df = pd.read_csv(filepath)
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    return df

def find_level_interactions(df, level, tolerance=10):
    """
    Find all candles that interacted with a level
    
    Returns interactions with:
    - date, type (wick_high/wick_low/body_high/body_low)
    - rejection strength (wick length / candle range)
    """
    interactions = []
    
    for idx, row in df.iterrows():
        candle_range = row['High'] - row['Low']
        if candle_range == 0:
            continue
            
        # Check if high touched level
        if row['High'] >= level - tolerance and row['High'] <= level + tolerance:
            is_wick = row['Close'] < row['High']  # Upper wick = rejection
            upper_wick = row['High'] - max(row['Open'], row['Close'])
            rejection_strength = (upper_wick / candle_range) * 100 if candle_range > 0 else 0
            
            interactions.append({
                'date': idx,
                'type': 'wick_high' if is_wick else 'body_high',
                'price': row['High'],
                'rejection_strength': rejection_strength,
                'candle_range': candle_range
            })
        
        # Check if low touched level
        elif row['Low'] >= level - tolerance and row['Low'] <= level + tolerance:
            is_wick = row['Close'] > row['Low']  # Lower wick = rejection
            lower_wick = min(row['Open'], row['Close']) - row['Low']
            rejection_strength = (lower_wick / candle_range) * 100 if candle_range > 0 else 0
            
            interactions.append({
                'date': idx,
                'type': 'wick_low' if is_wick else 'body_low',
                'price': row['Low'],
                'rejection_strength': rejection_strength,
                'candle_range': candle_range
            })
    
    return interactions

def analyze_level(df, level, tolerance=10):
    """Analyze a single key level"""
    interactions = find_level_interactions(df, level, tolerance)
    
    if not interactions:
        return {
            'level': level,
            'status': 'NO_INTERACTIONS',
            'interactions_count': 0,
            'wick_precision': 0,
            'avg_rejection': 0
        }
    
    wick_count = sum(1 for i in interactions if i['type'].startswith('wick'))
    wick_precision = (wick_count / len(interactions)) * 100
    avg_rejection = np.mean([i['rejection_strength'] for i in interactions])
    
    # Determine status based on Ian's methodology
    if wick_precision > 70 and len(interactions) >= 2 and avg_rejection > 30:
        status = 'CONFIRMED'
    elif wick_precision > 50 and len(interactions) >= 2:
        status = 'MODERATE'
    else:
        status = 'NEEDS_VALIDATION'
    
    return {
        'level': level,
        'status': status,
        'interactions_count': len(interactions),
        'wick_count': wick_count,
        'wick_precision': wick_precision,
        'avg_rejection': avg_rejection,
        'interactions': interactions
    }

def identify_key_levels(df, timeframe='D1'):
    """
    Identify potential key levels from price data
    
    Uses:
    - Swing highs/lows
    - High-volume nodes
    - Psychological round numbers
    """
    levels = []
    
    # Find swing highs and lows
    window = 20 if timeframe == 'D1' else 10
    
    # Swing highs
    for i in range(window, len(df) - window):
        if df['High'].iloc[i] == df['High'].iloc[i-window:i+window+1].max():
            levels.append({
                'price': round(df['High'].iloc[i], 1),
                'type': 'swing_high',
                'date': df.index[i]
            })
    
    # Swing lows
    for i in range(window, len(df) - window):
        if df['Low'].iloc[i] == df['Low'].iloc[i-window:i+window+1].min():
            levels.append({
                'price': round(df['Low'].iloc[i], 1),
                'type': 'swing_low',
                'date': df.index[i]
            })
    
    # Add psychological levels
    current_price = df['Close'].iloc[-1]
    round_nums = [
        round(current_price / 500) * 500,
        round(current_price / 100) * 100,
    ]
    for rn in round_nums:
        levels.append({'price': float(rn), 'type': 'psychological', 'date': None})
    
    # Remove duplicates (within 5 points)
    unique_levels = []
    for level in sorted(levels, key=lambda x: x['price'], reverse=True):
        if not unique_levels or abs(level['price'] - unique_levels[-1]['price']) > 5:
            unique_levels.append(level)
    
    return unique_levels

def cluster_levels(levels, zone_threshold=50):
    """Cluster levels that are within zone_threshold of each other"""
    if not levels:
        return []
    
    clusters = []
    sorted_levels = sorted(levels, key=lambda x: x['level'])
    
    current_cluster = [sorted_levels[0]]
    
    for level in sorted_levels[1:]:
        if level['level'] - current_cluster[-1]['level'] <= zone_threshold:
            current_cluster.append(level)
        else:
            clusters.append(current_cluster)
            current_cluster = [level]
    
    clusters.append(current_cluster)
    return clusters

def main():
    print("=" * 70)
    print("  NAS100 Key Level Analysis (Ian's ICT/CRT Methodology)")
    print("=" * 70)
    print()
    
    # Load data
    print("[LOADING] D1 data...")
    df_d1 = load_data('C:/Users/AC/.openclaw/workspace/NAS100_D1_100bars.csv')
    print(f"[OK] Loaded {len(df_d1)} D1 bars")
    print(f"   Range: {df_d1.index[0].date()} to {df_d1.index[-1].date()}")
    print(f"   Current Price: {df_d1['Close'].iloc[-1]:.1f}")
    print()
    
    # Current price levels
    current_price = df_d1['Close'].iloc[-1]
    recent_high = df_d1['High'].iloc[-5:].max()
    recent_low = df_d1['Low'].iloc[-5:].min()
    week_high = df_d1['High'].iloc[-1]  # Mar 27 high
    week_low = df_d1['Low'].iloc[-1]    # Mar 27 low
    
    # Define key levels based on recent price action
    proposed_levels = [
        # Resistance levels
        {'level': 24550.1, 'name': 'R5 - Weekly High (Mar 23)', 'type': 'swing_high'},
        {'level': 24338.0, 'name': 'R4 - D1 High (Mar 24)', 'type': 'swing_high'},
        {'level': 24161.0, 'name': 'R3 - FVG Zone', 'type': 'consolidation'},
        {'level': 23773.6, 'name': 'R2 - D1 High (Mar 27)', 'type': 'swing_high'},
        {'level': 23618.7, 'name': 'R1 - D1 Close (Mar 26)', 'type': 'order_block'},
        
        # Support levels
        {'level': 23559.6, 'name': 'S0 - D1 Low (Mar 26)', 'type': 'swing_low'},
        {'level': 23031.1, 'name': 'S1 - Weekly Low (Mar 27)', 'type': 'swing_low'},
        {'level': 22850.0, 'name': 'S2 - Psychological', 'type': 'psychological'},
        {'level': 22500.0, 'name': 'S3 - Major Support', 'type': 'psychological'},
    ]
    
    print("[ANALYZING] Key levels using Ian's methodology...")
    print()
    
    results = []
    for prop_level in proposed_levels:
        result = analyze_level(df_d1, prop_level['level'], tolerance=15)
        result['name'] = prop_level['name']
        result['level_type'] = prop_level['type']
        results.append(result)
        
        status_icon = {
            'CONFIRMED': '[OK]',
            'MODERATE': '[WARN]',
            'NEEDS_VALIDATION': '[?]',
            'NO_INTERACTIONS': '[--]'
        }.get(result['status'], '[?]')
        
        print(f"{status_icon} {prop_level['level']:>10.1f} - {prop_level['name']}")
        print(f"   Interactions: {result['interactions_count']} | Wick Precision: {result.get('wick_precision', 0):.0f}% | Avg Rejection: {result.get('avg_rejection', 0):.1f}%")
    
    print()
    print("=" * 70)
    print("  Ian's Key Level Assessment")
    print("=" * 70)
    print()
    
    # Highlight confirmed levels
    confirmed = [r for r in results if r['status'] == 'CONFIRMED']
    moderate = [r for r in results if r['status'] == 'MODERATE']
    
    if confirmed:
        print("[CONFIRMED] LEVELS (Wick Precision >70%, 2+ tests, >30% rejection):")
        for r in confirmed:
            print(f"   {r['level']:.1f} - {r['name']}")
        print()
    
    if moderate:
        print("[MODERATE] LEVELS (Partial confirmation):")
        for r in moderate:
            print(f"   {r['level']:.1f} - {r['name']}")
        print()
    
    # Zone analysis
    print("[ZONE ANALYSIS]:")
    
    # Resistance zone
    res_zone_levels = [r['level'] for r in results if r['level'] > current_price and r['interactions_count'] > 0]
    if len(res_zone_levels) >= 2:
        zone_spread = max(res_zone_levels[:3]) - min(res_zone_levels[:3])
        if zone_spread < 50:
            print(f"   Resistance Zone: {min(res_zone_levels[:3]):.1f} - {max(res_zone_levels[:3]):.1f} ({zone_spread:.1f} pts)")
    
    # Support zone
    supp_zone_levels = [r['level'] for r in results if r['level'] < current_price and r['interactions_count'] > 0]
    if len(supp_zone_levels) >= 2:
        zone_spread = max(supp_zone_levels[-3:]) - min(supp_zone_levels[-3:])
        if zone_spread < 50:
            print(f"   Support Zone: {min(supp_zone_levels[-3:]):.1f} - {max(supp_zone_levels[-3:]):.1f} ({zone_spread:.1f} pts)")
    
    print()
    print("[SAVING] Analysis to key_levels_nas100.json...")
    
    # Save results
    import json
    output = {
        'symbol': 'NAS100',
        'analysis_date': datetime.now().isoformat(),
        'current_price': float(current_price),
        'timeframe': 'D1',
        'bars_analyzed': len(df_d1),
        'levels': [
            {
                'level': r['level'],
                'name': r['name'],
                'type': r['level_type'],
                'status': r['status'],
                'interactions': r['interactions_count'],
                'wick_precision': r.get('wick_precision', 0),
                'avg_rejection': r.get('avg_rejection', 0)
            }
            for r in results
        ]
    }
    
    with open('C:/Users/AC/.openclaw/workspace/key_levels_nas100.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("[OK] Analysis complete!")
    
    return results

if __name__ == "__main__":
    main()
