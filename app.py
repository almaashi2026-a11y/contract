import os
import time
import requests
from fastapi import FastAPI
import uvicorn

app = FastAPI()

# قراءة رابط الـ RPC الأساسي
RPC_URL = os.environ.get("SOLANA_RPC_URL", "")

engine_status = {
    "status": "Running",
    "last_event": "Waiting for transactions..."
}

@app.get("/")
def health_check():
    """مسار الحفاظ على السيرفر نشطاً على Render"""
    return {
        "status": "online",
        "engine": "Solana Pump.fun Polling Radar",
        "details": engine_status
    }

def fetch_latest_pump_tokens():
    """فحص أحدث المعاملات لعقد Pump.fun عبر HTTP RPC"""
    if not RPC_URL:
        print("⚠️ رابط RPC غير موجود في متغيرات البيئة.")
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
                # نأخذ أحدث معاملة تم رصدها
                latest_tx = transactions[0]
                sig = latest_tx.get("signature", "")
                event_msg = f"🚨 تم رصد نشاط جديد على Pump.fun! التوقيع: {sig}"
                engine_status["last_event"] = event_msg
                print(event_msg)
        else:
            print(f"⚠️ خطأ في الاستعلام HTTP: {response.status_code}")
    except Exception as e:
        print(f"❌ خطأ في الاتصال: {e}")

import threading

def background_worker():
    """حلقة عمل تعمل في الخلفية لفحص الشبكة كل ثانيتين"""
    while True:
        fetch_latest_pump_tokens()
        time.sleep(2) # فحص كل ثوانٍ لتجنب الضغط على الخادم

@app.on_event("startup")
def startup_event():
    """بدء المراقبة فور تشغيل السيرفر"""
    t = threading.Thread(target=background_worker, daemon=True)
    t.start()
    print("✅ تم بدء تشغيل رادار البلوكتشين بنجاح!")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=10000)
