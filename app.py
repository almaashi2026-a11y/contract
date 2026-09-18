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

engine_status = {
    "status": "Running",
    "last_event": "Waiting for tokens..."
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Solana Flexible Pump Radar",
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
    """استخراج عنوان التوكن الفعلي (Mint) من تفاصيل المعاملة بدقة"""
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

def get_token_info(mint_address: str) -> dict:
    """محاولة جلب معلومات العملة من DexScreener، وفي حال عدم التوفر نعيد بيانات افتراضية لكي لا يتعطل الإرسال"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{mint_address}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            pairs = data.get("pairs", [])
            if pairs:
                sol_pairs = [p for p in pairs if p.get("chainId"] == "solana"]
                if sol_pairs:
                    pair = sol_pairs[0]
                    return {
                        "liquidity": pair.get("liquidity", {}).get("usd", 0),
                        "volume": pair.get("volume", {}).get("h1", 0),
                        "symbol": pair.get("baseToken", {}).get("symbol", "NEW"),
                        "name": pair.get("baseToken", {}).get("name", "Pump Token"),
                        "url": pair.get("url", f"https://dexscreener.com/solana/{mint_address}")
                    }
    except Exception:
        pass
    
    return {
        "liquidity": 0,
        "volume": 0,
        "symbol": "NEW",
        "name": "Pump Token",
        "url": f"https://dexscreener.com/solana/{mint_address}"
    }

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
                        # إذا تعذر استخراج المينت، نرسل المعاملة الاحتياطية لضمان عدم توقف البوت
                        mint_address = sig
                    
                    info = get_token_info(mint_address)
                    liq = info.get("liquidity", 0)
                    vol = info.get("volume", 0)
                    symbol = info.get("symbol")
                    name = info.get("name")
                    pair_url = info.get("url")
                    
                    # فلترة سريعة تتجنب فقط العملات الضخمة جداً (فوق 50,000$) وتترك الخفيفة والجديدة تمر كلها
                    if liq <= 50000:
                        event_msg = (
                            f"⚡ *رصد عقد عملة جديدة (Pump.fun)*\n\n"
                            f"🪙 الاسم: *{name}* (`{symbol}`)\n"
                            f"💧 السيولة: *${liq:,.2f}*\n"
                            f"📊 التداول: *${vol:,.2f}*\n\n"
                            f"🔑 العقد:\n`{mint_address}`\n\n"
                            f"🔗 [DexScreener]({pair_url})\n"
                            f"🛡️ [BubbleMaps](https://app.bubblemaps.io/solana/{mint_address})"
                        )
                        engine_status["last_event"] = event_msg
                        print(f"✅ تم إرسال العقد الخفيف بنجاح: {mint_address}")
                        send_telegram_alert(event_msg)
    except Exception as e:
        print(f"❌ خطأ في الجلب: {e}")

def worker_loop():
    while True:
        fetch_latest_pump_tokens()
        time.sleep(2)

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    print("✅ تم تفعيل الرادار المرن بنجاح!")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=10000)
