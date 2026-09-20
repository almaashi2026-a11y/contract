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
    "last_event": "Smart Money Holder Sniper Active..."
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Elite Smart Money Holder Sniper",
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

def analyze_smart_money_holders(token_address: str, chain_id: str) -> dict:
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
                fdv = pair.get("fdv", 0)
                
                txns = pair.get("txns", {})
                m5 = txns.get("m5", {})
                buys = m5.get("buys", 0)
                sells = m5.get("sells", 0)
                
                symbol = pair.get("baseToken", {}).get("symbol", "WHALE")
                name = pair.get("baseToken", {}).get("name", "Smart Token")
                pair_url = pair.get("url", f"https://dexscreener.com/{chain_id}/{token_address}")
                
                if buys >= 3 and sells <= 1 and liq >= 800:
                    return {
                        "valid": True,
                        "liquidity": liq,
                        "fdv": fdv,
                        "buys": buys,
                        "sells": sells,
                        "symbol": symbol,
                        "name": name,
                        "url": pair_url
                    }
    except Exception:
        pass
    return {"valid": False}

def run_smart_money_scanner():
    global processed_tokens
    try:
        trending_url = "https://api.dexscreener.com/token-boosts/latest/v1"
        res = requests.get(trending_url, timeout=3)
        if res.status_code == 200:
            items = res.json()
            if isinstance(items, list):
                for item in items[:10]:
                    chain_id = item.get("chainId", "solana")
                    token_address = item.get("tokenAddress", "")
                    
                    if token_address and token_address not in processed_tokens:
                        processed_tokens.add(token_address)
                        if len(processed_tokens) > 4000:
                            processed_tokens.clear()
                            
                        metrics = analyze_smart_money_holders(token_address, chain_id)
                        if metrics.get("valid"):
                            liq = metrics.get("liquidity", 0)
                            fdv = metrics.get("fdv", 0)
                            buys = metrics.get("buys", 0)
                            sells = metrics.get("sells", 0)
                            symbol = metrics.get("symbol", "WHALE")
                            name = metrics.get("name", "Token")
                            url = metrics.get("url", f"https://dexscreener.com/{chain_id}/{token_address}")
                            
                            event_msg = (
                                f"💎🐋 *صيد محفظة ذكية تحتفظ (Smart Money Holder)*\n\n"
                                f"⛓️ الشبكة: *{chain_id.upper()}*\n"
                                f"🪙 التوكن: *{name}* (`{symbol}`)\n"
                                f"💧 السيولة: *${liq:,.2f}* \vert{} القيمة السوقية: *${fdv:,.2f}*\n"
                                f"🛒 الزخم الفوري: *{buys} شراء* 🟢 مقابل *{sells} بيع* 🔴\n\n"
                                f"🔑 عقد التوكن:\n`{token_address}`\n\n"
                                f"📊 أدوات التحليل الفوري والاحتفاظ:\n"
                                f"🔗 [DexScreener]({url})\n"
                                f"🛡️ [BubbleMaps (فحص الموزعين)](https://app.bubblemaps.io/{chain_id}/{token_address})\n"
                                f"⚡ [GMGN (تتبع المحافظ الحية)](https://gmgn.ai/{chain_id}/token/{token_address})\n"
                                f"🤖 [Trojan Bot (تنفيذ سريع)](https://t.me/Paris_TrojanBot?start=r-1)"
                            )
                            engine_status["last_event"] = event_msg
                            send_telegram_alert(event_msg)
    except Exception:
        pass

def worker_loop():
    while True:
        run_smart_money_scanner()
        time.sleep(0.05)

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    print("🚀 تم تفعيل محرك رصد المحافظ الذكية والاحتفاظ بنجاح تام!")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=10000)
