import time
import requests
import os
from flask import Flask
import threading

# إعداد خادم الويب الخفيف لإرضاء منصة الاستضافة ومنع إغلاق البورت
app = Flask('')

@app.route('/')
def home():
    return "Direct Sniper Engine is Active and Running!"

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

def direct_sniper_engine():
    """
    محرك مباشر لجلب أحدث التوكنات والسيولة في السوق لتجنب فراغ النتائج
    """
    # استخدام نقطة جلب أحدث الروابط المضافة مباشرة من المنصة
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    
    try:
        response = requests.get(url, timeout=5)
        profiles = response.json()
    except Exception as e:
        print(f"خطأ في الاتصال بالشبكة: {e}")
        return

    # إذا كانت القائمة فارغة، نلجأ لرابط بديل لجلب العملات المميزة مباشرة
    if not profiles or not isinstance(profiles, list):
        fallback_url = "https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112" # استخدام سولانا كمرجع
        try:
            res = requests.get(fallback_url, timeout=5)
            data = res.json()
            pairs = data.get("pairs", [])
        except:
            return
    else:
        # استخراج عناوين العقود من آخر البروفايلات المضافة
        pairs = []
        for p in profiles[:15]:  # فحص أحدث 15 عملة
            if p.get("chainId") == "solana":
                token_addr = p.get("tokenAddress")
                if token_addr:
                    # جلب تفاصيل الزوج لكل عقـد مباشرة
                    detail_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_addr}"
                    try:
                        detail_res = requests.get(detail_url, timeout=3)
                        detail_data = detail_res.json()
                        p_list = detail_data.get("pairs", [])
                        if p_list:
                            pairs.extend(p_list)
                    except:
                        continue

    print(жf"🔍 تم فحص {len(pairs)} زوج نشط في السوق...")

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
                
            volume_5m = pair.get("volume", {}).get("m5", 0)
            
            # فلاتر مرنة لضمان ظهور الصفقات وعدم جفاف النتائج:
            # السيولة بين 5,000$ و 2,000,000$
            if liquidity < 5000 or liquidity > 2000000:
                continue
                
            # زخم إيجابي خفيف لضمان وجود حركة
            if price_change_5m < 0.5:
                continue
                
            alert_message = f"""
🎯 **[LIVE SNIPER TARGET FOUND]** 🎯

🪙 **العملة:** `{token_name} ({token_symbol})`
📍 **عقد العملة (CA):**
`{ca}`

📊 **البيانات اللحظية:**
• القيمة السوقية (MC): `${mcap:,.0f}`
• السيولة المتاحة: `${liquidity:,.0f}` 🟢
• الزخم (5m): `+{price_change_5m}%` 🔥
• حجم التداول (5m): `${volume_5m:,.0f}`

🔗 **روابط الفحص والتحليل الفوري:**
• [Defined Charts](https://defined.fi/token/{ca})
• [BubbleMaps](https://app.bubblemaps.io/token/{ca})

⚡ *صفقتك الوحيدة اليوم تتطلب تركيزاً تاماً.. افحص الشارت وتوكل على الله!*
"""
            send_telegram_alert(alert_message)
            print(f"✅ تم إرسال تنبيه حقيقي للعملة: {token_symbol}")
            time.sleep(2)
            
        except Exception:
            continue

if __name__ == "__main__":
    # تشغيل سيرفر الويب في الخلفية لمنع مشاكل البورت
    t = threading.Thread(target=run_web)
    t.daemon = True
    t.start()
    
    # حلقة العمل المستمرة
    while True:
        print("🛡️ جاري جلب أحدث العملات والتدفقات الحية...")
        direct_sniper_engine()
        time.sleep(45) # الفحص كل 45 ثانية
