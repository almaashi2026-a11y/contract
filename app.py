import time
import requests
import os
from flask import Flask
import threading

app = Flask('')

@app.route('/')
def home():
    return "Sniper Bot Active & Ready!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

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

def direct_sniper_engine():
    # استخدام محرك البحث العام المباشر لجلب أحدث عملات سولانا النشطة
    url = "https://api.dexscreener.com/latest/dex/search?q=solana"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        pairs = data.get("pairs", [])
    except Exception as e:
        print(f"خطأ في الاتصال: {e}")
        return

    print(f"🔍 تم العثور على {len(pairs)} عملة في الفحص الحالي...")

    for pair in pairs:
        try:
            if pair.get("chainId") != "solana":
                continue
                
            token_name = pair.get("baseToken", {}).get("name", "Unknown")
            token_symbol = pair.get("baseToken", {}).get("symbol", "")
            ca = pair.get("baseToken", {}).get("address", "")
            liquidity = pair.get("liquidity", {}).get("usd", 0)
            mcap = pair.get("marketCap", 0)
            price_change_5m = pair.get("priceChange", {}).get("m5", 0)
            if price_change_5m is None:
                price_change_5m = 0
                
            # شروط مرنة جداً لضمان ظهور النتائج فوراً
            if liquidity < 1000:
                continue
                
            alert_message = f"""
🎯 **[LIVE SNIPER ALERT]** 🎯

🪙 **العملة:** `{token_name} ({token_symbol})`
📍 **عقد العملة (CA):**
`{ca}`

📊 **البيانات اللحظية:**
• القيمة السوقية (MC): `${mcap:,.0f}`
• السيولة: `${liquidity:,.0f}` 🟢
• الزخم (5m): `+{price_change_5m}%` 🔥

🔗 **روابط الفحص:**
• [Defined Charts](https://defined.fi/token/{ca})
• [BubbleMaps](https://app.bubblemaps.io/token/{ca})
"""
            send_telegram_alert(alert_message)
            print(f"✅ تم إرسال تنبيه للعملة: {token_symbol}")
            time.sleep(2)
            break # يرسل عملة واحدة في كل دورة لكي لا يحدث ضغط، ثم يتابع
        except Exception:
            continue

if __name__ == "__main__":
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()
    
    while True:
        direct_sniper_engine()
        time.sleep(30) # فحص كل 30 ثانية
