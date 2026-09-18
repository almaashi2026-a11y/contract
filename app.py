import os
import time
import requests
from fastapi import FastAPI
import uvicorn
import threading

app = FastAPI()

RPC_URL = os.environ.get("SOLANA_RPC_URL", "")
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# نطاق السيولة للعملات الخفيفة والنشطة (من 500$ إلى 15,000$ فقط لتجنب الثقيلة)
MIN_LIQUIDITY_USD = 500.0
MAX_LIQUIDITY_USD = 15000.0  

engine_status = {
    "status": "Running",
    "last_event": "Waiting for light & fresh tokens..."
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Solana Light & Fresh Pump Radar",
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

def get_token_mint_from_tx(signature: str) -> str:
    """استخراج عنوان التوكن الفعلي (Mint) من تفاصيل المعاملة"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
            ]
        }
        res = requests.post(RPC_URL, json=payload, timeout=5)
        if res.status_code == 200:
            data = res.json()
            result = data.get("result")
            if result:
                meta = result.get("meta", {})
                post_balances = meta.get("postTokenBalances", [])
                for pb in post_balances:
                    mint = pb.get("mint")
                    if mint and mint != "So11111111111111111111111111111111111111112":
                        return mint
    except Exception:
        pass
    return ""

def check_dexscreener_metrics(mint_address: str) -> dict:
    """فحص سيولة التوكن والتأكد من أنه خفيف ونشط"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{mint_address}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            pairs = data.get("pairs", [])
            if pairs:
                sol_pairs = [p for p in pairs if p.get("chainId") == "solana"]
                if sol_pairs:
                    pair = sol_pairs[0]
                    liquidity = pair.get("liquidity", {}).get("usd", 0)
                    h1_volume = pair.get("volume", {}).get("h1", 0)
                    symbol = pair.get("baseToken", {}).get("symbol", "UNKNOWN")
                    name = pair.get("baseToken", {}).get("name", "Unknown Token")
                    return {
                        "valid": True,
                        "liquidity": liquidity,
                        "volume_h1": h1_volume,
                        "symbol": symbol,
                        "name": name,
                        "pair_url": pair.get("url", f"https://dexscreener.com/solana/{mint_address}")
                    }
    except Exception:
        pass
    return {"valid": False}

last_sent_signature = ""

def fetch_latest_pump_tokens():
    global last_sent_signature
    if not RPC_URL:
        return

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [
            "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P", # عقد Pump.fun
            {"limit": 5}
        ]
    }
    
    try:
        response = requests.post(RPC_URL, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            transactions = data.get("result", [])
            if transactions:
                latest_tx = transactions[0]
                sig = latest_tx.get("signature", "")
                
                if sig and sig != last_sent_signature:
                    last_sent_signature = sig
                    
                    mint_address = get_token_mint_from_tx(sig)
                    if not mint_address:
                        return
                    
                    metrics = check_dexscreener_metrics(mint_address)
                    if metrics.get("valid"):
                        liquidity = metrics.get("liquidity", 0)
                        
                        # فلترة العملات الخفيفة حصراً (السيولة بين الحد الأدنى والأقصى)
                        if MIN_LIQUIDITY_USD <= liquidity <= MAX_LIQUIDITY_USD:
                            symbol = metrics.get("symbol")
                            name = metrics.get("name")
                            volume = metrics.get("volume_h1")
                            pair_url = metrics.get("pair_url")
                            
                            event_msg = (
                                f"⚡ *عقد عملة خفيفة وجديدة (Pump.fun)*\n\n"
                                f"🪙 الاسم: *{name}* (`{symbol}`)\n"
                                f"💧 السيولة الخفيفة: *${liquidity:,.2f}*\n"
                                f"📊 التداول: *${volume:,.2f}*\n\n"
                                f"🔑 العقد:\n`{mint_address}`\n\n"
                                f"🔗 [فتح DexScreener]({pair_url})\n"
                                f"🛡️ [فحص BubbleMaps](https://app.bubblemaps.io/solana/{mint_address})"
                            )
                            engine_status["last_event"] = event_msg
                            print(f"🚀 تم رصد عملة خفيفة: {symbol} سيولة: {liquidity}")
                            send_telegram_alert(event_msg)
    except Exception as e:
        print(f"❌ خطأ في الفحص: {e}")

def worker_loop():
    while True:
        fetch_latest_pump_tokens()
        time.sleep(2)

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    print("✅ تم تفعيل رادار العملات الخفيفة والنشطة بنجاح!")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=10000)
