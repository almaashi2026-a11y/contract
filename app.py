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
    "last_event": "Sniper mode active: Waiting for second-one launches..."
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Instant First-Second Multi-Chain Pump Sniper",
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
        requests.post(url, json=payload, timeout=3)
    except Exception as e:
        print(f"❌ خطأ تليجرام: {e}")

processed_signatures = set()

def monitor_solana_instant_pumps():
    """رصد فوري لعقد Pump.fun على سولانا من الثانية الأولى"""
    global processed_signatures
    if not RPC_URL:
        return

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [
            "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P", # عقد Pump.fun الأساسي
            {"limit": 5}
        ]
    }
    
    try:
        response = requests.post(RPC_URL, json=payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            transactions = data.get("result", [])
            for tx in reversed(transactions):
                sig = tx.get("signature", "")
                if sig and sig not in processed_signatures:
                    processed_signatures.add(sig)
                    if len(processed_signatures) > 1000:
                        processed_signatures.clear()
                    
                    # تنبيه فوري من الثانية الأولى وقبل اكتمال فهرسة المنصات
                    event_msg = (
                        f"⚡🚨 *قنبلة ولادة عملة جديدة (من الثانية الأولى)!*\n\n"
                        f"⛓️ الشبكة: *Solana (Pump.fun)*\n"
                        f"🔑 المعاملة العقدية:\n`{sig}`\n\n"
                        f"🔗 [متابعة فورية على DexScreener](https://dexscreener.com/solana/{sig})\n"
                        f"🛡️ [فحص BubbleMaps](https://app.bubblemaps.io/solana/{sig})"
                    )
                    engine_status["last_event"] = event_msg
                    print(f"🚀 تم رصد انطلاقة فورية على سولانا: {sig}")
                    send_telegram_alert(event_msg)
    except Exception as e:
        print(f"❌ خطأ في رصد سولانا الفوري: {e}")

def monitor_multichain_latest_tokens():
    """رصد أحدث الأزواج والسيولة المضافة عالمياً على جميع السلاسل"""
    global processed_signatures
    try:
        url = "https://api.dexscreener.com/latest/dex/search?q=boosted" # أو جلب الأحدث
        # بدلاً من ذلك، نستخدم نقطة نهاية أحدث البوستر والتوكنات المضافة
        trending_url = "https://api.dexscreener.com/token-boosts/latest/v1"
        res = requests.get(trending_url, timeout=5)
        if res.status_code == 200:
            tokens = res.json()
            if isinstance(tokens, list):
                for item in tokens[:5]:
                    chain_id = item.get("chainId", "unknown")
                    token_address = item.get("tokenAddress", "")
                    
                    if not token_address or token_address in processed_signatures:
                        continue
                    
                    processed_signatures.add(token_address)
                    
                    event_msg = (
                        f"🌐🔥 *رصد إطلاق جديد ومبكر عبر ({chain_id.upper()})*\n\n"
                        f"🔑 العقد:\n`{token_address}`\n\n"
                        f"🔗 [فتح DexScreener](https://dexscreener.com/{chain_id}/{token_address})"
                    )
                    engine_status["last_event"] = event_msg
                    print(f"✅ تم رصد توكن مبكر على {chain_id}: {token_address}")
                    send_telegram_alert(event_msg)
    except Exception as e:
        print(f"❌ خطأ في فحص السلاسل الأخرى: {e}")

def worker_loop():
    while True:
        monitor_solana_instant_pumps()
        monitor_multichain_latest_tokens()
        time.sleep(1.5) # فحص متواصل وعالي السرعة كل ثانية ونصف

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    print("✅ تم تفعيل رادار القنص الفوري من الثانية الأولى بنجاح!")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=10000)
