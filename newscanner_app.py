from flask import Flask, render_template_string, redirect, url_for
from curl_cffi import requests
from datetime import datetime
import re
import json
import time

app = Flask(__name__)
STOCKS_TO_SCAN = ["RELIANCE", "HDFCBANK", "TMPV", "INFY", "TCS"]
session = requests.Session(impersonate="chrome120")

# --- HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Stock Scanner Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; padding: 20px; background: #f4f4f4; }
        .container { max-width: 1000px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .btn-refresh { padding: 12px 25px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 5px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: center; }
        th { background-color: #004085; color: white; }
        .BUY { color: green; font-weight: bold; } .SELL { color: red; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🎯 Ideal Strike Price Sniper</h2>
        <form action="/refresh" method="POST">
            <button class="btn-refresh">Refresh Scan Data</button>
        </form>
        <p>Last Scanned: {{ last_scan_time }}</p>

        <h3>Stocks Passing Rule</h3>
        <table>
            <tr>
                <th>Stock</th><th>Signal</th><th>PCR</th>
                <th>Call Vol</th><th>Call OI</th><th>Call Chg OI</th>
                <th>Put Vol</th><th>Put OI</th><th>Put Chg OI</th>
            </tr>
            {% for row in passed_stocks %}
            <tr>
                <td><b>{{ row.stock }}</b></td>
                <td class="{{ row.signal }}">{{ row.signal }}</td>
                <td>{{ row.pcr }}</td>
                <td>{{ row.c_vol }}</td><td>{{ row.c_oi }}</td><td>{{ row.c_chg }}</td>
                <td>{{ row.p_vol }}</td><td>{{ row.p_oi }}</td><td>{{ row.p_chg }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

# Global Storage
last_scan_data = {"time": "Never", "passed": []}

def fetch_nse_data(url):
    headers = {"Accept": "*/*", "Referer": "https://www.nseindia.com/"}
    try:
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        response = session.get(url, headers=headers, timeout=10)
        return response.status_code, response.text
    except: return 500, ""

def perform_scan():
    multiplyNo = 1.25
    passed = []
    today = datetime.today().date()

    for stock in STOCKS_TO_SCAN:
        status1, text1 = fetch_nse_data(f"https://www.nseindia.com/api/option-chain-contract-info?symbol={stock}")
        if status1 != 200: continue
        
        matches = re.findall(r'\d{2}-[A-Za-z]{3}-\d{4}', text1)
        if not matches: continue
        nearest_expiry = min([datetime.strptime(d, "%d-%b-%Y").date() for d in list(set(matches))], key=lambda x: abs(x - today)).strftime("%d-%b-%Y")

        status2, text2 = fetch_nse_data(f"https://www.nseindia.com/api/option-chain-v3?type=Equity&symbol={stock}&expiry={nearest_expiry}")
        if status2 != 200: continue
        
        data = json.loads(text2).get('records', {}).get('data', [])
        
        # Calculate Totals
        t_c_vol = sum(r.get('CE', {}).get('totalTradedVolume', 0) for r in data)
        t_c_oi = sum(r.get('CE', {}).get('openInterest', 0) for r in data)
        t_c_chg = sum(r.get('CE', {}).get('changeinOpenInterest', 0) for r in data)
        t_p_vol = sum(r.get('PE', {}).get('totalTradedVolume', 0) for r in data)
        t_p_oi = sum(r.get('PE', {}).get('openInterest', 0) for r in data)
        t_p_chg = sum(r.get('PE', {}).get('changeinOpenInterest', 0) for r in data)
        
        # Calculate PCR (Put OI / Call OI)
        pcr = round(t_p_oi / t_c_oi, 2) if t_c_oi > 0 else 0

        # Rule Check (Double check all 3 parameters: Vol, OI, ChangeOI)
        signal = None
        # Bullish
        if (t_p_vol >= multiplyNo * t_c_vol) and (t_p_oi >= multiplyNo * t_c_oi) and (t_p_chg >= multiplyNo * t_c_chg):
            signal = "BUY"
        # Bearish
        elif (t_c_vol >= multiplyNo * t_p_vol) and (t_c_oi >= multiplyNo * t_p_oi) and (t_c_chg >= multiplyNo * t_p_chg):
            signal = "SELL"
            
        if signal:
            passed.append({
                "stock": stock, "signal": signal, "pcr": pcr,
                "c_vol": f"{t_c_vol:,}", "c_oi": f"{t_c_oi:,}", "c_chg": f"{t_c_chg:,}",
                "p_vol": f"{t_p_vol:,}", "p_oi": f"{t_p_oi:,}", "p_chg": f"{t_p_chg:,}"
            })
        
        time.sleep(1)
    return passed

@app.route('/')
def index():
    global last_scan_data
    # First time auto-run logic
    if last_scan_data['time'] == "Never":
        results = perform_scan()
        last_scan_data = {"time": datetime.now().strftime("%H:%M:%S"), "passed": results}
        
    return render_template_string(HTML_TEMPLATE, last_scan_time=last_scan_data['time'], passed_stocks=last_scan_data['passed'])

@app.route('/refresh', methods=['POST'])
def refresh():
    global last_scan_data
    results = perform_scan()
    last_scan_data = {"time": datetime.now().strftime("%H:%M:%S"), "passed": results}
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True, port=5001)