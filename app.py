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

# الحد الأدنى للسيولة بالدولار لاعتبار التوكن جيداً وقابلاً للتداول
MIN_LIQUIDITY_USD = 2000.0  

engine_status = {
    "status": "Running",
    "last_event": "Waiting for high-liquidity tokens..."
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Solana Pump.fun Smart Filter Radar",
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
    """استخراج عنوان التوكن الفعلي (Mint) من تفاصيل المعاملة عبر RPC"""
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
                # البحث عن الحسابات الجديدة أو الـ postTokenBalances لاستخراج عقد التوكن
                meta = result.get("meta", {})
                post_balances = meta.get("postTokenBalances", [])
                for pb in post_balances:
                    mint = pb.get("mint")
                    # تجاهل عملة SOL نفسها والتركيز على التوكنات الجديدة
                    if mint and mint != "So11111111111111111111111111111111111111112":
                        return mint
    except Exception:
        pass
    return ""

def check_dexscreener_metrics(mint_address: str) -> dict:
    """فحص السيولة وحجم التداول ومعلومات التوكن عبر DexScreener"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{mint_address}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            pairs = data.get("pairs", [])
            if pairs:
                # تصفية أزواج شبكة سولانا
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
                    
                    # 1. استخراج عنوان التوكن الحقيقي
                    mint_address = get_token_mint_from_tx(sig)
                    if not mint_address:
                        return
                    
                    # 2. فحص السيولة والمؤشرات عبر DexScreener
                    metrics = check_dexscreener_metrics(mint_address)
                    if metrics.get("valid"):
                        liquidity = metrics.get("liquidity", 0)
                        
                        # فلترة الصفقات حسب الحد الأدنى للسيولة
                        if liquidity >= MIN_LIQUIDITY_USD:
                            symbol = metrics.get("symbol")
                            name = metrics.get("name")
                            volume = metrics.get("volume_h1")
                            pair_url = metrics.get("pair_url")
                            
                            event_msg = (
                                f"💎 *تم رصد عقد قوي بـ Pump.fun!*\n\n"
                                f"🪙 الاسم: *{name}* (`{symbol}`)\n"
                                f"💧 السيولة: *${liquidity:,.2f}*\n"
                                f"📊 حجم التداول (ساعة): *${volume:,.2f}*\n\n"
                                f"🔑 العقد:\n`{mint_address}`\n\n"
                                f"🔗 [فتح DexScreener]({pair_url})\n"
                                f"🛡️ [فحص BubbleMaps](https://app.bubblemaps.io/solana/{mint_address})"
                            )
                            engine_status["last_event"] = event_msg
                            print(f"✅ تم إرسال تنبيه لتوكن ممتاز: {symbol} سيولة: {liquidity}")
                            send_telegram_alert(event_msg)
    except Exception as e:
        print(f"❌ خطأ في الفحص: {e}")

def worker_loop():
    while True:
        fetch_latest_pump_tokens()
        time.sleep(3)

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    print("✅ تم بدء تشغيل الرادار بفلترة السيولة بنجاح!")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=10000)
