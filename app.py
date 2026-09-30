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

latest_scanned_tokens = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Institutional Sniper Terminal - عبد الرحمن</title>
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: Tahoma, sans-serif; margin: 0; padding: 20px; }
        h1 { color: #58a6ff; text-align: center; font-size: 24px; margin-bottom: 20px; }
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
    <h1>⚡ Direct Sniper & Flow Terminal ⚡</h1>
    <table>
        <thead>
            <tr>
                <th>الشبكة</th>
                <th>الرمز المميز</th>
                <th>الحالة</th>
                <th>القيمة السوقية (MCap)</th>
                <th>السيولة ($)</th>
                <th>عقد العملة (CA)</th>
                <th>روابط الفحص</th>
            </tr>
        </thead>
        <tbody>
            {% for item in data %}
            <tr>
                <td><span class="chain-tag">{{ item.chain | upper }}</span></td>
                <td><b>{{ item.name }}</b> ({{ item.symbol }})</td>
                <td class="buy">نشط 🟢</td>
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
                <td colspan="7" style="color: #8b949e; padding: 20px;">جاري جلب البيانات المباشرة للأسواق...</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

def direct_market_scanner():
    global latest_scanned_tokens
    sent_alerts = set()
    
    # استخدام رابط جلب أحدث البروفايلات والتوكنات المضافة مباشرة
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    
    while True:
        temp_list = []
        try:
            res = requests.get(url, timeout=5)
            profiles = res.json()
            
            if isinstance(profiles, list):
                for p in profiles[:20]:
                    ca = p.get("tokenAddress")
                    chain = p.get("chainId", "solana")
                    if not ca:
                        continue
                        
                    # جلب تفاصيل الزوج لكل عقد
                    detail_url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
                    detail_res = requests.get(detail_url, timeout=3)
                    pairs = detail_res.json().get("pairs", [])
                    
                    for pair in pairs:
                        liquidity = pair.get("liquidity", {}).get("usd", 0)
                        mcap = pair.get("marketCap", 0)
                        
                        token_data = {
                            "chain": chain,
                            "name": pair.get("baseToken", {}).get("name", "Unknown"),
                            "symbol": pair.get("baseToken", {}).get("symbol", ""),
                            "ca": ca,
                            "liquidity": liquidity,
                            "mcap": mcap
                        }
                        temp_list.append(token_data)
                        
                        if ca not in sent_alerts:
                            sent_alerts.add(ca)
                            alert_msg = f"""
🎯 **[DIRECT SNIPER ALERT]** 🎯

🌐 **الشبكة:** `{chain.upper()}`
🪙 **العملة:** `{token_data['name']} ({token_data['symbol']})`
📍 **عقد العملة (CA):**
`{ca}`

📊 **البيانات اللحظية:**
• القيمة السوقية: `${mcap:,.0f}`
• السيولة: `${liquidity:,.0f}` 🟢

🔗 **روابط الفحص:**
• [Defined Charts](https://defined.fi/token/{ca})
• [BubbleMaps](https://app.bubblemaps.io/token/{ca})
"""
                            send_telegram_alert(alert_msg)
                            time.sleep(1)
                        break
        except Exception as e:
            print(f"Scanner error: {e}")
            
        if temp_list:
            latest_scanned_tokens = temp_list
            
        time.sleep(45)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, data=latest_scanned_tokens)

if __name__ == "__main__":
    scanner_thread = threading.Thread(target=direct_market_scanner)
    scanner_thread.daemon = True
    scanner_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
