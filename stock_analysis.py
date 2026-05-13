#!/usr/bin/env python3
"""
Advanced Stock Analysis Script - Tracks Performance from Market Open
Features:
- Tracks percentage change from market open
- Pre-market and after-hours data
- Support/resistance levels
- Volume analysis
- Momentum indicators
- Email alerts for significant moves
"""

import yfinance as yf
import json
import os
import csv
import time
from datetime import datetime, time as dt_time
from pathlib import Path
import pandas as pd
import numpy as np

# Configuration
ALERT_THRESHOLD = float(os.getenv('ALERT_THRESHOLD', '2.0'))  # Alert if change > 2%
SEND_ALERTS = os.getenv('SEND_ALERTS', 'false').lower() == 'true'

def is_market_open():
    """Check if US market is currently open (9:30 AM - 4:00 PM EST)"""
    now = datetime.now()
    # Note: This is simplified - doesn't account for holidays
    market_open = now.replace(hour=9, minute=30, second=0)
    market_close = now.replace(hour=16, minute=0, second=0)
    return market_open <= now <= market_close

def get_stocks():
    """Get stocks from environment variable or use default list"""
    env_stocks = os.getenv('STOCKS_TO_ANALYZE')
    if env_stocks:
        return [s.strip().upper() for s in env_stocks.split(',')]
    
    # Default tech-focused portfolio
    return ['SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'TSLA', 'AMZN', 'META', 'AMD', 'INTC', 'NFLX']

def get_market_open_data(symbol):
    """Get today's market open price and current data"""
    try:
        ticker = yf.Ticker(symbol)
        
        # Get today's data with 5-minute intervals
        today_data = ticker.history(period='1d', interval='5m')
        
        if today_data.empty:
            # Try getting 2 days data if today is empty (pre-market)
            today_data = ticker.history(period='2d', interval='5m')
        
        # Get current price (most recent)
        current_price = today_data['Close'].iloc[-1] if not today_data.empty else None
        
        # Get market open price (first data point of today)
        market_open_price = today_data['Close'].iloc[0] if not today_data.empty else None
        
        # Get previous day close for comparison
        hist = ticker.history(period='2d')
        prev_close = hist['Close'].iloc[-2] if len(hist) >= 2 else None
        
        # Get pre-market price (if available)
        pre_market = ticker.history(period='1d', interval='1m', prepost=True)
        pre_market_price = pre_market['Close'].iloc[0] if not pre_market.empty and len(pre_market) > 0 else None
        
        # Get after-hours price
        after_hours = ticker.history(period='1d', interval='1m', prepost=True)
        after_hours_price = after_hours['Close'].iloc[-1] if not after_hours.empty and len(after_hours) > 0 else None
        
        return {
            'current': round(float(current_price), 2) if current_price else None,
            'market_open': round(float(market_open_price), 2) if market_open_price else None,
            'prev_close': round(float(prev_close), 2) if prev_close else None,
            'pre_market': round(float(pre_market_price), 2) if pre_market_price else None,
            'after_hours': round(float(after_hours_price), 2) if after_hours_price else None,
            'today_data': today_data
        }
    except Exception as e:
        print(f"  ⚠️ Error getting market data: {e}")
        return None

def calculate_predictions(ticker_symbol, current_data, market_data):
    """Calculate predicted movements based on technical indicators"""
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Get historical data for analysis
        hist = ticker.history(period='5d')
        if len(hist) < 5:
            return None
        
        # Calculate simple moving averages
        sma_5 = hist['Close'].rolling(window=5).mean().iloc[-1]
        sma_20 = hist['Close'].rolling(window=20).mean().iloc[-1] if len(hist) >= 20 else sma_5
        
        # Calculate RSI (simplified)
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs.iloc[-1])) if not loss.iloc[-1] == 0 else 50
        
        # Volume trend
        volume_trend = "increasing" if hist['Volume'].iloc[-1] > hist['Volume'].iloc[-2] else "decreasing"
        
        # Support and resistance levels
        recent_high = hist['High'].tail(20).max()
        recent_low = hist['Low'].tail(20).min()
        
        # Prediction logic
        current = market_data['current'] if market_data['current'] else current_data.get('price', 0)
        
        if current and sma_5 and sma_20:
            if current > sma_5 and current > sma_20:
                trend = "bullish 📈"
                confidence = "High"
            elif current < sma_5 and current < sma_20:
                trend = "bearish 📉"
                confidence = "High"
            elif current > sma_5:
                trend = "slightly bullish ↗️"
                confidence = "Medium"
            else:
                trend = "slightly bearish ↘️"
                confidence = "Medium"
            
            # Predict next hour movement
            if rsi > 70:
                next_hour = "likely pullback 🔻"
            elif rsi < 30:
                next_hour = "likely bounce 🔺"
            else:
                next_hour = "sideways ➡️"
        else:
            trend = "insufficient data"
            confidence = "Low"
            next_hour = "unknown"
        
        return {
            'trend': trend,
            'confidence': confidence,
            'rsi': round(rsi, 1),
            'sma_5': round(sma_5, 2),
            'sma_20': round(sma_20, 2),
            'support': round(recent_low, 2),
            'resistance': round(recent_high, 2),
            'volume_trend': volume_trend,
            'next_hour_prediction': next_hour
        }
    except Exception as e:
        print(f"  ⚠️ Prediction error: {e}")
        return None

