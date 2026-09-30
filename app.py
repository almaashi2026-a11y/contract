import time
import requests
import os
from flask import Flask
import threading

# إعداد خادم الويب الخفيف لإرضاء منصة الاستضافة ومنع إغلاق البورت
app = Flask('')

@app.route('/')
def home():
    return "Explosion Sniper Pro - Live Feed Active!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# إعدادات البوت والربط مع تيليجرام (قم بوضع بياناتك هنا)
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

def sniper_live_scanner():
    """
    مسح أحدث الأزواج المضافة في السوق لضمان التقاط الفرص فور ظهورها
    """
    # استخدام نقطة جلب العملات والتوكنات الجديدة مباشرة
    url = "https://api.dexscreener.com/latest/dex/tokens/solana" # أو استخدام API عام لأحدث الأزواج
    # وبما أن DexScreener يعتمد أحياناً على البحث، سنستخدم رابط يجلب الأنشطة أو البحث الشامل:
    search_url = "https://api.dexscreener.com/latest/dex/search?q=SOL"
    
    try:
        response = requests.get(search_url, timeout=5)
        data = response.json()
        pairs = data.get("pairs", [])
    except Exception as e:
        print(f"خطأ في جلب بيانات الشبكة: {e}")
        return

    print(f"🔍 تم فحص {lenpair if 'lenpair' in locals() else len(pairs)} عملة في السوق...")

    for pair in pairs:
        try:
            # التأكد أن الشبكة هي Solana
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

            volume_5m = pair.get("volume", {}).get("m5", 0)
            
            # فلاتر مرنة لضمان ظهور نتائج حقيقية ونظيفة:
            # السيولة بين 10,000$ و 1,000,000$
            if liquidity < 10000 or liquidity > 1000000:
                continue
                
            # الزخم الإيجابي في آخر 5 دقائق (أكبر من 2% لتجربة ظهور النتائج بوضوح)
            if price_change_5m < 2.0:
                continue
                
            alert_message = f"""
🎯 **[SNIPER ALERT - فرصة مرصودة]** 🎯

🪙 **العملة:** `{token_name} ({token_symbol})`
📍 **عقد العملة (CA):**
`{ca}`

📊 **البيانات اللحظية:**
• القيمة السوقية (MC): `${mcap:,.0f}`
• السيولة: `${liquidity:,.0f}` 🟢
• الزخم (5m): `+{price_change_5m}%` 🔥
• حجم التداول (5m): `${volume_5m:,.0f}`

🔗 **روابط الفحص المباشر:**
• [Defined Charts](https://defined.fi/token/{ca})
• [BubbleMaps](https://app.bubblemaps.io/token/{ca})

⚡ *استعد لتنفيذ صفقتك اليومية بحذر وعين تلاحظ التفاصيل!*
"""
            send_telegram_alert(alert_message)
            print(f"✅ تم العرسال وإرسال تنبيه للعملة: {token_symbol}")
            time.sleep(2)
            
        except Exception as err:
            continue

if __name__ == "__main__":
    # تشغيل سيرفر الويب للخلفية
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()
    
    while True:
        print("🛡️ البوت يعمل ويقوم بمسح السوق الآن...")
        sniper_live_scanner()
        time.sleep(60) # الفحص كل دقيقة لتحديث البيانات
