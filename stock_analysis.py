#!/usr/bin/env python3
"""
Live Market Analysis Script with Real Volume Data
Generates: Console output, JSON report, HTML dashboard, CSV report
"""

import yfinance as yf
import pandas as pd
import json
from datetime import datetime
import os

# ============================================================
# CONFIGURATION
# ============================================================

SYMBOLS = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'TSLA', 'AMZN', 'META']
REPORTS_DIR = 'reports'

# Create reports directory if it doesn't exist
os.makedirs(REPORTS_DIR, exist_ok=True)

# ============================================================
# DATA FETCHING WITH VOLUME
# ============================================================

def get_stock_data(symbol):
    """Fetch current price, changes, and volume data for a symbol"""
    try:
        ticker = yf.Ticker(symbol)
        
        # Get historical data for volume calculation and previous close
        hist = ticker.history(period="5d")
        
        if hist.empty:
            return None
        
        # Get current price and changes
        current_price = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2] if len(hist) >= 2 else current_price
        
        # Calculate percent changes
        from_prev_pct = ((current_price - prev_close) / prev_close) * 100
        
        # Get today's open (first price of today)
        today_hist = ticker.history(period="1d", interval="5m")
        if not today_hist.empty:
            open_price = today_hist['Open'].iloc[0]
            from_open_pct = ((current_price - open_price) / open_price) * 100
        else:
            from_open_pct = 0
        
        # ========== VOLUME CALCULATION ==========
        # 10-day average volume
        avg_volume_10d = hist['Volume'].tail(10).mean()
        current_volume = hist['Volume'].iloc[-1]
        
        if avg_volume_10d > 0:
            volume_ratio = current_volume / avg_volume_10d
        else:
            volume_ratio = 0
        
        # Format volume display with emojis
        if volume_ratio >= 1.5:
            volume_display = f"🔊 {volume_ratio:.1f}x"  # High volume (above 1.5x)
        elif volume_ratio <= 0.5:
            volume_display = f"🔇 {volume_ratio:.1f}x"  # Low volume (below 0.5x)
        else:
            volume_display = f"📊 {volume_ratio:.1f}x"  # Normal volume
        
        # ========== SIMPLE PREDICTION ==========
        # Based on price momentum + volume confirmation
        prediction, confidence = generate_prediction(from_prev_pct, from_open_pct, volume_ratio)
        
        return {
            'symbol': symbol,
            'current': round(current_price, 2),
            'from_open': round(from_open_pct, 2),
            'from_prev': round(from_prev_pct, 2),
            'volume_ratio': round(volume_ratio, 2),
            'volume_display': volume_display,
            'avg_volume_10d': int(avg_volume_10d),
            'current_volume': int(current_volume),
            'prediction': prediction,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

# ============================================================
# PREDICTION ENGINE
# ============================================================

def generate_prediction(from_prev_pct, from_open_pct, volume_ratio):
    """
    Generate prediction based on:
    - Momentum (change from previous close)
    - Intraday strength (change from open)
    - Volume confirmation
    """
    
    # Base momentum score (-100 to +100)
    momentum_score = from_prev_pct * 10  # 1% move = 10 points
    
    # Intraday adjustment
    if from_open_pct > 0:
        momentum_score += 5
    elif from_open_pct < 0:
        momentum_score -= 5
    
    # Volume multiplier (high volume amplifies, low volume reduces confidence)
    if volume_ratio >= 1.2:
        # Strong volume - increase conviction
        momentum_score = momentum_score * 1.2
    elif volume_ratio <= 0.6:
        # Weak volume - reduce conviction
        momentum_score = momentum_score * 0.7
    
    # Determine prediction
    if momentum_score > 5:
        prediction = "bullish"
        confidence = min(90, int(50 + momentum_score))
    elif momentum_score < -5:
        prediction = "bearish"
        confidence = min(90, int(50 + abs(momentum_score)))
    else:
        prediction = "neutral"
        confidence = 50
    
    return prediction, confidence

# ============================================================
# FORMATTING FUNCTIONS
# ============================================================

def format_percent(value, with_emoji=True):
    """Format percentage with color indicator"""
    if value > 0:
        emoji = "🟢" if with_emoji else "+"
        return f"{emoji} +{value:.2f}%"
    elif value < 0:
        emoji = "🔴" if with_emoji else ""
        return f"{emoji} {value:.2f}%"
    else:
        return f"⚪ 0.00%"

def format_prediction(prediction, confidence):
    """Format prediction with emoji"""
    if prediction == "bullish":
        return f"bullish 📈 ({confidence}%)"
    elif prediction == "bearish":
        return f"bearish 📉 ({confidence}%)"
    else:
        return f"neutral ⚪"

# ============================================================
# CONSOLE OUTPUT
# ============================================================

def print_console_report(stocks_data):
    """Print formatted report to console"""
    valid_data = [s for s in stocks_data if s is not None]
    
    print("\n" + "=" * 90)
    print(f"📈 LIVE MARKET SUMMARY - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🕒 Session: 🟢 MARKET OPEN")
    print("=" * 90)
    
    # Header
    print(f"{'Symbol':<8} {'Current':<12} {'From Open':<12} {'From Prev':<12} {'Volume':<12} {'Prediction':<20}")
    print("-" * 90)
    
    # Data rows
    for stock in valid_data:
        from_open_str = format_percent(stock['from_open'])
        from_prev_str = format_percent(stock['from_prev'])
        pred_str = format_prediction(stock['prediction'], stock['confidence'])
        
        print(f"{stock['symbol']:<8} ${stock['current']:<11} {from_open_str:<12} {from_prev_str:<12} {stock['volume_display']:<12} {pred_str:<20}")
    
    print("=" * 90)
    print(f"📄 Detailed report saved to: {REPORTS_DIR}/live_analysis_report.json")
    print(f"🌐 Live dashboard saved to: {REPORTS_DIR}/live_dashboard.html")
    print(f"📊 CSV report saved to: {REPORTS_DIR}/live_analysis.csv")
    print("\n✅ Analysis complete! {}/{} stocks analyzed".format(len(valid_data), len(SYMBOLS)))

# ============================================================
# FILE OUTPUTS
# ============================================================

def save_json_report(stocks_data):
    """Save JSON report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'session': 'MARKET_OPEN',
        'stocks': [s for s in stocks_data if s is not None]
    }
    
    filepath = os.path.join(REPORTS_DIR, 'live_analysis_report.json')
    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2)
    
    return filepath

def save_csv_report(stocks_data):
    """Save CSV report"""
    valid_data = [s for s in stocks_data if s is not None]
    
    if not valid_data:
        return None
    
    df = pd.DataFrame(valid_data)
    # Select and reorder columns
    columns = ['symbol', 'current', 'from_open', 'from_prev', 'volume_ratio', 
               'current_volume', 'avg_volume_10d', 'prediction', 'confidence', 'timestamp']
    df = df[columns]
    
    filepath = os.path.join(REPORTS_DIR, 'live_analysis.csv')
    df.to_csv(filepath, index=False)
    
    return filepath

def save_html_dashboard(stocks_data):
    """Generate HTML dashboard with volume visualization"""
    valid_data = [s for s in stocks_data if s is not None]
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Live Market Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #1e1e1e; color: #e0e0e0; }}
        h1 {{ color: #00ff88; }}
        .timestamp {{ color: #888; margin-bottom: 20px; }}
        table {{ border-collapse: collapse; width: 100%; background: #2d2d2d; }}
        th, td {{ border: 1px solid #444; padding: 12px; text-align: left; }}
        th {{ background: #3d3d3d; color: #00ff88; }}
        .positive {{ color: #00ff88; }}
        .negative {{ color: #ff4444; }}
        .bullish {{ color: #00ff88; }}
        .bearish {{ color: #ff4444; }}
        .neutral {{ color: #ffaa00; }}
        .volume-high {{ color: #ff8844; font-weight: bold; }}
        .volume-normal {{ color: #44ff88; }}
        .volume-low {{ color: #888; }}
        .container {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .chart {{ flex: 1; background: #2d2d2d; padding: 15px; border-radius: 8px; }}
        .volume-bar {{ background: #00ff88; height: 20px; border-radius: 10px; margin: 5px 0; }}
    </style>
</head>
<body>
    <h1>📈 Live Market Dashboard</h1>
    <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    
    <div class="container">
        <div class="chart">
            <h3>Volume Analysis</h3>
"""
    
    # Add volume bars
    for stock in valid_data[:5]:  # Show top 5 for brevity
        width = min(100, stock['volume_ratio'] * 40)
        color = "#00ff88" if stock['volume_ratio'] >= 1 else "#ff8844" if stock['volume_ratio'] >= 0.7 else "#888"
        html_content += f"""
            <div>{stock['symbol']} ({stock['volume_ratio']}x avg)</div>
            <div style="background:#444; border-radius:10px;"><div style="background:{color}; width:{width}%; height:20px; border-radius:10px;"></div></div>
        """
    
    html_content += """
        </div>
    </div>
    
    <table>
        <tr>
            <th>Symbol</th>
            <th>Price</th>
            <th>From Open</th>
            <th>From Prev</th>
            <th>Volume</th>
            <th>Prediction</th>
            <th>Volume (shares)</th>
        </tr>
"""
    
    for stock in valid_data:
        from_open_class = "positive" if stock['from_open'] > 0 else "negative" if stock['from_open'] < 0 else ""
        from_prev_class = "positive" if stock['from_prev'] > 0 else "negative" if stock['from_prev'] < 0 else ""
        
        volume_class = "volume-high" if stock['volume_ratio'] >= 1.2 else "volume-low" if stock['volume_ratio'] <= 0.6 else "volume-normal"
        
        html_content += f"""
        <tr>
            <td><strong>{stock['symbol']}</strong></td>
            <td>${stock['current']}</td>
            <td class="{from_open_class}">{'+' if stock['from_open'] > 0 else ''}{stock['from_open']}%</td>
            <td class="{from_prev_class}">{'+' if stock['from_prev'] > 0 else ''}{stock['from_prev']}%</td>
            <td class="{volume_class}">{stock['volume_display']}</td>
            <td class="{stock['prediction']}">{stock['prediction']} ({stock['confidence']}%)</td>
            <td>{stock['current_volume']:,}</td>
        </tr>
"""
    
    html_content += """
    </table>
    <p style="margin-top: 20px; color: #888;">
        📊 Volume legend: 🔊 >1.5x (high) | 📊 0.5-1.5x (normal) | 🔇 <0.5x (low)
    </p>
</body>
</html>
"""
    
    filepath = os.path.join(REPORTS_DIR, 'live_dashboard.html')
    with open(filepath, 'w') as f:
        f.write(html_content)
    
    return filepath

# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    print(f"\n🚀 Fetching live market data for {len(SYMBOLS)} symbols...")
    
    # Fetch data for all symbols
    stocks_data = []
    for symbol in SYMBOLS:
        print(f"  📡 Fetching {symbol}...", end=" ")
        data = get_stock_data(symbol)
        if data:
            stocks_data.append(data)
            print(f"✅ (Volume: {data['volume_display']})")
        else:
            print("❌ Failed")
    
    # Generate all reports
    print("\n📝 Generating reports...")
    save_json_report(stocks_data)
    save_csv_report(stocks_data)
    save_html_dashboard(stocks_data)
    
    # Print console output
    print_console_report(stocks_data)

if __name__ == "__main__":
    main()
