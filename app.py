import os
import requests
from flask import Flask, render_template_string, request
import threading
import time

app = Flask('')

# ضع هنا توكن بوت تيليجرام ومعرف الشات الخاص بك بدقة
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

def send_telegram_alert(message):
    if "YOUR_" in TELEGRAM_BOT_TOKEN or not TELEGRAM_BOT_TOKEN:
        print("⚠️ تحذير: لم تقم بإدخال توكن تليجرام الصحيح في الكود!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=3)
        if response.status_code != 200:
            print(f"❌ خطأ تيليجرام: {response.text}")
    except Exception as e:
        print(f"❌ فشل إرسال تنبيه تيليجرام: {e}")

fomo_tokens = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="4"> <!-- تحديث تلقائي أسرع كل 4 ثوانٍ -->
    <title>FOMO Sniper Pro - عبد الرحمن</title>
    <style>
        body { background-color: #020408; color: #00ffcc; font-family: 'Courier New', monospace; margin: 0; padding: 15px; }
        h1 { color: #ff0055; text-align: center; font-size: 20px; text-transform: uppercase; letter-spacing: 2px; }
        .status-box { background: #0d1117; padding: 8px; border: 1px solid #ff0055; text-align: center; margin-bottom: 15px; font-size: 12px; color: #fff; }
        table { width: 100%; border-collapse: collapse; background: #0d1117; border-radius: 6px; overflow: hidden; border: 1px solid #21262d; }
        th, td { padding: 8px 10px; text-align: center; border-bottom: 1px solid #21262d; font-size: 12px; }
        th { background: #161b22; color: #8b949e; }
        tr:hover { background: #ff005515; }
        .chain-badge { background: #1f6feb; padding: 2px 6px; border-radius: 4px; font-size: 11px; color: #fff; font-weight: bold; }
        .fomo-high { color: #ff0055; font-weight: bold; animation: pulse 0.6s infinite; }
        .fomo-med { color: #ffaa00; font-weight: bold; }
        .ca-box { color: #58a6ff; background: #010409; padding: 2px 4px; border-radius: 3px; border: 1px solid #30363d; font-size: 11px; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <h1>🚀 FOMO SNIPER PRO (رصد الزخم الشديد والتنفيذ) 🚀</h1>
    
    <div class="status-box">
        🔥 نظام قياس الفومو والسيولة الحية مفعل لجميع السلاسل | تحديث الواجهة: كل 4 ثوانٍ
    </div>

    <table>
        <thead>
            <tr>
                <th>الشبكة</th>
                <th>الرمز المميز</th>
                <th>مؤشر الفومو (FOMO)</th>
                <th>القيمة السوقية</th>
                <th>السيولة ($)</th>
                <th>الحجم (5m)</th>
                <th>عقد العملة (CA)</th>
                <th>روابط التداول</th>
            </tr>
        </thead>
        <tbody>
            {% for item in data %}
            <tr>
                <td><span class="chain-badge">{{ item.chain | upper }}</span></td>
                <td><b>{{ item.name }}</b> ({{ item.symbol }})</td>
                <td>
                    {% if item.fomo_score > 70 %}
                        <span class="fomo-high">🔥 فومو عالي جداً ({{ item.fomo_score }}%)</span>
                    {% elif item.fomo_score > 40 %}
                        <span class="fomo-med">⚡ زخم ممتاز ({{ item.fomo_score }}%)</span>
                    {% else %}
                        <span style="color: #00ffcc;">مبكر ({{ item.fomo_score }}%)</span>
                    {% endif %}
                </td>
                <td>${{ "{:,.0f}".format(item.mcap) }}</td>
                <td>${{ "{:,.0f}".format(item.liquidity) }}</td>
                <td style="color: #3fb950;">${{ "{:,.0f}".format(item.vol_5m) }}</td>
                <td><span class="ca-box">{{ item.ca }}</span></td>
                <td>
                    <a href="https://defined.fi/token/{{ item.ca }}" target="_blank" style="color: #58a6ff; text-decoration: none;">Charts</a> | 
                    <a href="https://app.bubblemaps.io/token/{{ item.ca }}" target="_blank" style="color: #f0883e; text-decoration: none;">Bubble</a>
                </td>
            </tr>
            {% else %}
            <tr>
                <td colspan="8" style="color: #8b949e; padding: 25px;">جاري ترصد صفقات الفومو والانطلاقات القوية في السوق...</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

def fomo_sniper_engine():
    global fomo_tokens
    seen_addresses = set()
    
    endpoints = [
        "https://api.dexscreener.com/token-profiles/latest/v1",
        "https://api.dexscreener.com/latest/dex/search?q=solana",
        "https://api.dexscreener.com/latest/dex/search?q=base"
    ]
    
    while True:
        temp_results = []
        for endpoint in endpoints:
            try:
                res = requests.get(endpoint, timeout=2.5)
                data = res.json()
                items = data if isinstance(data, list) else data.get("pairs", [])
                
                for item in items[:12]:
                    ca = item.get("tokenAddress") or item.get("baseToken", {}).get("address")
                    chain = item.get("chainId", "multi")
                    
                    if not ca or ca in seen_addresses:
                        continue
                    
                    if "pairs" in endpoint or "baseToken" in item:
                        pair = item
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
                    vol_5m = pair.get("volume", {}).get("m5", 0)
                    if vol_5m is None:
                        vol_5m = 0

                    # شروط تصفية دقيقة
                    if liquidity < 1000 or liquidity > 4000000:
                        continue
                    
                    # حساب مؤشر الفومو (FOMO Score) بناءً على نسبة حجم الـ 5 دقائق إلى السيولة
                    fomo_score = int(min(100, (vol_5m / max(1, liquidity)) * 100))
                        
                    seen_addresses.add(ca)
                    token_info = {
                        "chain": chain,
                        "name": name,
                        "symbol": symbol,
                        "ca": ca,
                        "liquidity": liquidity,
                        "mcap": mcap,
                        "vol_5m": vol_5m,
                        "fomo_score": fomo_score
                    }
                    temp_results.append(token_info)
                    
                    # تنبيه تليجرام فوري مع تفاصيل الفومو للشراء
                    alert_text = f"""
🚨 **[FOMO SNIPER ALERT - تنبيه فومو]** 🚨

🌐 الشبكة: `{chain.upper()}`
🪙 العملة: `{name} ({symbol})`
🔥 مؤشر الفومو: `{fomo_score}%`

📍 **عقد العملة (انسخ للتنفيذ):**
`{ca}`

📊 **مستويات السيولة والزخم:**
• القيمة السوقية: `${mcap:,.0f}`
• السيولة: `${liquidity:,.0f}` 🟢
• حجم 5 دقائق: `${vol_5m:,.0f}` 🚀

🔗 **الروابط:**
• [Defined Charts](https://defined.fi/token/{ca})
• [BubbleMaps](https://app.bubblemaps.io/token/{ca})
"""
                    send_telegram_alert(alert_text)
                    
            except Exception as e:
                continue
                
        if temp_results:
            # ترتيب العملات حسب الأعلى فومو في المقدمة
            temp_results.sort(key=lambda x: x['fomo_score'], reverse=True)
            fomo_tokens = temp_results + fomo_tokens[:40]
            
        time.sleep(3)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, data=fomo_tokens[:30])

if __name__ == "__main__":
    engine_thread = threading.Thread(target=fomo_sniper_engine)
    engine_thread.daemon = True
    engine_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
