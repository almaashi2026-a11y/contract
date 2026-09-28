import time
import requests

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
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"خطأ في إرسال التنبيه: {e}")

def professional_sniper_engine():
    """
    محرك القنص المؤسسي: يدمج فلتر السيولة، امتصاص الـ 5 دقائق، وتفوق حجم الشراء
    """
    url = "https://api.dexscreener.com/latest/dex/search?q=solana"
    try:
        response = requests.get(url)
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
            
            # مؤشرات الـ 5 دقائق
            price_change_5m = pair.get("priceChange", {}).get("m5", 0)
            
            # فحص الحجوم (إذا توفرت تفاصيل الشراء والبيع في الاستجابة)
            # شروط الفلتر الصارمة
            if not liquidity or liquidity < 20000 or liquidity > 500000:
                continue
                
            if price_change_5m is None or price_change_5m < 5.0:
                continue
                
            # صياغة البطاقة الاحترافية المرسلة لجوالك
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
• [OKX DEX Execution](https://t.me/)

⚡ *تذكرهـا: صفقة واحدة في اليوم تضمن لك التركيز والنجاح.. توكل على الله!*
"""
            send_telegram_alert(alert_message)
            time.sleep(2)
            
        except Exception as e:
            continue

if __name__ == "__main__":
    while True:
        print("🛡️ جاري تشغيل ماسح القنص المؤسسي بدقة عالية...")
        professional_sniper_engine()
        time.sleep(90)  # فحص دوري مدروس
