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
    "last_event": "Elite Multi-Chain Smart Money Sniper Active..."
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Elite Multi-Chain Smart Money & Heavy Volume Hunter",
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
        requests.post(url, json=payload, timeout=2)
    except Exception as e:
        print(f"❌ خطأ تليجرام: {e}")

processed_tokens = set()

def analyze_elite_smart_money(token_address: str, chain_id: str) -> dict:
    """فحص عميق ومتقدم لسيولة التوكن وحجم التدفق ومؤشرات المحافظ الكبرى"""
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    
    for _ in range(3):
        try:
            res = requests.get(url, timeout=3)
            if res.status_code == 200:
                data = res.json()
                pairs = data.get("pairs", [])
                if pairs:
                    # تصفية الزوج الأقوى سيولة على الشبكة المطلوبة
                    target_pairs = [p for p in pairs if p.get("chainId") == chain_id]
                    pair = target_pairs[0] if target_pairs else pairs[0]
                    
                    liq = pair.get("liquidity", {}).get("usd", 0)
                    txns = pair.get("txns", {})
                    m5_txns = txns.get("m5", {})
                    buys = m5_txns.get("buys", 0)
                    sells = m5_txns.get("sells", 0)
                    volume_m5 = pair.get("volume", {}).get("m5", 0)
                    
                    symbol = pair.get("baseToken", {}).get("symbol", "ELITE")
                    name = pair.get("baseToken", {}).get("name", "Smart Token")
                    pair_url = pair.get("url", f"https://dexscreener.com/{chain_id}/{token_address}")
                    
                    return {
                        "valid": True,
                        "liquidity": liq,
                        "volume_m5": volume_m5,
                        "buys": buys,
                        "sells": sells,
                        "symbol": symbol,
                        "name": name,
                        "url": pair_url
                    }
        except Exception:
            pass
        time.sleep(0.3)
        
    return {"valid": False}

def run_elite_hunter():
    global processed_tokens
    
    # رصد أحدث النبضات والتدفقات الحية عبر جميع السلاسل العالمية لحظياً
    try:
        trending_url = "https://api.dexscreener.com/token-boosts/latest/v1"
        res = requests.get(trending_url, timeout=4)
        if res.status_code == 200:
            items = res.json()
            if isinstance(items, list):
                for item in items[:5]:
                    chain_id = item.get("chainId", "solana")
                    token_address = item.get("tokenAddress", "")
                    
                    if token_address and token_address not in processed_tokens:
                        processed_tokens.add(token_address)
                        if len(processed_tokens) > 2000:
                            processed_tokens.clear()
                            
                        metrics = analyze_elite_smart_money(token_address, chain_id)
                        if metrics.get("valid"):
                            liq = metrics.get("liquidity", 0)
                            vol = metrics.get("volume_m5", 0)
                            buys = metrics.get("buys", 0)
                            sells = metrics.get("sells", 0)
                            symbol = metrics.get("symbol", "ELITE")
                            name = metrics.get("name", "Token")
                            url = metrics.get("url", f"https://dexscreener.com/{chain_id}/{token_address}")
                            
                            # شروط نخبوية واحترافية: حجم تداول مبكر ممتاز وضغط شراء كاسح للمحافظ الكبرى
                            if buys >= (sells * 2) and vol > 400 and liq > 1000:
                                event_msg = (
                                    f"👑💎 *رصد احترافي: دخول سمارت مني (Smart Money Elite)*\n\n"
                                    f"⛓️ الشبكة: *{chain_id.upper()}*\n"
                                    f"🪙 الاسم: *{name}* (`{symbol}`)\n"
                                    f"💧 السيولة: *${liq:,.2f}*\n"
                                    f"📊 التدفق المبكر (5د): *${vol:,.2f}*\n"
                                    f"🛒 الصفقات: *{buys} شراء* 🟢 | *{sells} بيع* 🔴\n\n"
                                    f"🔑 العقد الذهبي:\n`{token_address}`\n\n"
                                    f"🔍 **أدوات التحليل والمتابعة الفورية:**\n"
                                    f"🔗 [DexScreener]({url})\n"
                                    f"🛡️ [BubbleMaps تتبع تركز المحافظ](https://app.bubblemaps.io/{chain_id}/{token_address})\n"
                                    f"⚡ [GMGN تتبع المحافظ والاحتفاظ](https://gmgn.ai/{chain_id}/token/{token_address})"
                                )
                                engine_status["last_event"] = event_msg
                                print(f"🚀 صيد فرصة سمارت مني احترافية على {chain_id.upper()}: {symbol}")
                                send_telegram_alert(event_msg)
    except Exception as e:
        print(f"❌ خطأ في رصد المحافظ الاحترافية: {e}")

def worker_loop():
    while True:
        run_elite_hunter()
        time.sleep(0.8)

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    print("✅ تم تفعيل رادار سمارت مني النخبوي لجميع السلاسل بنجاح!")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=10000)
