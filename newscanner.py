from flask import Flask, render_template_string, request, jsonify
from curl_cffi import requests
from datetime import datetime
import re
import json
import time

app = Flask(__name__)

STOCKS_TO_SCAN = [
  "360ONE", "ABB", "ABCAPITAL", "ADANIENSOL", "ADANIENT", "ADANIGREEN", "ADANIPORTS", "ADANIPOWER", "ALKEM", "AMBER", 
  "AMBUJACEM", "ANGELONE", "APLAPOLLO", "APOLLOHOSP", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "AUBANK", "AUROPHARMA", 
  "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJAJHLDNG", "BAJFINANCE", "BANDHANBNK", "BANKBARODA", "BANKINDIA", "BDL", 
  "BEL", "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BLUESTARCO", "BOSCHLTD", "BPCL", "BRITANNIA", "BSE", "CAMS", 
  "CANBK", "CDSL", "CGPOWER", "CHOLAFIN", "CIPLA", "COALINDIA", "COCHINSHIP", "COFORGE", "COLPAL", "CONCOR", "CROMPTON", 
  "CUMMINSIND", "DABUR", "DALBHARAT", "DELHIVERY", "DIVISLAB", "DIXON", "DLF", "DMART", "DRREDDY", "EICHERMOT", 
  "ETERNAL", "EXIDEIND", "FEDERALBNK", "FORCEMOT", "FORTIS", "GAIL", "GLENMARK", "GMRAIRPORT", "GODFRYPHLP", "GODREJCP", 
  "GODREJPROP", "GRASIM", "GVT&D", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", 
  "HINDALCO", "HINDPETRO", "HINDUNILVR", "HINDZINC", "HYUNDAI", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDEA", 
  "IDFCFIRSTB", "IEX", "INDHOTEL", "INDIANB", "INDIGO", "INDUSINDBK", "INDUSTOWER", "INFY", "INOXWIND", "IOC", "IREDA", 
  "IRFC", "ITC", "JINDALSTEL", "JIOFIN", "JSWENERGY", "JSWSTEEL", "JUBLFOOD", "KALYANKJIL", "KAYNES", "KEI", "KFINTECH", 
  "KOTAKBANK", "KPITTECH", "LAURUSLABS", "LICHSGFIN", "LICI", "LODHA", "LT", "LTF", "LTM", "LUPIN", "M&M", "MANAPPURAM", 
  "MANKIND", "MARICO", "MARUTI", "MAXHEALTH", "MAZDOCK", "MCX", "MFSL", "MOTHERSON", "MOTILALOFS", "MPHASIS", 
  "MUTHOOTFIN", "NAM-INDIA", "NATIONALUM", "NAUKRI", "NBCC", "NESTLEIND", "NHPC", "NMDC", "NTPC", "NUVAMA", "NYKAA", 
  "OBEROIRLTY", "OFSS", "OIL", "ONGC", "PAGEIND", "PATANJALI", "PAYTM", "PERSISTENT", "PETRONET", "PFC", "PGEL", 
  "PHOENIXLTD", "PIDILITIND", "PIIND", "PNB", "PNBHOUSING", "POLICYBZR", "POLYCAB", "POWERGRID", "POWERINDIA", 
  "PREMIERENE", "PRESTIGE", "RADICO", "RBLBANK", "RECLTD", "RELIANCE", "RVNL", "SAIL", "SAMMAANCAP", "SBICARD", 
  "SBILIFE", "SBIN", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SOLARINDS", "SONACOMS", "SRF", "SUNPHARMA", "SUPREMEIND", 
  "SUZLON", "SWIGGY", "TATACONSUM", "TATAELXSI", "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TIINDIA", "TITAN", "TMPV", 
  "TORNTPHARM", "TRENT", "TVSMOTOR", "ULTRACEMCO", "UNIONBANK", "UNITDSPR", "UNOMINDA", "UPL", "VBL", "VEDL", "VMM", 
  "VOLTAS", "WAAREEENER", "WIPRO", "YESBANK", "ZYDUSLIFE"
]
session = requests.Session(impersonate="chrome120")