def analyze_stock_advanced(symbol):
    """Advanced analysis tracking from market open"""
    try:
        print(f"  📊 Analyzing {symbol}...")
        
        # Get market data
        market_data = get_market_open_data(symbol)
        if not market_data or not market_data['current']:
            return None
        
        current_price = market_data['current']
        market_open = market_data['market_open']
        prev_close = market_data['prev_close']
        
        # Calculate percentages
        change_from_open = None
        if market_open and current_price:
            change_from_open = ((current_price - market_open) / market_open) * 100
        
        change_from_prev = None
        if prev_close and current_price:
            change_from_prev = ((current_price - prev_close) / prev_close) * 100
        
        pre_market_change = None
        if market_data['pre_market'] and prev_close:
            pre_market_change = ((market_data['pre_market'] - prev_close) / prev_close) * 100
        
        # Get additional data
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Volume analysis
        volume = market_data['today_data']['Volume'].iloc[-1] if not market_data['today_data'].empty else 0
        avg_volume = info.get('averageVolume', volume)
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1
        
        # Day range
        day_high = market_data['today_data']['High'].iloc[-1] if not market_data['today_data'].empty else current_price
        day_low = market_data['today_data']['Low'].iloc[-1] if not market_data['today_data'].empty else current_price
        
        # Get predictions
        current_info = {'price': current_price}
        predictions = calculate_predictions(symbol, current_info, market_data)
        
        # Determine trading session
        if is_market_open():
            session = "Market Open"
            session_icon = "🟢"
        else:
            now = datetime.now()
            if now.time() < dt_time(9, 30):
                session = "Pre-Market"
                session_icon = "🌅"
            else:
                session = "After-Hours"
                session_icon = "🌙"
        
        # Create alert if significant movement
        alert = None
        if SEND_ALERTS and change_from_open and abs(change_from_open) > ALERT_THRESHOLD:
            alert = {
                'symbol': symbol,
                'change_from_open': change_from_open,
                'current_price': current_price,
                'message': f"{'🚨 UP' if change_from_open > 0 else '🔻 DOWN'} {abs(change_from_open):.2f}% from market open!"
            }
        
        return {
            'symbol': symbol,
            'company_name': info.get('longName', symbol),
            'current_price': current_price,
            'market_open': market_open,
            'change_from_open': round(change_from_open, 2) if change_from_open else None,
            'change_from_open_percent': round(change_from_open, 2) if change_from_open else None,
            'change_from_prev': round(change_from_prev, 2) if change_from_prev else None,
            'change_from_prev_percent': round(change_from_prev, 2) if change_from_prev else None,
            'pre_market_change': round(pre_market_change, 2) if pre_market_change else None,
            'session': session,
            'session_icon': session_icon,
            'volume': int(volume),
            'avg_volume': int(avg_volume),
            'volume_ratio': round(volume_ratio, 2),
            'day_high': round(float(day_high), 2),
            'day_low': round(float(day_low), 2),
            'predictions': predictions,
            'alert': alert,
            'pe_ratio': info.get('trailingPE', 'N/A'),
            'market_cap': format_market_cap(info.get('marketCap', 'N/A')),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None

def format_market_cap(cap):
    """Format market cap"""
    if cap == 'N/A':
        return 'N/A'
    if cap >= 1e12:
        return f"{cap/1e12:.2f}T"
    elif cap >= 1e9:
        return f"{cap/1e9:.2f}B"
    elif cap >= 1e6:
        return f"{cap/1e6:.2f}M"
    return str(cap)

def print_live_summary(results):
    """Print real-time summary"""
    print("\n" + "=" * 90)
    print(f"📈 LIVE MARKET SUMMARY - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🕒 Session: {'🟢 MARKET OPEN' if is_market_open() else '🌅 PRE-MARKET / 🌙 AFTER-HOURS'}")
    print("=" * 90)
    
    # Headers
    print(f"{'Symbol':<8} {'Current':<10} {'From Open':<12} {'From Prev':<12} {'Volume':<12} {'Prediction':<15}")
    print("-" * 90)
    
    alerts = []
    
    for stock in results:
        if not stock:
            continue
        
        # Change from open with color indicator
        if stock['change_from_open'] is not None:
            change_icon = "🟢" if stock['change_from_open'] >= 0 else "🔴"
            change_str = f"{change_icon} {stock['change_from_open']:+.2f}%"
        else:
            change_str = "N/A"
        
        # Change from previous close
        if stock['change_from_prev'] is not None:
            prev_icon = "📈" if stock['change_from_prev'] >= 0 else "📉"
            prev_str = f"{prev_icon} {stock['change_from_prev']:+.2f}%"
        else:
            prev_str = "N/A"
        
        # Volume ratio indicator
        vol_icon = "🔥" if stock['volume_ratio'] > 1.5 else "📊"
        vol_str = f"{vol_icon} {stock['volume_ratio']:.1f}x"
        
        # Prediction
        pred_str = stock['predictions']['trend'][:12] if stock['predictions'] else "N/A"
        
        print(f"{stock['symbol']:<8} ${stock['current_price']:<9} {change_str:<12} {prev_str:<12} {vol_str:<12} {pred_str:<15}")
        
        # Collect alerts
        if stock.get('alert'):
            alerts.append(stock['alert'])
    
    # Print alerts if any
    if alerts:
        print("\n" + "=" * 90)
        print("🚨 ALERTS - Significant Moves from Market Open:")
        for alert in alerts:
            print(f"  ⚡ {alert['symbol']}: {alert['message']} (${alert['current_price']})")
    
    print("=" * 90)

def save_detailed_report(results, report_dir):
    """Save detailed JSON report with all predictive data"""
    report_path = Path(report_dir) / "live_analysis_report.json"
    
    # Clean data for JSON (remove non-serializable objects)
    clean_results = []
    for stock in results:
        if stock:
            stock_copy = stock.copy()
            if 'predictions' in stock_copy and stock_copy['predictions']:
                stock_copy['predictions'] = stock_copy['predictions']
            if 'alert' in stock_copy and stock_copy['alert']:
                stock_copy['alert'] = stock_copy['alert']
            clean_results.append(stock_copy)
    
    with open(report_path, 'w') as f:
        json.dump(clean_results, f, indent=2)
    print(f"📄 Detailed report saved to: {report_path}")
    return report_path

def save_html_dashboard(results, report_dir):
    """Generate an HTML dashboard with predictions"""
    if not results:
        return None
    
    market_status = "OPEN" if is_market_open() else "CLOSED"
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Live Stock Dashboard - {datetime.now().strftime('%Y-%m-%d')}</title>
    <meta http-equiv="refresh" content="300">
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
        .market-status {{
            text-align: center;
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            font-weight: bold;
        }}
        .market-open {{
            background: #4CAF50;
            color: white;
        }}
        .market-closed {{
            background: #f44336;
            color: white;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        .positive {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .negative {{
            color: #f44336;
            font-weight: bold;
        }}
        .bullish {{
            color: #4CAF50;
        }}
        .bearish {{
            color: #f44336;
        }}
        .prediction-card {{
            background: #f9f9f9;
            padding: 5px;
            border-radius: 3px;
            font-size: 12px;
        }}
        .alert {{
            background: #ff9800;
            color: white;
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            animation: blink 1s infinite;
        }}
        @keyframes blink {{
            50% {{ opacity: 0.5; }}
        }}
    </style>
</head>
<body>
<div class="container">
    <h1>📊 Live Stock Market Dashboard</h1>
    <div class="market-status market-{'open' if is_market_open() else 'closed'}">
        🕒 MARKET {market_status} - {datetime.now().strftime('%H:%M:%S')}
    </div>
"""
    
    # Add alerts section
    alerts = [s for s in results if s and s.get('alert')]
    if alerts:
        html_content += '<div class="alert">🚨 ALERTS: '
        for alert in alerts:
            html_content += f'{alert["symbol"]}: {alert["alert"]["message"]} | '
        html_content += '</div>'
    
    html_content += """
    <table>
        <thead>
            <tr>
                <th>Symbol</th>
                <th>Company</th>
                <th>Price</th>
                <th>From Open</th>
                <th>Volume</th>
                <th>Prediction</th>
                <th>RSI</th>
                <th>Support/Resistance</th>
            </tr>
        </thead>
        <tbody>
"""
    
    for stock in results:
        if not stock:
            continue
        
        change_class = "positive" if stock.get('change_from_open', 0) and stock['change_from_open'] >= 0 else "negative"
        change_icon = "▲" if stock.get('change_from_open', 0) and stock['change_from_open'] >= 0 else "▼"
        
        trend_class = "bullish" if stock['predictions'] and 'bullish' in stock['predictions']['trend'] else "bearish" if stock['predictions'] and 'bearish' in stock['predictions']['trend'] else ""
        
        html_content += f"""
            <tr>
                <td><strong>{stock['symbol']}</strong></td>
                <td>{stock['company_name'][:30]}</td>
                <td>${stock['current_price']}</td>
                <td class="{change_class}">{change_icon} {abs(stock.get('change_from_open', 0)):.2f}%</td>
                <td>{stock['volume_ratio']:.1f}x</td>
                <td class="{trend_class}">{stock['predictions']['trend'] if stock['predictions'] else 'N/A'}</td>
                <td>{stock['predictions']['rsi'] if stock['predictions'] else 'N/A'}</td>
                <td>S:{stock['predictions']['support'] if stock['predictions'] else 'N/A'}<br>R:{stock['predictions']['resistance'] if stock['predictions'] else 'N/A'}</td>
            </tr>
"""
    
    html_content += """
        </tbody>
    </table>
    
    <div style="margin-top: 20px; padding: 10px; background: #f0f0f0; border-radius: 5px;">
        <small>📌 Legend: 🟢 Positive from open | 🔴 Negative from open | 🔥 High volume | Auto-refreshes every 5 minutes</small>
    </div>
</div>
</body>
</html>
"""
    
    report_path = Path(report_dir) / "live_dashboard.html"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"🌐 Live dashboard saved to: {report_path}")
    return report_path

def main():
    """Main execution"""
    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    
    stocks = get_stocks()
    
    print("=" * 90)
    print(f"🚀 ADVANCED STOCK ANALYSIS - Tracking from Market Open")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Analyzing {len(stocks)} stocks: {', '.join(stocks)}")
    if SEND_ALERTS:
        print(f"🔔 Alerts enabled: Will notify if > {ALERT_THRESHOLD}% move")
    print("=" * 90)
    
    results = []
    for i, symbol in enumerate(stocks, 1):
        print(f"\n[{i}/{len(stocks)}]", end=" ")
        data = analyze_stock_advanced(symbol)
        if data:
            results.append(data)
            # Print real-time change
            if data['change_from_open']:
                icon = "📈" if data['change_from_open'] >= 0 else "📉"
                print(f"  {icon} From open: {data['change_from_open']:+.2f}% | Current: ${data['current_price']}")
            else:
                print(f"  ℹ️ ${data['current_price']} (No open data yet)")
        else:
            print(f"  ❌ Failed to analyze {symbol}")
            results.append(None)
        
        time.sleep(0.5)  # Rate limiting
    
    # Print live summary
    print_live_summary(results)
    
    # Save reports
    json_path = save_detailed_report(results, report_dir)
    html_path = save_html_dashboard(results, report_dir)
    
    # Save CSV for historical tracking
    csv_path = Path(report_dir) / "live_analysis.csv"
    if results:
        df = pd.DataFrame([r for r in results if r])
        df.to_csv(csv_path, index=False)
        print(f"📊 CSV report saved to: {csv_path}")
    
    print("\n" + "=" * 90)
    print(f"✅ Analysis complete! {len([r for r in results if r])}/{len(stocks)} stocks analyzed")
    print(f"📁 Reports saved to '{report_dir}/'")
    print("=" * 90)

if __name__ == "__main__":
    main()
