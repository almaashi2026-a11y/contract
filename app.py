import os
import time
import requests
from fastapi import FastAPI
import uvicorn
import threading

app = FastAPI()

# إعدادات الاتصال والتوكن والـ ID الصحيح
RPC_URL = os.environ.get("SOLANA_RPC_URL", "")
TG_TOKEN = "8517074768:AAG1NQKsDBOFpd07QrSXFYZ2qGwcVv0huak"
TG_CHAT_ID = "8517074768"

engine_status = {
    "status": "Running",
    "last_event": "Waiting for transactions..."
}

@app.get("/")
def health_check():
    """مسار الحفاظ على السيرفر نشطاً على Render"""
    return {
        "status": "online",
        "engine": "Solana Pump.fun Telegram Radar",
        "details": engine_status
    }

def send_telegram_alert(message: str):
    """دالة إرسال التنبيهات المباشرة إلى تليجرام"""
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code != 200:
            print(f"❌ خطأ تليجرام (رد السيرفر): {response.text}")
        else:
            print("📤 تم إرسال التنبيه إلى تليجرام بنجاح!")
    except Exception as e:
        print(f"❌ خطأ في اتصال تليجرام: {e}")

# متغير لتخزين آخر تفعيل تم إرساله لمنع التكرار
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
                
                # إذا ظهر عقد جديد لم يتم إرساله من قبل
                if sig and sig != last_sent_signature:
                    last_sent_signature = sig
                    event_msg = f"🚨 *تم رصد عقد جديد على Pump.fun!*\n\n`{sig}`\n\n🔗 [DexScreener](https://dexscreener.com/solana/{sig})"
                    engine_status["last_event"] = event_msg
                    print(event_msg)
                    
                    # إرسال التنبيه إلى تليجرام
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
    print("✅ تم بدء تشغيل الرادار وتليجرام بنجاح!")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=10000)
