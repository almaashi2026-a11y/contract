import time
import requests
import os
from flask import Flask
import threading

# إعداد خادم الويب الخفيف لإرضاء منصة Render ومنع إغلاق البورت
app = Flask('')

@app.route('/')
def home():
    return "Explosion Sniper Pro - Institutional Edition is Alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
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

def institutional_behavioral_scanner():
    """
    محرك القنص السلوكي المؤسسي: فحص السيولة، ضغط الشراء والبيع، وزخم الـ 5 دقائق
    """
    url = "https://api.dexscreener.com/latest/dex/search?q=solana"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        pairs = data.get("pairs", [])
    except Exception as e:
        print(f"خطأ في جلب بيانات الشبكة: {e}")
        return

    for pair in pairs:
        try:
            token_name = pair.get("baseToken", {}).get("name", "Unknown")
            token_symbol = pair.get("baseToken", {}).get("symbol", "")
            ca = pair.get("baseToken", {}).get("address", "")
            liquidity = pair.get("liquidity", {}).get("usd", 0)
            mcap = pair.get("marketCap", 0)
            
            # مؤشرات الحجوم والزخم
            price_change_5m = pair.get("priceChange", {}).get("m5", 0)
            volume = pair.get("volume", {})
            vol_5m = volume.get("m5", 0)
            
            # محاكاة تحليل التداولات (الشراء والبيع خلال الفترات المتاحة)
            txs = pair.get("txns", {}).get("m5", {})
            buys_5m = txs.get("buys", 0)
            sells_5m = txs.get("sells", 0)
            
            # 1. فلتر السيولة المؤسسية الآمنة (بين 20 ألف و 500 ألف دولار)
            if not liquidity or liquidity < 20000 or liquidity > 500000:
                continue
                
            # 2. فلتر الزخم (صعود بنسبة لا تقل عن 5% في 5 دقائق)
            if price_change_5m is None or price_change_5m < 5.0:
                continue
                
            # 3. فلتر الضغط الشرائي (عدد الصفقات الشرائية أعلى بوضوح من البيعية)
            if buys_5m > 0 and sells_5m > 0:
                buy_sell_ratio = buys_5m / sells_5m
                if buy_sell_ratio < 1.3: # يجب أن يكون الشراء أعلى بنسبة 30% على الأقل
                    continue
            
            # صياغة بطاقة التنبيه الاحترافية المتقدمة
            alert_message = f"""
🎯 **[INSTITUTIONAL BEHAVIORAL SNIPER]** 🎯

🪙 **العملة:** `{token_name} ({token_symbol})`
📍 **عقد العملة (CA):**
`{ca}`

📊 **التحليل الكمي وسلوك السيولة (5m):**
• القيمة السوقية (MC): `${mcap:,.0f}`
• السيولة الآمنة: `${liquidity:,.0f}` 🟢
• زخم السعر (5m): `+{price_change_5m}%` 🔥
• صفقات الشراء vs البيع: `{buys_5m} شراء / {sells_5m} بيع` 📈
• حجم التدفق النقدي: `${vol_5m:,.0f}`

🔗 **روابط الفحص والتحقق الفوري:**
• [Defined Charts](https://defined.fi/token/{ca})
• [BubbleMaps](https://app.bubblemaps.io/token/{ca})

⚡ *قاعدة القناص: هذه الفرصة اجتازت فلتر ضغط الحيتان.. ادرس شارتك ونفذ صفقتك الوحيدة بحذر!*
"""
            send_telegram_alert(alert_message)
            print(f"تم إرسال تنبيه احترافي للعملة: {token_symbol}")
            time.sleep(2)
            
        except Exception:
            continue

if __name__ == "__main__":
    # تشغيل خادم الويب في الخلفية لمنع خطأ البورت في منصات الاستضافة
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()
    
    # الحلقة التكرارية لعمل البوت المستمر
    while True:
        print("🛡️ جاري تشغيل الماسح السلوكي والكمّي للأسواق...")
        institutional_behavioral_scanner()
        time.sleep(120)  # الفحص كل دقيقتين بدقة عالية
