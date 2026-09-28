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

def fetch_latest_tokens_from_dex():
    """
    جلب العملات والبيانات اللحظية من DexScreener API
    """
    url = "https://api.dexscreener.com/latest/dex/search?q=solana" # مثال على البحث في شبكة سولانا
    try:
        response = requests.get(url)
        data = response.json()
        return data.get("pairs", [])
    except Exception as e:
        print(f"خطأ في الاتصال بـ API: {e}")
        return []

def run_explosion_sniper_scanner():
    print("🚀 جاري تشغيل ماسح 'Explosion Sniper Pro' الآلي...")
    
    # جلب القائمة
    pairs = fetch_latest_tokens_from_dex()
    
    for pair in pairs:
        try:
            token_name = pair.get("baseToken", {}).get("name", "Unknown")
            ca = pair.get("baseToken", {}).get("address", "")
            liquidity = pair.get("liquidity", {}).get("usd", 0)
            mcap = pair.get("marketCap", 0)
            
            # بيانات التغير وحجوم 5 دقائق (إن وجدت في الـ API)
            price_change_5m = pair.get("priceChange", {}).get("m5", 0)
            volume_5m = pair.get("volume", {}).get("m5", 0)
            
            # 1. فلتر السيولة الآمنة (بين 20K و 500K)
            if not liquidity or liquidity < 20000 or liquidity > 500000:
                continue
                
            # 2. فلتر الزخم على الـ 5 دقائق (صعود بنسبة أكبر من 5%)
            if price_change_5m is None or price_change_5m < 5.0:
                continue
                
            # صياغة البطاقة الملونة والمنسقة للتليجرام
            alert_message = f"""
🚨 **صيد جديد - Explosion Sniper Pro** 🚨

🪙 **العملة:** `{token_name}`
📍 **عقد العملة (CA):**
`{ca}`

📊 **البيانات اللحظية:**
• القيمة السوقية (MC): `${mcap:,.0f}`
• السيولة (Liquidity): `${liquidity:,.0f}`
• زخم الـ 5m: `+{price_change_5m}%` 🟢
• حجم تداول الـ 5m: `${volume_5m:,.0f}`

🔗 **روابط الفحص والتنفيذ السريع:**
• [Defined Charts](https://defined.fi/token/{ca})
• [BubbleMaps](https://app.bubblemaps.io/)
• [OKX DEX / Raydium](https://t.me/)

⚡ *التزم بقاعدة: صفقة واحدة في اليوم.. افحص الحيتان وتوكل على الله!*
"""
            
            # إرسال التنبيه
            send_telegram_alert(alert_message)
            print(تم إرسال تنبيه للعملة: {token_name})
            
            # إيقاف مؤقت لمنع التكرار السريع
            time.sleep(2)
            
        except Exception as e:
            continue

# لتشغيل البوت بشكل مستمر كل دقيقتين
if __name__ == "__main__":
    while True:
        run_explosion_sniper_scanner()
        time.sleep(120)  # الفحص كل دقيقتين
