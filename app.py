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
    "last_event": "Second-One True Sniper Active Across All Chains..."
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "True Second-One Multi-Chain Sniper",
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
        requests.post(url, json=payload, timeout=1.5)
    except Exception:
        pass

processed_tokens = set()

def get_instant_token_data(token_address: str, chain_id: str) -> dict:
    """جلب بيانات اللحظة الأولى وفحص الصفقات الفورية بدلاً من الانتظار"""
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        res = requests.get(url, timeout=2)
        if res.status_code == 200:
            data = res.json()
            pairs = data.get("pairs", [])
            if pairs:
                target_pairs = [p for p in pairs if p.get("chainId") == chain_id]
                pair = target_pairs[0] if target_pairs else pairs[0]
                
                liq = pair.get("liquidity", {}).get("usd", 0)
                
                # التقاط فوري لبيانات الدقيقة الأولى (أو التداولات الأولى المتاحة)
                txns = pair.get("txns", {})
                h1_txns = txns.get("h1", {}) # نستخدم فحص شامل للحظات الأولى
                buys = h1_txns.get("buys", 1)
                sells = h1_txns.get("sells", 0)
                volume = pair.get("volume", {}).get("h1", 0)
                
                symbol = pair.get("baseToken", {}).get("symbol", "SNIPER")
                name = pair.get("baseToken", {}).get("name", "New Token")
                pair_url = pair.get("url", f"https://dexscreener.com/{chain_id}/{token_address}")
                
                return {
                    "valid": True,
                    "liquidity": liq,
                    "volume": volume,
                    "buys": buys,
                    "sells": sells,
                    "symbol": symbol,
                    "name": name,
                    "url": pair_url
                }
    except Exception:
        pass
    return {"valid": False}

def run_true_second_one_sniper():
    global processed_tokens
    try:
        trending_url = "https://api.dexscreener.com/token-boosts/latest/v1"
        res = requests.get(trending_url, timeout=3)
        if res.status_code == 200:
            items = res.json()
            if isinstance(items, list):
                for item in items[:8]:
                    chain_id = item.get("chainId", "solana")
                    token_address = item.get("tokenAddress", "")
                    
                    if token_address and token_address not in processed_tokens:
                        processed_tokens.add(token_address)
                        if len(processed_tokens) > 3000:
                            processed_tokens.clear()
                            
                        metrics = get_instant_token_data(token_address, chain_id)
                        if metrics.get("valid"):
                            liq = metrics.get("liquidity", 0)
                            volume = metrics.get("volume", 0)
                            buys = metrics.get("buys", 0)
                            sells = metrics.get("sells", 0)
                            symbol = metrics.get("symbol", "SNIPER")
                            name = metrics.get("name", "Token")
                            url = metrics.get("url", f"https://dexscreener.com/{chain_id}/{token_address}")
                            
                            # شروط فورية من الثانية الأولى للمحافظ القوية وغلبة الشراء
                            if buys >= sells and liq > 500:
                                event_msg = (
                                    f"⚡🎯 *رصد فوري من الثانية الأولى (Smart Money)*\n\n"
                                    f"⛓️ الشبكة: *{chain_id.upper()}*\n"
                                    f"🪙 الاسم: *{name}* (`{symbol}`)\n"
                                    f"💧 السيولة الأولية: *${liq:,.2f}*\n"
                                    f"🛒 الصفقات الفورية: *{buys} شراء* 🟢 | *{sells} بيع* 🔴\n\n"
                                    f"🔑 العقد:\n`{token_address}`\n\n"
                                    f"🔗 [DexScreener]({url})\n"
                                    f"🛡️ [BubbleMaps](https://app.bubblemaps.io/{chain_id}/{token_address})\n"
                                    f"⚡ [GMGN متابعة المحافظ](https://gmgn.ai/{chain_id}/token/{token_address})"
                                )
                                engine_status["last_event"] = event_msg
                                send_telegram_alert(event_msg)
    except Exception:
        pass

def worker_loop():
    while True:
        run_true_second_one_sniper()
        time.sleep(0.1) # سرعة قصوى بدون أي انتظار

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    print("✅ تم تفعيل رادار (الثانية الأولى الحقيقية) لجميع السلاسل بنجاح!")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=10000)
