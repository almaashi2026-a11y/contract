import time
import requests
import os
from threading import Thread
from flask import Flask

# إعداد خادم وهمي لإرضاء منصة Render ومنع إغلاق البورت
app = Flask('')

@app.route('/')
def home():
    return "Explosion Sniper Pro is Alive and Running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# إعدادات البوت والربط مع تيليجرام
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

def send_telegram_alert(message):
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

def professional_sniper_engine():
    url = "https://api.dexscreener.com/latest/dex/search?q=solana"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        pairs = data.get("pairs", [])
    except Exception as e:
        print(f"خطأ في الاتصال بالشبكة: {e}")
        return

    for pair in pairs:
        try:
            token_name = pair.get("baseToken", {}).get("name", "Unknown")
            ca = pair.get("baseToken", {}).get("address", "")
            liquidity = pair.get("liquidity", {}).get("usd", 0)
            mcap = pair.get("marketCap", 0)
            price_change_5m = pair.get("priceChange", {}).get("m5", 0)
            
            if not liquidity or liquidity < 20000 or liquidity > 500000:
                continue
                
            if price_change_5m is None or price_change_5m < 5.0:
                continue
                
            alert_message = f"""
🎯 **[INSTITUTIONAL SNIPER ALERT]** 🎯

🪙 **العملة:** `{token_name}`
📍 **عقد العملة (CA):**
`{ca}`

📊 **البيانات المالية والفنية:**
• القيمة السوقية (MC): `${mcap:,.0f}`
• السيولة الآمنة: `${liquidity:,.0f}` 🟢
• زخم الـ 5m: `+{price_change_5m}%` 🔥

🔗 **روابط الفحص المباشر والتحليل:**
• [Defined Charts](https://defined.fi/token/{ca})
• [BubbleMaps](https://app.bubblemaps.io/)

⚡ *تذكرها: صفقة واحدة في اليوم تضمن لك التركيز والنجاح!*
"""
            send_telegram_alert(alert_message)
            time.sleep(2)
        except Exception:
            continue

def run_sniper_loop():
    while True:
        print("🛡️ جاري مسح السوق وبحث الفرص...")
        professional_sniper_engine()
        time.sleep(90)

if __name__ == "__main__":
    # تشغيل الخادم الوهمي في خلفية منفصلة لإرضاء المنصة
    t = Thread(target=run_web)
    t.start()
    
    # تشغيل حلقة البوت الأساسية
    run_sniper_loop()
