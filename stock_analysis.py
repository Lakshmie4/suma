#!/usr/bin/env python3
import yfinance as yf
import pandas as pd
import json
import os
from datetime import datetime

SYMBOLS = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'TSLA', 'AMZN', 'META']
REPORTS_DIR = 'reports'
os.makedirs(REPORTS_DIR, exist_ok=True)

def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="10d")
        if hist.empty:
            return None
        
        current = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2] if len(hist) >= 2 else current
        from_prev = ((current - prev_close) / prev_close) * 100
        
        today = ticker.history(period="1d", interval="5m")
        from_open = 0
        if not today.empty:
            open_price = today['Open'].iloc[0]
            from_open = ((current - open_price) / open_price) * 100
        
        # Volume calculation
        avg_vol = hist['Volume'].tail(10).mean()
        curr_vol = hist['Volume'].iloc[-1]
        vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 0
        
        if vol_ratio >= 1.5:
            vol_disp = f"🔊 {vol_ratio:.1f}x"
        elif vol_ratio <= 0.5:
            vol_disp = f"🔇 {vol_ratio:.1f}x"
        else:
            vol_disp = f"📊 {vol_ratio:.1f}x"
        
        # Prediction with confidence
        score = from_prev * 10
        if from_open > 0:
            score += 5
        if vol_ratio >= 1.2:
            score *= 1.2
        elif vol_ratio <= 0.6:
            score *= 0.7
        
        if score > 5:
            pred, conf = "bullish 📈", min(90, int(50 + score))
        elif score < -5:
            pred, conf = "bearish 📉", min(90, int(50 + abs(score)))
        else:
            pred, conf = "neutral ⚪", 50
        
        return {
            'symbol': symbol, 'current': round(current, 2),
            'from_open': round(from_open, 2), 'from_prev': round(from_prev, 2),
            'vol_ratio': round(vol_ratio, 2), 'vol_disp': vol_disp,
            'avg_volume': int(avg_vol), 'current_volume': int(curr_vol),
            'prediction': pred, 'confidence': conf
        }
    except Exception as e:
        print(f"Error {symbol}: {e}")
        return None

# Console output
def print_report(data):
    valid = [d for d in data if d]
    print("\n" + "=" * 90)
    print(f"📈 LIVE MARKET SUMMARY - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 90)
    print(f"{'Symbol':<8} {'Current':<10} {'From Open':<10} {'From Prev':<10} {'Volume':<10} {'Prediction':<20}")
    print("-" * 90)
    for s in valid:
        open_str = f"🟢 +{s['from_open']}%" if s['from_open'] > 0 else f"🔴 {s['from_open']}%"
        prev_str = f"🟢 +{s['from_prev']}%" if s['from_prev'] > 0 else f"🔴 {s['from_prev']}%"
        print(f"{s['symbol']:<8} ${s['current']:<9} {open_str:<10} {prev_str:<10} {s['vol_disp']:<10} {s['prediction']:<20} ({s['confidence']}%)")
    print("=" * 90)

# Save outputs
def save_reports(data):
    valid = [d for d in data if d]
    with open(f'{REPORTS_DIR}/live_report.json', 'w') as f:
        json.dump({'timestamp': datetime.now().isoformat(), 'stocks': valid}, f, indent=2)
    
    pd.DataFrame(valid).to_csv(f'{REPORTS_DIR}/live_report.csv', index=False)
    
    html = f"""<html><head><title>Market Dashboard</title>
    <style>body{{font-family:Arial;background:#1e1e1e;color:#e0e0e0;}} table{{width:100%;}} th,td{{padding:10px;text-align:left;}} .bullish{{color:#00ff88;}} .bearish{{color:#ff4444;}}</style>
    </head><body><h1>📈 Market Dashboard</h1><p>{datetime.now()}</p>
    <table border=1><tr><th>Symbol</th><th>Price</th><th>Volume</th><th>Prediction</th></tr>"""
    for s in valid:
        html += f"<tr><td>{s['symbol']}</td><td>${s['current']}</td><td>{s['vol_disp']}</td><td class='{s['prediction'].split()[0]}'>{s['prediction']}</td></tr>"
    html += "</table></body></html>"
    with open(f'{REPORTS_DIR}/live_dashboard.html', 'w') as f:
        f.write(html)
    print(f"📁 Reports saved to {REPORTS_DIR}/")

# Main
if __name__ == "__main__":
    print("🚀 Fetching data...")
    data = [get_stock_data(s) for s in SYMBOLS]
    print_report(data)
    save_reports(data)
    print(f"✅ Complete - {len([d for d in data if d])}/{len(SYMBOLS)} stocks")
