from flask import Flask, request, render_template_string
from curl_cffi import requests
from datetime import datetime, timedelta
import re
import json
import time

app = Flask(__name__)
session = requests.Session(impersonate="chrome120")

# --- HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>NiftyTrader Clone - OI Chain</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        h2 { text-align: center; color: #0056b3; margin-top: 0;}
        .form-box { display: flex; justify-content: center; align-items: center; gap: 15px; margin-bottom: 20px; padding: 15px; background: #e9ecef; border-radius: 5px;}
        input[type="text"], input[type="date"] { padding: 10px; font-size: 16px; border: 1px solid #ccc; border-radius: 5px; outline: none; }
        button { padding: 10px 25px; font-size: 16px; background-color: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;}
        button:hover { background-color: #0056b3; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; text-align: right; }
        th, td { border: 1px solid #ddd; padding: 8px 10px; }
        th { background-color: #004085; color: white; text-align: center; }
        .calls-hdr { color: #28a745; background-color: #f8f9fa; font-weight: bold; text-align: center; font-size: 15px;}
        .puts-hdr { color: #dc3545; background-color: #f8f9fa; font-weight: bold; text-align: center; font-size: 15px;}
        
        .strike { background-color: #e9ecef; font-weight: bold; color: #000; text-align: center; font-size: 14px;}
        .itm { background-color: #fff9c4; } /* Halka yellow ITM ke liye */
        
        .total-row { background-color: #d1ecf1; font-weight: bold; color: #0c5460; }
        .msg-box { padding: 15px; border-radius: 5px; text-align: center; margin-bottom: 15px; font-weight: bold;}
        .alert-error { background-color: #f8d7da; color: #721c24; }
        .alert-success { background-color: #d4edda; color: #155724; }
        .val-green { color: green; }
        .val-red { color: red; }
    </style>
</head>
<body>
    <div class="container">
        <h2>📈 Full Option Chain Analyzer</h2>
        
        <form class="form-box" method="POST">
            <label><b>Symbol:</b></label>
            <input type="text" name="symbol" placeholder="e.g. ADANIENSOL" value="{{ symbol }}" required>
            
            <label><b>Expiry Date:</b></label>
            <input type="date" name="expiry_date" value="{{ date_input }}" min="{{ min_date }}" max="{{ max_date }}" required>
            
            <button type="submit">Get Data</button>
        </form>

        {% if error %}
            <div class="msg-box alert-error">{{ error }}</div>
        {% endif %}

        {% if info_msg %}
            <div class="msg-box alert-success">{{ info_msg }}</div>
        {% endif %}

        {% if data %}
            <div style="display:flex; justify-content:space-between; margin-bottom: 10px; font-weight: bold;">
                <span>Underlying Price: ₹{{ underlying }}</span>
                <span>Showing Exact Expiry: <span style="color:blue;">{{ final_expiry }}</span></span>
            </div>
            
            <table>
                <tr>
                    <td colspan="5" class="calls-hdr">CALLS</td>
                    <td class="strike">STRIKE</td>
                    <td colspan="5" class="puts-hdr">PUTS</td>
                </tr>
                <tr>
                    <th>VOLUME</th><th>OI</th><th>CHG IN OI</th><th>IV</th><th>LTP</th>
                    <th class="strike">PRICE</th>
                    <th>LTP</th><th>IV</th><th>CHG IN OI</th><th>OI</th><th>VOLUME</th>
                </tr>
                {% for row in data %}
                <tr>
                    <td class="{{ 'itm' if row.strikePrice < underlying else '' }}">{{ row.CE.totalTradedVolume if row.CE else '-' }}</td>
                    <td class="{{ 'itm' if row.strikePrice < underlying else '' }}">{{ row.CE.openInterest if row.CE else '-' }}</td>
                    <td class="{{ 'itm' if row.strikePrice < underlying else '' }} {{ 'val-green' if row.CE and row.CE.changeinOpenInterest > 0 else 'val-red' }}">
                        {{ row.CE.changeinOpenInterest if row.CE else '-' }}
                    </td>
                    <td class="{{ 'itm' if row.strikePrice < underlying else '' }}">{{ row.CE.impliedVolatility if row.CE else '-' }}</td>
                    <td class="{{ 'itm' if row.strikePrice < underlying else '' }}"><b>{{ row.CE.lastPrice if row.CE else '-' }}</b></td>
                    
                    <td class="strike">{{ row.strikePrice }}</td>
                    
                    <td class="{{ 'itm' if row.strikePrice > underlying else '' }}"><b>{{ row.PE.lastPrice if row.PE else '-' }}</b></td>
                    <td class="{{ 'itm' if row.strikePrice > underlying else '' }}">{{ row.PE.impliedVolatility if row.PE else '-' }}</td>
                    <td class="{{ 'itm' if row.strikePrice > underlying else '' }} {{ 'val-green' if row.PE and row.PE.changeinOpenInterest > 0 else 'val-red' }}">
                        {{ row.PE.changeinOpenInterest if row.PE else '-' }}
                    </td>
                    <td class="{{ 'itm' if row.strikePrice > underlying else '' }}">{{ row.PE.openInterest if row.PE else '-' }}</td>
                    <td class="{{ 'itm' if row.strikePrice > underlying else '' }}">{{ row.PE.totalTradedVolume if row.PE else '-' }}</td>
                </tr>
                {% endfor %}
                
                <tr class="total-row">
                    <td>{{ totals.c_vol }}</td>
                    <td>{{ totals.c_oi }}</td>
                    <td>{{ totals.c_chg_oi }}</td>
                    <td>-</td>
                    <td>-</td>
                    <td class="strike">TOTAL</td>
                    <td>-</td>
                    <td>-</td>
                    <td>{{ totals.p_chg_oi }}</td>
                    <td>{{ totals.p_oi }}</td>
                    <td>{{ totals.p_vol }}</td>
                </tr>
            </table>
        {% endif %}
    </div>
</body>
</html>
"""

def fetch_nse_url(url):
    headers = {"Accept": "*/*", "User-Agent": "Mozilla/5.0"}
    try:
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        time.sleep(0.5)
        response = session.get(url, headers=headers, timeout=10)
        return response.status_code, response.text
    except Exception as e:
        return 500, str(e)

@app.route('/', methods=['GET', 'POST'])
def index():
    # Aaj ki date aur 45 din baad ki date calculate karna
    today = datetime.today().date()
    max_date = today + timedelta(days=45)
    
    symbol = ""
    date_input = today.strftime("%Y-%m-%d")
    
    error = None
    info_msg = None
    data = None
    totals = {}
    underlying = 0
    final_expiry = ""

    if request.method == 'POST':
        symbol = request.form.get('symbol').upper().strip()
        date_input = request.form.get('expiry_date')
        
        try:
            selected_dt = datetime.strptime(date_input, "%Y-%m-%d").date()
        except:
            selected_dt = today

        # Backend Validation (Agar koi HTML manipulate karke galat date bhej de)
        if selected_dt < today:
            error = "Back dates are not allowed!"
        elif selected_dt > max_date:
            error = "Cannot select a date more than 45 days in the future!"
        else:
            # API 1: Fetch Valid Expiry Dates
            url_api1 = f"https://www.nseindia.com/api/option-chain-contract-info?symbol={symbol}"
            status1, text1 = fetch_nse_url(url_api1)
            
            if status1 == 200:
                # Regex se valid dates nikalna
                matches = re.findall(r'\d{2}-[A-Za-z]{3}-\d{4}', text1)
                valid_dates = list(set(matches))
                
                if not valid_dates:
                    error = f"No active contracts found for {symbol}."
                else:
                    # Nearest Expiry Date Logic
                    valid_dt_objs = [datetime.strptime(d, "%d-%b-%Y").date() for d in valid_dates]
                    nearest_dt = min(valid_dt_objs, key=lambda x: abs(x - selected_dt))
                    final_expiry = nearest_dt.strftime("%d-%b-%Y")
                    
                    if nearest_dt != selected_dt:
                        info_msg = f"Your selected date ({selected_dt.strftime('%d-%b-%Y')}) was not an expiry day. Automatically snapped to the nearest valid expiry: {final_expiry}"
                    else:
                        info_msg = f"Data fetched successfully for {final_expiry}."

                    # API 2: Fetch Full Option Chain
                    url_api2 = f"https://www.nseindia.com/api/option-chain-v3?type=Equity&symbol={symbol}&expiry={final_expiry}"
                    status2, text2 = fetch_nse_url(url_api2)
                    
                    if status2 == 200:
                        try:
                            json_data = json.loads(text2)
                            data = json_data.get('records', {}).get('data', [])
                            underlying = json_data.get('records', {}).get('underlyingValue', 0)
                            
                            # Calculate Grand Totals
                            t_c_vol = sum(row.get('CE', {}).get('totalTradedVolume', 0) for row in data)
                            t_c_oi = sum(row.get('CE', {}).get('openInterest', 0) for row in data)
                            t_c_chg_oi = sum(row.get('CE', {}).get('changeinOpenInterest', 0) for row in data)
                            
                            t_p_vol = sum(row.get('PE', {}).get('totalTradedVolume', 0) for row in data)
                            t_p_oi = sum(row.get('PE', {}).get('openInterest', 0) for row in data)
                            t_p_chg_oi = sum(row.get('PE', {}).get('changeinOpenInterest', 0) for row in data)
                            
                            totals = {
                                "c_vol": f"{t_c_vol:,}", "c_oi": f"{t_c_oi:,}", "c_chg_oi": f"{t_c_chg_oi:,}",
                                "p_vol": f"{t_p_vol:,}", "p_oi": f"{t_p_oi:,}", "p_chg_oi": f"{t_p_chg_oi:,}"
                            }
                        except Exception as e:
                            error = f"Failed to parse Option Chain JSON. Error: {str(e)}"
                    else:
                        error = f"API 2 Blocked (Code {status2}). Please try again."
            else:
                error = f"API 1 Blocked (Code {status1}). Could not verify expiry dates."

    return render_template_string(
        HTML_TEMPLATE, 
        symbol=symbol, 
        date_input=date_input, 
        min_date=today.strftime("%Y-%m-%d"), 
        max_date=max_date.strftime("%Y-%m-%d"),
        error=error, 
        info_msg=info_msg,
        data=data, 
        totals=totals,
        underlying=underlying,
        final_expiry=final_expiry
    )

if __name__ == "__main__":
    print("🚀 Server Started! Open: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)