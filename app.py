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
    "last_event": "Solana Pre-Launch & Accumulation Sniper Active..."
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Solana Pre-Launch Smart Money Sniper",
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

def analyze_pre_launch_accumulation(token_address: str) -> dict:
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        res = requests.get(url, timeout=2)
        if res.status_code == 200:
            data = res.json()
            pairs = data.get("pairs", [])
            if pairs:
                sol_pairs = [p for p in pairs if p.get("chainId"] == "solana"]
                if not sol_pairs:
                    return {"valid": False}
                
                pair = sol_pairs[0]
                liq = pair.get("liquidity", {}).get("usd", 0)
                fdv = pair.get("fdv", 0)
                
                txns = pair.get("txns", {})
                m5 = txns.get("m5", {})
                buys = m5.get("buys", 0)
                sells = m5.get("sells", 0)
                
                symbol = pair.get("baseToken", {}).get("symbol", "EARLY")
                name = pair.get("baseToken", {}).get("name", "Pre-Launch Token")
                pair_url = pair.get("url", f"https://dexscreener.com/solana/{token_address}")
                
                # شروط ما قبل الانفجار واكتتاب المحافظ: شراء حصري بدون أي مبيعات وسيولة تجميعية مبكرة
                if buys >= 2 and sells == 0 and 1000 <= liq <= 25000:
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

def run_pre_launch_sniper():
    global processed_tokens
    try:
        trending_url = "https://api.dexscreener.com/token-boosts/latest/v1"
        res = requests.get(trending_url, timeout=3)
        if res.status_code == 200:
            items = res.json()
            if isinstance(items, list):
                for item in items:
                    chain_id = item.get("chainId", "")
                    if chain_id != "solana":
                        continue
                        
                    token_address = item.get("tokenAddress", "")
                    if token_address and token_address not in processed_tokens:
                        processed_tokens.add(token_address)
                        if len(processed_tokens) > 4000:
                            processed_tokens.clear()
                            
                        metrics = analyze_pre_launch_accumulation(token_address)
                        if metrics.get("valid"):
                            liq = metrics.get("liquidity", 0)
                            fdv = metrics.get("fdv", 0)
                            buys = metrics.get("buys", 0)
                            sells = metrics.get("sells", 0)
                            symbol = metrics.get("symbol", "EARLY")
                            name = metrics.get("name", "Token")
                            url = metrics.get("url", f"https://dexscreener.com/solana/{token_address}")
                            
                            event_msg = (
                                f"🚀💎 *رصد مرحلة الاكتتاب والتجميع المبكر (Pre-Launch)*\n\n"
                                f"🪙 التوكن: {name} (`{symbol}`)\n"
                                f"💧 السيولة التجميعية: `${liq:,.2f}`\n"
                                f"📈 القيمة السوقية: `${fdv:,.2f}`\n"
                                f"🛒 عمليات الشراء الصافي: `{buys}` شراء 🟢 | البيع: `0` (احتفاظ كامل)\n\n"
                                f"🔑 عقد التوكن (قبل الانفجار):\n`{token_address}`\n\n"
                                f"🔍 *أدوات الفحص والتحقق الإجباري قبل الدخول:*\n"
                                f"🔗 [DexScreener]({url})\n"
                                f"🛡️ [BubbleMaps (فحص تركز المحافظ والمطور)](https://app.bubblemaps.io/solana/{token_address})\n"
                                f"⚡ [GMGN (تتبع حيتان الشراء)](https://gmgn.ai/solana/token/{token_address})"
                            )
                            engine_status["last_event"] = event_msg
                            send_telegram_alert(event_msg)
    except Exception:
        pass

def worker_loop():
    while True:
        run_pre_launch_sniper()
        time.sleep(0.05)

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    print("🚀 تم تفعيل محرك اكتتاب وتجميع المحافظ المبكرة على سولانا بنجاح!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
