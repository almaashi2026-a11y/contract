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
    "last_event": "Solana Pre-Launch Sniper Initialized Successfully"
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Solana Pre-Launch Accumulation Sniper",
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
    except Exception:
        pass

processed_tokens = set()

def run_sniper_logic():
    global processed_tokens
    while True:
        try:
            trending_url = "https://api.dexscreener.com/token-boosts/latest/v1"
            res = requests.get(trending_url, timeout=4)
            if res.status_code == 200:
                items = res.json()
                if isinstance(items, list):
                    for item in items:
                        if item.get("chainId") != "solana":
                            continue
                        
                        token_address = item.get("tokenAddress", "")
                        if token_address and token_address not in processed_tokens:
                            processed_tokens.add(token_address)
                            if len(processed_tokens) > 2000:
                                processed_tokens.clear()
                            
                            # جلب تفاصيل التوكن
                            token_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
                            t_res = requests.get(token_url, timeout=2)
                            if t_res.status_code == 200:
                                t_data = t_res.json()
                                pairs = t_data.get("pairs", [])
                                if pairs:
                                    pair = pairs[0]
                                    liq = pair.get("liquidity", {}).get("usd", 0)
                                    fdv = pair.get("fdv", 0)
                                    txns = pair.get("txns", {}).get("m5", {})
                                    buys = txns.get("buys", 0)
                                    sells = txns.get("sells", 0)
                                    
                                    symbol = pair.get("baseToken", {}).get("symbol", "EARLY")
                                    name = pair.get("baseToken", {}).get("name", "Token")
                                    dex_url = pair.get("url", f"https://dexscreener.com/solana/{token_address}")
                                    
                                    # شروط التجميع المبكر واكتتاب المحافظ (شراء بدون بيع وسيولة أولية)
                                    if buys >= 2 and sells == 0 and 500 <= liq <= 30000:
                                        msg = (
                                            f"🚀💎 *رصد اكتتاب وتجميع مبكر (Pre-Launch)*\n\n"
                                            f"🪙 التوكن: {name} (`{symbol}`)\n"
                                            f"💧 السيولة: `${liq:,.2f}`\n"
                                            f"📈 القيمة السوقية: `${fdv:,.2f}`\n"
                                            f"🛒 شراء: `{buys}` 🟢 | بيع: `0` (احتفاظ تام)\n\n"
                                            f"🔑 العقد:\n`{token_address}`\n\n"
                                            f"📊 *روابط الفحص:*\n"
                                            f"🔗 [DexScreener]({dex_url})\n"
                                            f"🛡️ [BubbleMaps](https://app.bubblemaps.io/solana/{token_address})\n"
                                            f"⚡ [GMGN](https://gmgn.ai/solana/token/{token_address})"
                                        )
                                        engine_status["last_event"] = msg
                                        send_telegram_alert(msg)
        except Exception:
            pass
        
        time.sleep(2) # مؤقت خفيف لمنع الضغط على السيرفر والطلبات

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=run_sniper_logic, daemon=True)
    t.start()
    print("🚀 Background worker started successfully!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
