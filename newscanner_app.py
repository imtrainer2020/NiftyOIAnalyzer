from flask import Flask, render_template_string
from curl_cffi import requests
from datetime import datetime
import re
import json
import time

app = Flask(__name__)

# Aapke 5 stocks ki list
STOCKS_TO_SCAN = ["RELIANCE", "HDFCBANK", "TMPV", "INFY", "TCS"]

# Naya Anti-Block Session
session = requests.Session(impersonate="chrome120")

# --- HTML TEMPLATE (DASHBOARD) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Live Scanner</title>
    <meta http-equiv="refresh" content="60">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #f0f2f5; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 900px; margin: auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        h2 { text-align: center; color: #0056b3; margin-top: 0;}
        p.time { text-align: center; color: #666; font-size: 14px; margin-bottom: 20px;}
        
        .alert-box { padding: 15px; background-color: #e2e3e5; border-left: 5px solid #6c757d; border-radius: 4px; margin-bottom: 20px; font-weight: bold;}
        .alert-green { background-color: #d4edda; border-left-color: #28a745; color: #155724; }
        .alert-red { background-color: #f8d7da; border-left-color: #dc3545; color: #721c24; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; text-align: center; }
        th, td { border: 1px solid #ddd; padding: 12px; }
        th { background-color: #004085; color: white; }
        .buy-signal { background-color: #28a745; color: white; font-weight: bold; border-radius: 4px; padding: 4px 8px;}
        .sell-signal { background-color: #dc3545; color: white; font-weight: bold; border-radius: 4px; padding: 4px 8px;}
        .wait-signal { color: #6c757d; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🚀 Live Scanner Dashboard</h2>
        <p class="time">Last Scanned: <b>{{ current_time }}</b> (Auto-refreshes every 60s)</p>

        <h3>🎯 Stocks Passing Your Rule</h3>
        {% if passed_stocks %}
            {% for alert in passed_stocks %}
                <div class="alert-box {{ 'alert-green' if alert.signal == 'BUY' else 'alert-red' }}">
                    {{ alert.message }}
                </div>
            {% endfor %}
        {% else %}
            <div class="alert-box">
                No stocks are matching the 1.25x rule right now. Market might be sideways.
            </div>
        {% endif %}

        <h3>📊 Detailed Scan Report</h3>
        <table>
            <tr>
                <th>Stock</th>
                <th>Nearest Expiry</th>
                <th>Signal</th>
                <th>Call Vol</th>
                <th>Put Vol</th>
                <th>Call OI</th>
                <th>Put OI</th>
            </tr>
            {% for row in scan_results %}
            <tr>
                <td><b>{{ row.stock }}</b></td>
                <td>{{ row.expiry }}</td>
                <td>
                    {% if row.signal == 'BUY' %} <span class="buy-signal">BUY (BULLISH)</span>
                    {% elif row.signal == 'SELL' %} <span class="sell-signal">SELL (BEARISH)</span>
                    {% elif row.signal == 'ERROR' %} <span class="val-red">API ERROR</span>
                    {% else %} <span class="wait-signal">WAIT</span> {% endif %}
                </td>
                <td>{{ row.c_vol }}</td>
                <td>{{ row.p_vol }}</td>
                <td>{{ row.c_oi }}</td>
                <td>{{ row.p_oi }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

def fetch_nse_data(url):
    """NSE se safely data fetch karne ka function"""
    headers = {"Accept": "*/*", "Referer": "https://www.nseindia.com/"}
    try:
        # Base page visit zaroori hai cookies ke liye
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        time.sleep(0.5)
        response = session.get(url, headers=headers, timeout=10)
        return response.status_code, response.text
    except Exception as e:
        return 500, str(e)

def run_scanner():
    multiplyNo = 1.25
    results = []
    passed = []
    
    today = datetime.today().date()

    for stock in STOCKS_TO_SCAN:
        # --- STEP 1: API 1 se valid expiry dates lena ---
        url_api1 = f"https://www.nseindia.com/api/option-chain-contract-info?symbol={stock}"
        status1, text1 = fetch_nse_data(url_api1)
        
        if status1 != 200:
            results.append({"stock": stock, "expiry": "-", "signal": "ERROR", "c_vol": "-", "p_vol": "-", "c_oi": "-", "p_oi": "-"})
            continue
            
        # Regex se dates nikal kar nearest date find karna
        matches = re.findall(r'\d{2}-[A-Za-z]{3}-\d{4}', text1)
        valid_dates = list(set(matches))
        
        if not valid_dates:
            results.append({"stock": stock, "expiry": "-", "signal": "ERROR", "c_vol": "-", "p_vol": "-", "c_oi": "-", "p_oi": "-"})
            continue
            
        valid_dt_objs = [datetime.strptime(d, "%d-%b-%Y").date() for d in valid_dates]
        nearest_dt = min(valid_dt_objs, key=lambda x: abs(x - today))
        nearest_expiry = nearest_dt.strftime("%d-%b-%Y")

        # --- STEP 2: API 2 se actual data lena ---
        url_api2 = f"https://www.nseindia.com/api/option-chain-v3?type=Equity&symbol={stock}&expiry={nearest_expiry}"
        status2, text2 = fetch_nse_data(url_api2)
        
        if status2 != 200:
            results.append({"stock": stock, "expiry": nearest_expiry, "signal": "ERROR", "c_vol": "-", "p_vol": "-", "c_oi": "-", "p_oi": "-"})
            continue
            
        try:
            json_data = json.loads(text2)
            data = json_data.get('records', {}).get('data', [])
            
            # Grand Totals Calculate karna
            t_c_vol = sum(row.get('CE', {}).get('totalTradedVolume', 0) for row in data)
            t_c_oi = sum(row.get('CE', {}).get('openInterest', 0) for row in data)
            t_c_chg_oi = sum(row.get('CE', {}).get('changeinOpenInterest', 0) for row in data)
            
            t_p_vol = sum(row.get('PE', {}).get('totalTradedVolume', 0) for row in data)
            t_p_oi = sum(row.get('PE', {}).get('openInterest', 0) for row in data)
            t_p_chg_oi = sum(row.get('PE', {}).get('changeinOpenInterest', 0) for row in data)
            
            if t_c_vol == 0 or t_p_vol == 0:
                results.append({"stock": stock, "expiry": nearest_expiry, "signal": "WAIT", "c_vol": "-", "p_vol": "-", "c_oi": "-", "p_oi": "-"})
                continue

            # --- STEP 3: AAPKA 1.25x RULE CHECK ---
            signal = "WAIT"
            
            # BULLISH RULE
            if (t_p_vol >= multiplyNo * t_c_vol) and (t_p_oi >= multiplyNo * t_c_oi) and (t_p_chg_oi > 0) and (t_p_chg_oi >= multiplyNo * t_c_chg_oi):
                signal = "BUY"
                passed.append({
                    "signal": "BUY", 
                    "message": f"🟢 {stock} ({nearest_expiry}): BULLISH TREND! Puts are {multiplyNo}x heavier than Calls."
                })
                
            # BEARISH RULE
            elif (t_c_vol >= multiplyNo * t_p_vol) and (t_c_oi >= multiplyNo * t_p_oi) and (t_c_chg_oi > 0) and (t_c_chg_oi >= multiplyNo * t_p_chg_oi):
                signal = "SELL"
                passed.append({
                    "signal": "SELL", 
                    "message": f"🔴 {stock} ({nearest_expiry}): BEARISH TREND! Calls are {multiplyNo}x heavier than Puts."
                })

            results.append({
                "stock": stock, "expiry": nearest_expiry, "signal": signal,
                "c_vol": f"{t_c_vol:,}", "p_vol": f"{t_p_vol:,}",
                "c_oi": f"{t_c_oi:,}", "p_oi": f"{t_p_oi:,}"
            })
            
        except Exception as e:
            results.append({"stock": stock, "expiry": nearest_expiry, "signal": "ERROR", "c_vol": "-", "p_vol": "-", "c_oi": "-", "p_oi": "-"})

        # API Block na ho isliye halka sa rest
        time.sleep(1)
        
    return results, passed

@app.route('/')
def index():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scan_results, passed_stocks = run_scanner()
    
    return render_template_string(
        HTML_TEMPLATE, 
        current_time=current_time, 
        scan_results=scan_results, 
        passed_stocks=passed_stocks
    )

if __name__ == "__main__":
    print("🚀 Auto-Scanner Running! Open: http://127.0.0.1:5001")
    app.run(debug=True, port=5001)