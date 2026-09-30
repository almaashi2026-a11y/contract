import time
import requests
import os
from flask import Flask
import threading

# إعداد خادم الويب الخفيف لإرضاء منصة الاستضافة ومنع إغلاق البورت
app = Flask('')

@app.route('/')
def home():
    return "Tape Flow Sniper Engine is Active and Running!"

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

def tape_flow_sniper_engine():
    """
    محرك قراءة الشريط والتدفقات اللحظية: يركز على تتبع الصفقات الحية، ضغط الشراء، والسيولة الآمنة
    """
    # البحث الشامل لجلب الأزواج النشطة في سولانا
    url = "https://api.dexscreener.com/latest/dex/search?q=sol"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        pairs = data.get("pairs", [])
    except Exception as e:
        print(f"خطأ في الاتصال بالشبكة: {e}")
        return

    for pair in pairs:
        try:
            # التأكد من أن الشبكة هي سولانا
            if pair.get("chainId") != "solana":
                continue
                
            token_name = pair.get("baseToken", {}).get("name", "Unknown")
            token_symbol = pair.get("baseToken", {}).get("symbol", "")
            ca = pair.get("baseToken", {}).get("address", "")
            
            liquidity = pair.get("liquidity", {}).get("usd", 0)
            mcap = pair.get("marketCap", 0)
            
            # مؤشرات الزخم والصفقات في آخر 5 دقائق (محاكاة الشريط اللحظي)
            price_change_5m = pair.get("priceChange", {}).get("m5", 0)
            if price_change_5m is None:
                price_change_5m = 0
                
            volume_5m = pair.get("volume", {}).get("m5", 0)
            
            # قراءة صفقات الشراء والبيع إن وجدت
            txs = pair.get("txns", {}).get("m5", {})
            buys = txs.get("buys", 0)
            sells = txs.get("sells", 0)
            
            # --- معايير الفلترة المؤسسية المستوحاة من الشريط ---
            # 1. سيولة آمنة (بين 15 ألف و 600 ألف دولار)
            if liquidity < 15000 or liquidity > 600000:
                continue
                
            # 2. زخم إيجابي في آخر 5 دقائق
            if price_change_5m < 3.0:
                continue
                
            # 3. ضغط الشراء (أن يكون عدد عمليات الشراء أكبر أو مساوي للبيع مع وجود حركة)
            if buys > 0 and sells > 0:
                ratio = buys / sells
                if ratio < 1.2:
                    continue
            
            # صياغة بطاقة التنبيه الاحترافية (تشبه تدفقات الشريط)
            alert_message = f"""
⚡ **[TAPE FLOW SNIPER ALERT]** ⚡

🪙 **العملة:** `{token_name} ({token_symbol})`
📍 **عقد العملة (CA):**
`{ca}`

📊 **تحليل التدفق اللحظي والشريط:**
• القيمة السوقية (MC): `${mcap:,.0f}`
• السيولة المتاحة: `${liquidity:,.0f}` 🟢
• زخم الـ 5 دقائق: `+{price_change_5m}%` 🔥
• صفقات الشريط (5m): `{buys} شراء / {sells} بيع` 📈
• حجم التدفق النقدي: `${volume_5m:,.0f}`

🔗 **روابط الفحص المباشر:**
• [Defined Charts](https://defined.fi/token/{ca})
• [BubbleMaps](https://app.bubblemaps.io/token/{ca})

🎯 *قاعدتك الذهبية: راقب الشريط، تحقق من المحافظ، ونفذ صفقتك الوحيدة اليوم بثقة!*
"""
            send_telegram_alert(alert_message)
            print(f"✅ تم رصد وإرسال تدفق للعملة: {token_symbol}")
            time.sleep(2)
            
        except Exception:
            continue

if __name__ == "__main__":
    # تشغيل سيرفر الويب في الخلفية لمنع مشاكل المنصة
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()
    
    # الحلقة المستمرة لفحص الشريط والتدفقات
    while True:
        print("🛡️ جاري قراءة الشريط والبحث عن تدفقات السيولة اللحظية...")
        tape_flow_sniper_engine()
        time.sleep(60) # الفحص كل دقيقة لرصد أحدث الحركات
