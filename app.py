import os
import requests
from flask import Flask, render_template_string, request
import threading
import time

app = Flask('')

TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

def send_telegram_alert(message):
    if "YOUR_" in TELEGRAM_BOT_TOKEN or not TELEGRAM_BOT_TOKEN:
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

lightning_safe_tokens = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="3">
    <title>Lightning Fast Sniper - عبد الرحمن</title>
    <style>
        body { background-color: #010306; color: #00ffcc; font-family: 'Courier New', monospace; margin: 0; padding: 15px; }
        h1 { color: #ff0055; text-align: center; font-size: 19px; text-transform: uppercase; letter-spacing: 2px; }
        .status-box { background: #0d1117; padding: 6px; border: 1px solid #ff0055; text-align: center; margin-bottom: 12px; font-size: 11px; color: #fff; }
        table { width: 100%; border-collapse: collapse; background: #0d1117; border-radius: 6px; overflow: hidden; border: 1px solid #21262d; }
        th, td { padding: 7px 9px; text-align: center; border-bottom: 1px solid #21262d; font-size: 11px; }
        th { background: #161b22; color: #8b949e; }
        tr:hover { background: #ff005515; }
        .chain-badge { background: #7928ca; padding: 2px 5px; border-radius: 4px; font-size: 10px; color: #fff; font-weight: bold; }
        .flash-tag { color: #ff0055; font-weight: bold; animation: flash 0.5s infinite; }
        .ca-box { color: #58a6ff; background: #010409; padding: 2px 4px; border-radius: 3px; border: 1px solid #30363d; font-size: 10px; }
        @keyframes flash { 0% { opacity: 1; } 50% { opacity: 0.2; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <h1>⚡ LIGHTNING INSTANT SNIPER (أسرع رصد فوري) ⚡</h1>
    
    <div class="status-box">
        🚀 وضع السرعة القصوى مفعل (تتبع مباشر للأحداث والسيولة) | تحديث: كل 3 ثوانٍ
    </div>

    <table>
        <thead>
            <tr>
                <th>الشبكة</th>
                <th>الرمز المميز</th>
                <th>الحالة</th>
                <th>مؤشر الفومو</th>
                <th>السيولة ($)</th>
                <th>عقد العملة (CA)</th>
                <th>التنفيذ الفوري</th>
            </tr>
        </thead>
        <tbody>
            {% for item in data %}
            <tr>
                <td><span class="chain-badge">{{ item.chain | upper }}</span></td>
                <td><b>{{ item.name }}</b> ({{ item.symbol }})</td>
                <td class="flash-tag">انطلاقة صفرية 🔥</td>
                <td style="color: #ff0055; font-weight: bold;">{{ item.fomo_score }}%</td>
                <td>${{ "{:,.0f}".format(item.liquidity) }}</td>
                <td><span class="ca-box">{{ item.ca }}</span></td>
                <td>
                    <a href="https://defined.fi/token/{{ item.ca }}" target="_blank" style="color: #58a6ff; text-decoration: none;">Charts</a> | 
                    <a href="https://app.bubblemaps.io/token/{{ item.ca }}" target="_blank" style="color: #f0883e; text-decoration: none;">Bubble</a>
                </td>
            </tr>
            {% else %}
            <tr>
                <td colspan="7" style="color: #8b949e; padding: 20px;">جاري ترصد ولادة العملات الجديدة في أجزاء الثانية...</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

def process_token(item, chain, seen_addresses):
    global lightning_safe_tokens
    try:
        ca = item.get("tokenAddress") or item.get("baseToken", {}).get("address")
        if not ca or ca in seen_addresses:
            return
            
        pair = item
        name = pair.get("baseToken", {}).get("name", "Unknown")
        symbol = pair.get("baseToken", {}).get("symbol", "")
        liquidity = pair.get("liquidity", {}).get("usd", 0)
        mcap = pair.get("marketCap", 0)
        vol_5m = pair.get("volume", {}).get("m5", 0) or 0

        # فلاتر سريعة وخفيفة جداً لضمان عدم تضيع الوقت
        if liquidity < 1000 or liquidity > 10000000:
            return
            
        seen_addresses.add(ca)
        fomo_score = int(min(100, (vol_5m / max(1, liquidity)) * 100))
        
        token_info = {
            "chain": chain,
            "name": name,
            "symbol": symbol,
            "ca": ca,
            "liquidity": liquidity,
            "mcap": mcap,
            "fomo_score": fomo_score
        }
        
        lightning_safe_tokens.insert(0, token_info)
        if len(lightning_safe_tokens) > 50:
            lightning_safe_tokens.pop()
            
        # إرسال التنبيه الفوري الصاروخي
        alert_text = f"""
⚡ **[LIGHTNING SNIPER ALERT]** ⚡

🌐 الشبكة: `{chain.upper()}`
🪙 العملة: `{name} ({symbol})`
🔥 الفومو: `{fomo_score}%`

📍 **عقد العملة (انسخ فوراً):**
`{ca}`

📊 السيولة: `${liquidity:,.0f}` | القيمة: `${mcap:,.0f}`

🔗 **الروابط:**
• [Defined Charts](https://defined.fi/token/{ca})
• [BubbleMaps](https://app.bubblemaps.io/token/{ca})
"""
        send_telegram_alert(alert_text)
    except Exception:
        pass

def lightning_engine():
    seen_addresses = set()
    endpoints = [
        "https://api.dexscreener.com/token-profiles/latest/v1",
        "https://api.dexscreener.com/latest/dex/search?q=solana",
        "https://api.dexscreener.com/latest/dex/search?q=base",
        "https://api.dexscreener.com/latest/dex/search?q=eth"
    ]
    
    while True:
        for endpoint in endpoints:
            try:
                res = requests.get(endpoint, timeout=2)
                data = res.json()
                items = data if isinstance(data, list) else data.get("pairs", [])
                
                # استخدام خيوط معالجة سريعة متوازية لعدم انتظار أي تأخير في الطلبات
                for item in items[:15]:
                    chain = item.get("chainId", "solana")
                    t = threading.Thread(target=process_token, args=(item, chain, seen_addresses))
                    t.daemon = True
                    t.start()
            except Exception:
                continue
                
        # فترة نوم قصيرة للغاية (0.5 ثانية فقط) للبحث المستمر الفائق
        time.sleep(0.5)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, data=lightning_safe_tokens[:30])

if __name__ == "__main__":
    engine_thread = threading.Thread(target=lightning_engine)
    engine_thread.daemon = True
    engine_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
