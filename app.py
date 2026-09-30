import os
import requests
from flask import Flask, render_template_string, request
import threading
import time

app = Flask(__name__)

# إعدادات تيليجرام (ضع توكن بوتك ومعرفك هنا)
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

def send_telegram_alert(message):
    if "YOUR_" in TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"خطأ في إرسال التنبيه: {e}")

# تخزين مؤقت للنتائج المرصودة ذات السيولة القوية
latest_scanned_tokens = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>High-Liquidity Institutional Terminal - عبد الرحمن</title>
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: Tahoma, sans-serif; margin: 0; padding: 20px; }
        h1 { color: #58a6ff; text-align: center; font-size: 24px; margin-bottom: 20px; }
        .filter-box { background: #161b22; padding: 15px; border-radius: 8px; margin-bottom: 20px; display: flex; gap: 15px; justify-content: center; align-items: center; border: 1px solid #30363d; }
        input, select { background: #0d1117; color: #fff; border: 1px solid #30363d; padding: 8px 12px; border-radius: 5px; }
        button { background: #238636; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-weight: bold; }
        button:hover { background: #2ea043; }
        table { width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; border: 1px solid #30363d; }
        th, td { padding: 12px 15px; text-align: center; border-bottom: 1px solid #30363d; font-size: 14px; }
        th { background: #21262d; color: #8b949e; }
        tr:hover { background: #1f6feb15; }
        .buy { color: #3fb950; font-weight: bold; }
        .chain-tag { background: #30363d; padding: 3px 8px; border-radius: 4px; font-size: 12px; color: #58a6ff; }
        .ca-link { color: #58a6ff; text-decoration: none; font-family: monospace; }
    </style>
</head>
<body>
    <h1>🐋 High-Liquidity Whale & Flow Terminal 🐋</h1>
    
    <div class="filter-box">
        <form method="GET" action="/">
            <label>الحد الأدنى للسيولة القوية ($):</label>
            <input type="number" name="min_liq" value="{{ min_liq }}">
            <button type="submit">تحديث الفلتر</button>
        </form>
    </div>

    <table>
        <thead>
            <tr>
                <th>الشبكة</th>
                <th>الرمز المميز</th>
                <th>الحالة</th>
                <th>القيمة السوقية (MCap)</th>
                <th>السيولة القوية ($)</th>
                <th>عقد العملة (CA)</th>
                <th>روابط الفحص</th>
            </tr>
        </thead>
        <tbody>
            {% for item in data %}
            <tr>
                <td><span class="chain-tag">{{ item.chain | upper }}</span></td>
                <td><b>{{ item.name }}</b> ({{ item.symbol }})</td>
                <td class="buy">سيولة مؤسسية 🟢</td>
                <td>${{ "{:,.0f}".format(item.mcap) }}</td>
                <td>${{ "{:,.0f}".format(item.liquidity) }}</td>
                <td><span class="ca-link">{{ item.ca }}</span></td>
                <td>
                    <a href="https://defined.fi/token/{{ item.ca }}" target="_blank" style="color: #58a6ff; margin-left: 10px;">Charts</a>
                    <a href="https://app.bubblemaps.io/token/{{ item.ca }}" target="_blank" style="color: #f0883e;">BubbleMaps</a>
                </td>
            </tr>
            {% else %}
            <tr>
                <td colspan="7" style="color: #8b949e; padding: 20px;">جاري رصد صفقات السيولة القوية عبر السلاسل...</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

def whale_flow_scanner():
    """
    ماسح يركز على السيولة الضخمة والقوية حصراً مع إرسال تنبيهات تليجرام
    """
    global latest_scanned_tokens
    queries = ["solana", "ethereum", "bsc", "base"]
    sent_alerts = set() # لعدم تكرار إرسال نفس التنبيه
    
    while True:
        temp_list = []
        seen_cas = set()
        
        for q in queries:
            url = f"https://api.dexscreener.com/latest/dex/search?q={q}"
            try:
                res = requests.get(url, timeout=4)
                pairs = res.json().get("pairs", [])
                for pair in pairs:
                    chain = pair.get("chainId", "unknown")
                    ca = pair.get("baseToken", {}).get("address", "")
                    
                    if not ca or ca in seen_cas:
                        continue
                    seen_cas.add(ca)
                    
                    liquidity = pair.get("liquidity", {}).get("usd", 0)
                    mcap = pair.get("marketCap", 0)
                    
                    # 🐋 فلتر السيولة القوية حصراً (بين 100 ألف و 10 مليون دولار)
                    if liquidity < 100000 or liquidity > 10000000:
                        continue
                        
                    token_data = {
                        "chain": chain,
                        "name": pair.get("baseToken", {}).get("name", "Unknown"),
                        "symbol": pair.get("baseToken", {}).get("symbol", ""),
                        "ca": ca,
                        "liquidity": liquidity,
                        "mcap": mcap
                    }
                    temp_list.append(token_data)
                    
                    # إرسال تنبيه فوري لتليجرام إذا كانت الفرصة جديدة
                    if ca not in sent_alerts:
                        sent_alerts.add(ca)
                        alert_msg = f"""
🐋 **[HIGH LIQUIDITY WHALE ALERT]** 🐋

🌐 **الشبكة:** `{chain.upper()}`
🪙 **العملة:** `{token_data['name']} ({token_data['symbol']})`
📍 **عقد العملة (CA):**
`{ca}`

📊 **البيانات المالية القوية:**
• القيمة السوقية: `${mcap:,.0f}`
• السيولة المتاحة: `${liquidity:,.0f}` 🟢

🔗 **روابط الفحص والتحقق:**
• [Defined Charts](https://defined.fi/token/{ca})
• [BubbleMaps](https://app.bubblemaps.io/token/{ca})
"""
                        send_telegram_alert(alert_msg)
                        time.sleep(1)
                        
            except Exception as e:
                print(f"Scanner error: {e}")
                
        if temp_list:
            latest_scanned_tokens = temp_list[:50]
            
        time.sleep(30)

@app.route('/')
def index():
    min_liq = request.args.get('min_liq', '100000')
    try:
        min_val = float(min_liq)
    except:
        min_val = 100000.0
        
    filtered = [t for t in latest_scanned_tokens if t['liquidity'] >= min_val]
    return render_template_string(HTML_TEMPLATE, data=filtered, min_liq=min_liq)

if __name__ == "__main__":
    scanner_thread = threading.Thread(target=whale_flow_scanner)
    scanner_thread.daemon = True
    scanner_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
