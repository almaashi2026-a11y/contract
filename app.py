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
    "last_event": "Waiting for transactions..."
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
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"❌ خطأ تليجرام: {e}")

last_sent_signature = ""

def check_token_metrics(mint_address: str) -> bool:
    """
    مستقبلاً: دالة لفحص السيولة أو حجم التداول عبر DexScreener API 
    لضمان أن العقد يحمل سيولة حقيقية قبل التنبيه.
    """
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{mint_address}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            pairs = data.get("pairs", [])
            if pairs:
                # مثال: التأكد من أن زوج التداول على سولانا ولديه حد أدنى من السيولة
                solana_pairs = [p for p in pairs if p.get("chainId") == "solana"]
                if solana_pairs:
                    liquidity = solana_pairs[0].get("liquidity", {}).get("usd", 0)
                    # شرط مبدئي: يمكنك تعديل رقم السيولة الأدنى حسب رغبتك (مثلاً 5000 دولار)
                    if liquidity >= 1000: 
                        return True
        return False
    except Exception:
        return True # في حال الخطأ نمرر التنبيه مؤقتاً

def fetch_latest_pump_tokens():
    global last_sent_signature
    if not RPC_URL:
        return

    payload = {
        "jsonrcp": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [
            "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
            {"limit": 3}
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
                    
                    # يمكنك هنا جلب عنوان التوكن الفعلي من تفاصيل المعاملة وفحصه
                    event_msg = (
                        f"🚀 *صید عُقد مميز على Pump.fun!*\n\n"
                        f"🔑 المعاملة:\n`{sig}`\n\n"
                        f"🔗 [تحليل DexScreener](https://dexscreener.com/solana/{sig})\n"
                        f"🛡️ [فحص BubbleMaps](https://app.bubblemaps.io/solana/{sig})"
                    )
                    engine_status["last_event"] = event_msg
                    send_telegram_alert(event_msg)
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")

def worker_loop():
    while True:
        fetch_latest_pump_tokens()
        time.sleep(2)

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    print("✅ تم تفعيل رادار الفلترة الذكية بنجاح!")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=10000)