# --- HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Stock Scanner Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; padding: 20px; background: #f4f4f4; }
        .container { max-width: 1450px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .header-controls { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; background: #e9ecef; padding: 15px; border-radius: 6px; }
        .btn-refresh { padding: 12px 25px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 5px; font-weight: bold; }
        .btn-refresh:disabled { background: #6c757d; cursor: not-allowed; }
        
        .search-box { padding: 10px; font-size: 15px; width: 250px; border: 1px solid #ccc; border-radius: 5px; outline: none; }
        .search-box:disabled { background-color: #d6d8db; cursor: not-allowed; opacity: 0.6; }
        
        .count-badge { background: #ffc107; color: #000; padding: 6px 15px; border-radius: 20px; font-size: 18px; margin-left: 10px; font-weight: bold; border: 1px solid #e0a800; }

        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 10px 8px; text-align: center; font-size: 14px; }
        th { background-color: #004085; color: white; position: sticky; top: 0; z-index: 2; }
        .top-strikes-hdr { background-color: #17a2b8; color: white; }
        .BUY { color: green; font-weight: bold; } .SELL { color: red; font-weight: bold; }
        
        .strike-info { font-weight: bold; color: #0056b3; background-color: #f8f9fa; }
        .strike-info-put { font-weight: bold; color: #d35400; background-color: #f8f9fa; }
        
        /* NEW STYLES FOR HIGHLIGHTING */
        tr.highlight-row td { background-color: #fff8e1 !important; }
        mark { background-color: #ffeb3b; padding: 3px 6px; border-radius: 4px; font-weight: 900; border: 1px solid #d39e00; color: #000; box-shadow: 0 0 5px rgba(255,193,7,0.5);}
        
        #status { font-weight: bold; color: #d35400; font-size: 16px; margin: 15px 0 5px 0; }
        #autoScanLabel { font-weight: bold; color: #6c757d; font-size: 14px; margin-bottom: 15px; }
        .loader { display: inline-block; margin-left: 10px; width: 16px; height: 16px; border: 3px solid #f3f3f3; border-top: 3px solid #007bff; border-radius: 50%; animation: spin 1s linear infinite; vertical-align: middle;}
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <h2>🎯 Master Stock Scanner</h2>
        <button id="scanBtn" class="btn-refresh" onclick="startScan()">Refresh Scan Data</button>
        <div id="status">Waiting to start...</div>
        <div id="autoScanLabel">⏱️ Timer starting...</div>

        <div class="header-controls">
            <h3 style="margin: 0;">Stocks Passing Rule: <span id="passCount" class="count-badge">0</span></h3>
            <input type="text" id="searchInput" class="search-box" placeholder="🔍 Search Symbol..." disabled onkeyup="filterTable()">
        </div>

        <table id="resultTable">
            <thead>
                <tr>
                    <th>Stock</th>
                    <th>LTP</th>
                    <th>Signal</th>
                    <th>PCR</th>
                    <th>Call Vol</th>
                    <th>Call OI</th>
                    <th>Call Chg OI</th>
                    <th class="top-strikes-hdr">Top Selling Strikes<br><small>(Vol / OI / Chg)</small></th>
                    <th>Put Chg OI</th>
                    <th>Put OI</th>
                    <th>Put Vol</th>
                    <th class="top-strikes-hdr">Top Buying Strikes<br><small>(Vol / OI / Chg)</small></th>
                </tr>
            </thead>
            <tbody>
                </tbody>
        </table>
    </div>

    <script>
        let currentBatch = 0;
        let totalStocks = {{ total_stocks }};
        let isScanning = false;
        let allPassedStocks = []; 
        let lastScanCompleteTime = null;

        window.onload = function() {
            if (!sessionStorage.getItem('hasRunBefore')) {
                sessionStorage.setItem('hasRunBefore', 'true');
                startScan();
            } else {
                document.getElementById('status').innerHTML = "Click <b>Refresh Scan Data</b> to start scanning.";
                lastScanCompleteTime = Date.now(); 
            }
            
            setInterval(autoScanManager, 45000);
        };

        function autoScanManager() {
            if (isScanning) return; 

            let now = new Date();
            let hours = now.getHours();
            let minutes = now.getMinutes();
            let currentTotalMinutes = hours * 60 + minutes;

            // Market hours: 9:00 AM (540 mins) to 4:00 PM (960 mins)
            let isMarketOpen = (currentTotalMinutes >= 540 && currentTotalMinutes <= 960);
            let autoLabel = document.getElementById('autoScanLabel');

            if (!isMarketOpen) {
                autoLabel.innerHTML = "⏸️ Auto-Scan Paused (Outside Market Hours 9 AM - 4 PM)";
                return;
            }

            if (!lastScanCompleteTime) {
                autoLabel.innerHTML = "⏳ Waiting for the first scan to complete...";
                return;
            }

            let timeSinceLastScanMs = now.getTime() - lastScanCompleteTime;
            let minutesElapsed = Math.floor(timeSinceLastScanMs / 60000);
            let minutesLeft = 30 - minutesElapsed;

            if (timeSinceLastScanMs >= (30 * 60 * 1000)) { 
                autoLabel.innerHTML = "🔄 Auto-Scan Triggered!";
                startScan();
            } else {
                autoLabel.innerHTML = `⏱️ Next Auto-Scan in ~${minutesLeft} minute(s)`;
            }
        }

        async function startScan() {
            if (isScanning) return;
            isScanning = true;
            currentBatch = 0;
            allPassedStocks = []; 
            
            document.getElementById('scanBtn').disabled = true;
            let searchInput = document.getElementById('searchInput');
            searchInput.value = "";
            searchInput.disabled = true;
            searchInput.placeholder = "Wait for scan to finish...";
            
            updateCount(0);
            renderTable(allPassedStocks); 
            await fetchNextBatch();
        }

        async function fetchNextBatch() {
            let startIdx = currentBatch * 30;
            let endIdx = Math.min(startIdx + 30, totalStocks);
            
            document.getElementById('status').innerHTML = `Scanning batch ${currentBatch + 1} (Stocks ${startIdx + 1} to ${endIdx} of ${totalStocks})... <div class="loader"></div>`;
            
            try {
                let response = await fetch('/scan_batch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ batch: currentBatch })
                });
                
                let data = await response.json();
                
                allPassedStocks = allPassedStocks.concat(data.passed);
                allPassedStocks.sort((a, b) => Number(b.raw_total_vol) - Number(a.raw_total_vol));
                
                updateCount(allPassedStocks.length);
                renderTable(allPassedStocks); 

                if (data.is_last) {
                    document.getElementById('status').innerHTML = `<span style="color:green;">✅ Scan Complete! Finished scanning ${totalStocks} stocks. Sorted by Highest Volume.</span>`;
                    document.getElementById('scanBtn').disabled = false;
                    isScanning = false;
                    
                    let searchInput = document.getElementById('searchInput');
                    searchInput.disabled = false;
                    searchInput.placeholder = "🔍 Search Symbol...";
                    
                    lastScanCompleteTime = Date.now();
                    autoScanManager();
                    
                } else {
                    currentBatch++;
                    fetchNextBatch(); 
                }
            } catch (error) {
                document.getElementById('status').innerHTML = `<span style="color:red;">❌ Network Error occurred. Scan paused.</span>`;
                document.getElementById('scanBtn').disabled = false;
                isScanning = false;
            }
        }

        function renderTable(dataArray) {
            let tbody = document.getElementById('resultTable').querySelector('tbody');
            tbody.innerHTML = '';
            
            if(dataArray.length === 0 && !isScanning && currentBatch > 0) {
                tbody.innerHTML = '<tr><td colspan="12" style="color:gray;">No stocks matched the criteria.</td></tr>';
                return;
            }

            dataArray.forEach(row => {
                let hl = row.highlight_data;
                let rowClass = hl ? "highlight-row" : "";
                
                // Construct Call Strikes string with highlight logic
                let c_vol = row.strike_c_vol;
                let c_oi = row.strike_c_oi;
                let c_chg = row.strike_c_chg;
                
                if (hl && hl.side === 'C') {
                    if (hl.type === 'vol') c_vol = `<mark>${c_vol}</mark>`;
                    else if (hl.type === 'oi') c_oi = `<mark>${c_oi}</mark>`;
                    else if (hl.type === 'chg') c_chg = `<mark>${c_chg}</mark>`;
                }
                let call_strikes = `${c_vol} / ${c_oi} / ${c_chg}`;
                
                // Construct Put Strikes string with highlight logic
                let p_vol = row.strike_p_vol;
                let p_oi = row.strike_p_oi;
                let p_chg = row.strike_p_chg;
                
                if (hl && hl.side === 'P') {
                    if (hl.type === 'vol') p_vol = `<mark>${p_vol}</mark>`;
                    else if (hl.type === 'oi') p_oi = `<mark>${p_oi}</mark>`;
                    else if (hl.type === 'chg') p_chg = `<mark>${p_chg}</mark>`;
                }
                let put_strikes = `${p_vol} / ${p_oi} / ${p_chg}`;

                let tr = document.createElement('tr');
                tr.className = rowClass;
                tr.innerHTML = `
                    <td><b>${row.stock}</b></td>
                    <td><b>₹${row.underlying}</b></td>
                    <td class="${row.signal}">${row.signal}</td>
                    <td>${row.pcr}</td>
                    <td>${row.c_vol}</td>
                    <td>${row.c_oi}</td>
                    <td>${row.c_chg}</td>
                    <td class="strike-info">${call_strikes}</td>
                    <td>${row.p_chg}</td>
                    <td>${row.p_oi}</td>
                    <td>${row.p_vol}</td>
                    <td class="strike-info-put">${put_strikes}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        function filterTable() {
            let query = document.getElementById('searchInput').value.toUpperCase().trim();
            let filtered = allPassedStocks.filter(row => row.stock.includes(query));
            renderTable(filtered);
            updateCount(filtered.length);
        }

        function updateCount(count) {
            document.getElementById('passCount').innerText = count;
        }
    </script>
</body>
</html>
"""

def fetch_nse_data(url):
    headers = {"Accept": "*/*", "Referer": "https://www.nseindia.com/"}
    try:
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        response = session.get(url, headers=headers, timeout=10)
        return response.status_code, response.text
    except: return 500, ""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, total_stocks=len(STOCKS_TO_SCAN))

@app.route('/scan_batch', methods=['POST'])
def scan_batch():
    batch_idx = request.json.get('batch', 0)
    batch_size = 30
    
    start = batch_idx * batch_size
    end = start + batch_size
    chunk = STOCKS_TO_SCAN[start:end]
    
    passed = []
    multiplyNo = 2
    today = datetime.today().date()

    for stock in chunk:
        print(f"Scanning {stock}...")
        status1, text1 = fetch_nse_data(f"https://www.nseindia.com/api/option-chain-contract-info?symbol={stock}")
        if status1 != 200: continue
        
        matches = re.findall(r'\d{2}-[A-Za-z]{3}-\d{4}', text1)
        if not matches: continue
        nearest_expiry = min([datetime.strptime(d, "%d-%b-%Y").date() for d in list(set(matches))], key=lambda x: abs(x - today)).strftime("%d-%b-%Y")

        status2, text2 = fetch_nse_data(f"https://www.nseindia.com/api/option-chain-v3?type=Equity&symbol={stock}&expiry={nearest_expiry}")
        if status2 != 200: continue
        
        try:
            json_response = json.loads(text2)
            data = json_response.get('records', {}).get('data', [])
            underlying_price = json_response.get('records', {}).get('underlyingValue', 0)
        except Exception as e:
            continue
        
        t_c_vol = sum(r.get('CE', {}).get('totalTradedVolume', 0) for r in data)
        t_c_oi = sum(r.get('CE', {}).get('openInterest', 0) for r in data)
        t_c_chg = sum(r.get('CE', {}).get('changeinOpenInterest', 0) for r in data)
        
        t_p_vol = sum(r.get('PE', {}).get('totalTradedVolume', 0) for r in data)
        t_p_oi = sum(r.get('PE', {}).get('openInterest', 0) for r in data)
        t_p_chg = sum(r.get('PE', {}).get('changeinOpenInterest', 0) for r in data)
        
        pcr = round(t_p_oi / t_c_oi, 2) if t_c_oi > 0 else 0
        total_activity_vol = t_c_vol + t_p_vol 

        signal = None
        
        # EXACT MATHEMATICAL LOGIC
        if (t_p_vol >= multiplyNo * t_c_vol) and (t_p_oi >= multiplyNo * t_c_oi): #and (t_p_chg >= multiplyNo * t_c_chg):
            signal = "BUY"
        elif (t_c_vol >= multiplyNo * t_p_vol) and (t_c_oi >= multiplyNo * t_p_oi): #and (t_c_chg >= multiplyNo * t_p_chg):
            signal = "SELL"
            
        if signal:
            # --- HIGHEST STRIKES LOGIC ---
            max_c_vol = max_c_oi = -1
            max_c_chg = float('-inf')
            strike_c_vol = strike_c_oi = strike_c_chg = "-"
            
            max_p_vol = max_p_oi = -1
            max_p_chg = float('-inf')
            strike_p_vol = strike_p_oi = strike_p_chg = "-"
            
            for row in data:
                strike = row.get('strikePrice')
                
                # Check Calls
                ce = row.get('CE', {})
                if ce:
                    if ce.get('totalTradedVolume', 0) > max_c_vol:
                        max_c_vol = ce.get('totalTradedVolume', 0)
                        strike_c_vol = strike
                    if ce.get('openInterest', 0) > max_c_oi:
                        max_c_oi = ce.get('openInterest', 0)
                        strike_c_oi = strike
                    if ce.get('changeinOpenInterest', 0) > max_c_chg:
                        max_c_chg = ce.get('changeinOpenInterest', 0)
                        strike_c_chg = strike
                        
                # Check Puts
                pe = row.get('PE', {})
                if pe:
                    if pe.get('totalTradedVolume', 0) > max_p_vol:
                        max_p_vol = pe.get('totalTradedVolume', 0)
                        strike_p_vol = strike
                    if pe.get('openInterest', 0) > max_p_oi:
                        max_p_oi = pe.get('openInterest', 0)
                        strike_p_oi = strike
                    if pe.get('changeinOpenInterest', 0) > max_p_chg:
                        max_p_chg = pe.get('changeinOpenInterest', 0)
                        strike_p_chg = strike
            
            # --- NEW: 5% PROXIMITY HIGHLIGHT LOGIC ---
            highlight_data = None
            if underlying_price > 0:
                # Create a list of available valid strikes
                candidates = []
                if strike_c_vol != "-": candidates.append(('C', 'vol', strike_c_vol))
                if strike_c_oi != "-": candidates.append(('C', 'oi', strike_c_oi))
                if strike_c_chg != "-": candidates.append(('C', 'chg', strike_c_chg))
                if strike_p_vol != "-": candidates.append(('P', 'vol', strike_p_vol))
                if strike_p_oi != "-": candidates.append(('P', 'oi', strike_p_oi))
                if strike_p_chg != "-": candidates.append(('P', 'chg', strike_p_chg))
                
                min_diff = float('inf')
                best_candidate = None
                
                # Find the one strike with the absolute minimum difference
                for side, stype, val in candidates:
                    diff = abs(val - underlying_price) / underlying_price * 100
                    # Ensures we pick strictly "only 1" even if there are ties
                    if diff < min_diff:
                        min_diff = diff
                        best_candidate = (side, stype, val)
                
                # Check if the shortest difference is within max 0.5%
                if best_candidate and min_diff <= 0.5:
                    highlight_data = {
                        'side': best_candidate[0],
                        'type': best_candidate[1]
                    }

            # Append complete data including Highlight info
            passed.append({
                "stock": stock, 
                "underlying": underlying_price, 
                "signal": signal, 
                "pcr": pcr,
                "c_vol": f"{t_c_vol:,}", "c_oi": f"{t_c_oi:,}", "c_chg": f"{t_c_chg:,}",
                "strike_c_vol": strike_c_vol, "strike_c_oi": strike_c_oi, "strike_c_chg": strike_c_chg,
                "p_chg": f"{t_p_chg:,}", "p_oi": f"{t_p_oi:,}", "p_vol": f"{t_p_vol:,}",
                "strike_p_vol": strike_p_vol, "strike_p_oi": strike_p_oi, "strike_p_chg": strike_p_chg,
                "raw_total_vol": total_activity_vol,
                "highlight_data": highlight_data # <-- Passes highlight info to HTML
            })
        
        time.sleep(1)

    is_last = end >= len(STOCKS_TO_SCAN)
    return jsonify({"passed": passed, "is_last": is_last})

if __name__ == "__main__":
    app.run(debug=True, port=5001)