import time
import requests
import os
from flask import Flask
import threading

app = Flask('')

@app.route('/')
def home():
    return "Sniper Bot Running & Active!"

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
    # استخدام نقطة البحث المباشرة الموثوقة لأزواج سولانا
    url = "https://api.dexscreener.com/latest/dex/search?q=SOL"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        pairs = data.get("pairs", [])
    except Exception as e:
        print(f"خطأ في الاتصال: {e}")
        return

    print(f"🔍 تم جلب {len(pairs)} زوج محلياً للتصفية...")

    for pair in pairs:
        try:
            # التحقق من أن الشبكة هي سولانا حصراً
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
                
            # شروط مبسطة جداً لضمان خروج أول نتيجة والتأكد من إرسالها لتليجرام
            if liquidity <= 0:
                continue
                
            alert_message = f"""
🎯 **[TEST SNIPER ALERT]** 🎯

🪙 **العملة:** `{token_name} ({token_symbol})`
📍 **عقد العملة (CA):**
`{ca}`

📊 **البيانات:**
• القيمة السوقية (MC): `${mcap:,.0f}`
• السيولة: `${liquidity:,.0f}` 🟢
• الزخم (5m): `+{price_change_5m}%` 🔥

🔗 **روابط الفحص:**
• [Defined Charts](https://defined.fi/token/{ca})
• [BubbleMaps](https://app.bubblemaps.io/token/{ca})
"""
            send_telegram_alert(alert_message)
            print(f"✅ تم إرسال تنبيه ناجح للعملة: {token_symbol}")
            time.sleep(2)
            break # يرسل عملة واحدة للتأكد من وصولها ثم يكمل في الدورات القادمة
        except Exception:
            continue

if __name__ == "__main__":
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()
    
    while True:
        direct_sniper_engine()
        time.sleep(30)
