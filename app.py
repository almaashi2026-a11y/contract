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
        # تقليص الوقت المستقطع لأقصى سرعة إرسال ممكنة
        requests.post(url, json=payload, timeout=2)
    except Exception:
        pass

lightning_tokens = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="8"> <!-- تحديث سريع جداً كل 8 ثوانٍ -->
    <title>Lightning Speed Sniper - عبد الرحمن</title>
    <style>
        body { background-color: #05070a; color: #00ffcc; font-family: 'Courier New', monospace; margin: 0; padding: 15px; }
        h1 { color: #ff0055; text-align: center; font-size: 20px; text-transform: uppercase; letter-spacing: 2px; }
        .status-box { background: #0d1117; padding: 8px; border: 1px solid #ff0055; text-align: center; margin-bottom: 15px; font-size: 12px; color: #fff; }
        table { width: 100%; border-collapse: collapse; background: #0d1117; border-radius: 6px; overflow: hidden; border: 1px solid #21262d; }
        th, td { padding: 8px 10px; text-align: center; border-bottom: 1px solid #21262d; font-size: 12px; }
        th { background: #161b22; color: #8b949e; }
        tr:hover { background: #ff005515; }
        .speed-tag { color: #ff0055; font-weight: bold; animation: flash 1s infinite; }
        .ca-box { color: #58a6ff; background: #010409; padding: 2px 4px; border-radius: 3px; border: 1px solid #30363d; font-size: 11px; }
        @keyframes flash { 0% { opacity: 1; } 50% { opacity: 0.2; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <h1>⚡ LIGHTNING SPEED SNIPER (رصد قبل انتهاء الزخم) ⚡</h1>
    
    <div class="status-box">
        🚀 المحرك يعمل بأقصى تردد لضمان رصد الانطلاقات في أجزاء الثانية الأولى | تحديث الواجهة: كل 8 ثوانٍ
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
                <td><b>{{ item.chain | upper }}</b></td>
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
                <td colspan="7" style="color: #8b949e; padding: 20px;">جاري التقاط أول شمعة انطلاق في السوق الفوري...</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

def lightning_fast_engine():
    global lightning_tokens
    seen_addresses = set()
    
    # الاعتماد على نقاط التحديث المباشر للتوكنات الجديدة كلياً
    endpoints = [
        "https://api.dexscreener.com/token-profiles/latest/v1",
        "https://api.dexscreener.com/latest/dex/search?q=solana"
    ]
    
    while True:
        temp_results = []
        for endpoint in endpoints:
            try:
                res = requests.get(endpoint, timeout=3)
                data = res.json()
                
                # معالجة القوائم حسب شكل الاستجابة
                items = data if isinstance(data, list) else data.get("pairs", [])
                
                for item in items[:15]:
                    ca = item.get("tokenAddress") or item.get("baseToken", {}).get("address")
                    chain = item.get("chainId", "solana")
                    
                    if not ca or ca in seen_addresses:
                        continue
                    
                    # إذا كانت الاستجابة من البحث العام، نستخرج البيانات مباشرة
                    if "pairs" in endpoint or "baseToken" in item:
                        pair = item
                        name = pair.get("baseToken", {}).get("name", "Unknown")
                        symbol = pair.get("baseToken", {}).get("symbol", "")
                        liquidity = pair.get("liquidity", {}).get("usd", 0)
                        mcap = pair.get("marketCap", 0)
                    else:
                        # جلب تفاصيل سريعة جداً للعقد الجديد
                        detail_res = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{ca}", timeout=2)
                        pairs = detail_res.json().get("pairs", [])
                        if not pairs:
                            continue
                        pair = pairs[0]
                        name = pair.get("baseToken", {}).get("name", "Unknown")
                        symbol = pair.get("baseToken", {}).get("symbol", "")
                        liquidity = pair.get("liquidity", {}).get("usd", 0)
                        mcap = pair.get("marketCap", 0)

                    # شروط مرنة جداً لالتقاط العملة فور ولادتها وقبل تضخم السعر
                    if liquidity < 2000 or liquidity > 3000000:
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
                    
                    # تنبيه فوري لا يتأخر أبداً
                    alert_text = f"""
⚡ **[LIGHTNING SNIPER - EARLY ENTRY]** ⚡

🌐 **الشبكة:** `{chain.upper()}`
🪙 **العملة:** `{name} ({symbol})`
📍 **العقد (CA):**
`{ca}`

📊 **البيانات اللحظية الأولى:**
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
            lightning_tokens = temp_results + lightning_tokens[:30] # الاحتفاظ بأحدث الصفقات في الأعلى
            
        # تقليص فترة الانتظار إلى 5 ثوانٍ فقط لضمان السرعة المطلقة
        time.sleep(5)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, data=lightning_tokens[:25])

if __name__ == "__main__":
    engine_thread = threading.Thread(target=lightning_fast_engine)
    engine_thread.daemon = True
    engine_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
