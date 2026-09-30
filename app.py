import os
import requests
from flask import Flask, render_template_string, request
import threading
import time

app = Flask('')

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
        requests.post(url, json=payload, timeout=1.5)
    except Exception:
        pass

# قائمة تخزين مؤقت للعملات المرصودة بأعلى سرعة
multichain_tokens = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="5"> <!-- تحديث تلقائي فائق السرعة كل 5 ثوانٍ -->
    <title>Multi-Chain Lightning Sniper - عبد الرحمن</title>
    <style>
        body { background-color: #030508; color: #00ffcc; font-family: 'Courier New', monospace; margin: 0; padding: 15px; }
        h1 { color: #ff0055; text-align: center; font-size: 20px; text-transform: uppercase; letter-spacing: 2px; }
        .status-box { background: #0d1117; padding: 8px; border: 1px solid #00ffcc; text-align: center; margin-bottom: 15px; font-size: 12px; color: #fff; }
        table { width: 100%; border-collapse: collapse; background: #0d1117; border-radius: 6px; overflow: hidden; border: 1px solid #21262d; }
        th, td { padding: 8px 10px; text-align: center; border-bottom: 1px solid #21262d; font-size: 12px; }
        th { background: #161b22; color: #8b949e; }
        tr:hover { background: #00ffcc15; }
        .chain-badge { background: #7928ca; padding: 2px 6px; border-radius: 4px; font-size: 11px; color: #fff; font-weight: bold; }
        .speed-tag { color: #ff0055; font-weight: bold; animation: flash 0.8s infinite; }
        .ca-box { color: #58a6ff; background: #010409; padding: 2px 4px; border-radius: 3px; border: 1px solid #30363d; font-size: 11px; }
        @keyframes flash { 0% { opacity: 1; } 50% { opacity: 0.2; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <h1>⚡ MULTI-CHAIN LIGHTNING SNIPER (جميع السلاسل - رصد لحظي) ⚡</h1>
    
    <div class="status-box">
        🌐 يراقب كافة السلاسل (Solana, Base, ETH, BSC) بأعلى تردد زمني | تحديث الواجهة: كل 5 ثوانٍ
    </div>

    <table>
        <thead>
            <tr>
                <th>الشبكة</th>
                <th>الرمز المميز</th>
                <th>الحالة</th>
                <th>القيمة السوقية</th>
                <th>السيولة ($)</th>
                <th>عقد العملة (CA)</th>
                <th>التنفيذ السريع</th>
            </tr>
        </thead>
        <tbody>
            {% for item in data %}
            <tr>
                <td><span class="chain-badge">{{ item.chain | upper }}</span></td>
                <td>{{ item.name }} (<b>{{ item.symbol }}</b>)</td>
                <td class="speed-tag">انطلاقة مبكرة 🔥</td>
                <td>${{ "{:,.0f}".format(item.mcap) }}</td>
                <td>${{ "{:,.0f}".format(item.liquidity) }}</td>
                <td><span class="ca-box">{{ item.ca }}</span></td>
                <td>
                    <a href="https://defined.fi/token/{{ item.ca }}" target="_blank" style="color: #58a6ff; text-decoration: none;">Charts</a> | 
                    <a href="https://app.bubblemaps.io/token/{{ item.ca }}" target="_blank" style="color: #f0883e; text-decoration: none;">BubbleMaps</a>
                </td>
            </tr>
            {% else %}
            <tr>
                <td colspan="7" style="color: #8b949e; padding: 20px;">جاري رصد أحدث الصفقات والانطلاقات عبر جميع الشبكات...</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

def multichain_lightning_engine():
    global multichain_tokens
    seen_addresses = set()
    
    # مصادر متعددة لضمان شمولية جميع السلاسل والسرعة القصوى
    endpoints = [
        "https://api.dexscreener.com/token-profiles/latest/v1",
        "https://api.dexscreener.com/latest/dex/search?q=solana",
        "https://api.dexscreener.com/latest/dex/search?q=base",
        "https://api.dexscreener.com/latest/dex/search?q=ethereum"
    ]
    
    while True:
        temp_results = []
        for endpoint in endpoints:
            try:
                res = requests.get(endpoint, timeout=2.5)
                data = res.json()
                
                items = data if isinstance(data, list) else data.get("pairs", [])
                
                for item in items[:10]: # فحص أسرع وأكثر تركيزاً
                    ca = item.get("tokenAddress") or item.get("baseToken", {}).get("address")
                    chain = item.get("chainId", "multi")
                    
                    if not ca or ca in seen_addresses:
                        continue
                    
                    if "pairs" in endpoint or "baseToken" in item:
                        pair = item
                        name = pair.get("baseToken", {}).get("name", "Unknown")
                        symbol = pair.get("baseToken", {}).get("symbol", "")
                        liquidity = pair.get("liquidity", {}).get("usd", 0)
                        mcap = pair.get("marketCap", 0)
                    else:
                        detail_res = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{ca}", timeout=1.5)
                        pairs = detail_res.json().get("pairs", [])
                        if not pairs:
                            continue
                        pair = pairs[0]
                        name = pair.get("baseToken", {}).get("name", "Unknown")
                        symbol = pair.get("baseToken", {}).get("symbol", "")
                        liquidity = pair.get("liquidity", {}).get("usd", 0)
                        mcap = pair.get("marketCap", 0)

                    # شروط مرنة لالتقاط العملة أول ما تظهر في السوق وقبل تضخم السيولة
                    if liquidity < 1500 or liquidity > 5000000:
                        continue
                        
                    seen_addresses.add(ca)
                    token_info = {
                        "chain": chain,
                        "name": name,
                        "symbol": symbol,
                        "ca": ca,
                        "liquidity": liquidity,
                        "mcap": mcap
                    }
                    temp_results.append(token_info)
                    
                    # تنبيه فوري عبر التيليجرام
                    alert_text = f"""
⚡ **[MULTI-CHAIN LIGHTNING ALERT]** ⚡

🌐 **الشبكة:** `{chain.upper()}`
🪙 **العملة:** `{name} ({symbol})`
📍 **العقد (CA):**
`{ca}`

📊 **البيانات الأولية:**
• القيمة السوقية: `${mcap:,.0f}`
• السيولة: `${liquidity:,.0f}` 🟢

🔗 **الروابط السريعة:**
• [Defined Charts](https://defined.fi/token/{ca})
• [BubbleMaps](https://app.bubblemaps.io/token/{ca})
"""
                    send_telegram_alert(alert_text)
                    
            except Exception:
                continue
                
        if temp_results:
            multichain_tokens = temp_results + multichain_tokens[:40]
            
        # حلقة فحص متواصلة بأقل وقت انتظار ممكن
        time.sleep(3)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, data=multichain_tokens[:30])

if __name__ == "__main__":
    engine_thread = threading.Thread(target=multichain_lightning_engine)
    engine_thread.daemon = True
    engine_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
