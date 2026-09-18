import os
import time
import requests
from fastapi import FastAPI
import uvicorn
import threading

app = FastAPI()

TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

engine_status = {
    "status": "Running",
    "last_event": "Scanning multi-chain momentum tokens..."
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Multi-Chain Momentum & Volume Pump Radar",
        "details": engine_status
    }

def send_telegram_alert(message: str):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"❌ خطأ تليجرام: {e}")

# سجل لتخزين التوكنات التي تم إرسالها مسبقاً لعدم تكرار التنبيهات
sent_tokens = set()

def fetch_latest_multichain_tokens():
    global sent_tokens
    # نستخدم نقطة نهاية DexScreener للبحث عن أحدث الأزواج أو العملات النشطة عالمياً
    url = "https://api.dexscreener.com/latest/dex/search?q=solana%20eth%20bsc%20base" # أو جلب آخر الأصول المضافة
    
    # بدلاً من ذلك، سنراقب أحدث التوكنات عبر جلبها من الطريقة العامة لـ DexScreener أو مصادر متعددة
    # سنعتمد على نقطة جلب الـ Boosted / Latest profiles أو البحث الذكي
    try:
        # جلب أحدث الأزواج المضافة أو الأكثر تفاعلاً عبر الـ API العام
        trending_url = "https://api.dexscreener.com/token-boosts/latest/v1"
        res = requests.get(trending_url, timeout=10)
        if res.status_code == 200:
            tokens = res.json()
            if isinstance(tokens, list):
                for item in tokens[:10]: # فحص أحدث 10 توكنات تم ترويجها أو إطلاقها
                    chain_id = item.get("chainId", "")
                    token_address = item.get("tokenAddress", "")
                    
                    if not token_address or token_address in sent_tokens:
                        continue
                        
                    # جلب تفاصيل الزخم والسيولة لهذا التوكن بغض النظر عن سلسلته
                    pair_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
                    pair_res = requests.get(pair_url, timeout=5)
                    if pair_res.status_code == 200:
                        pair_data = pair_res.json()
                        pairs = pair_data.get("pairs", [])
                        if pairs:
                            # نأخذ أول زوج نشط على الشبكة
                            pair = pairs[0]
                            liq = pair.get("liquidity", {}).get("usd", 0)
                            vol = pair.get("volume", {}).get("h1", 0)
                            txns = pair.get("txns", {})
                            h1_txns = txns.get("h1", {})
                            buys = h1_txns.get("buys", 0)
                            sells = h1_txns.get("sells", 0)
                            
                            symbol = pair.get("baseToken", {}).get("symbol", "TOKEN")
                            name = pair.get("baseToken", {}).get("name", "Unknown")
                            dex_url = pair.get("url", f"https://dexscreener.com/{chain_id}/{token_address}")
                            
                            # شروط الزخم والسيولة الحية (تجنب العملات الميتة)
                            if liq > 1000 and buys > 2:
                                sent_tokens.add(token_address)
                                if len(sent_tokens) > 500: # تنظيف الذاكرة دورياً
                                    sent_tokens.clear()
                                    
                                event_msg = (
                                    f"🌐 *رصد فرصة عبر سلسلة ({chain_id.upper()})*\n\n"
                                    f"🪙 الاسم: *{name}* (`{symbol}`)\n"
                                    f"💧 السيولة: *${liq:,.2f}*\n"
                                    f"📈 عمليات الشراء (ساعة): *{buys} شراء* مقابل *{sells} بيع*\n"
                                    f"📊 حجم التداول: *${vol:,.2f}*\n\n"
                                    f"🔑 العقد:\n`{token_address}`\n\n"
                                    f"🔗 [DexScreener]({dex_url})"
                                )
                                engine_status["last_event"] = event_msg
                                print(f"✅ تم رصد توكن على {chain_id}: {symbol} | سيولة: {liq}")
                                send_telegram_alert(event_msg)
    except Exception as e:
        print(f"❌ خطأ في فحص السلاسل المتعددة: {e}")

def worker_loop():
    while True:
        fetch_latest_multichain_tokens()
        time.sleep(10) # فحص دوري كل 10 ثوانٍ لجميع السلاسل

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    print("✅ تم تفعيل رادار السلاسل المتعددة بنجاح!")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=10000)
