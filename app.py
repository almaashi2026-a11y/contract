import os
import asyncio
import json
import websockets
from fastapi import FastAPI
import uvicorn

app = FastAPI()

# قراءة متغيرات البيئة بدقة
RPC_URL = os.environ.get("SOLANA_RPC_URL", "")
WALLET_PRIVATE_KEY = os.environ.get("WALLET_PRIVATE_KEY", "")

# تحويل رابط الـ RPC إلى WSS تلقائياً لتجنب أخطاء الاتصال
if RPC_URL.startswith("https://"):
    WSS_URL = RPC_URL.replace("https://", "wss://", 1)
elif RPC_URL.startswith("http://"):
    WSS_URL = RPC_URL.replace("http://", "ws://", 1)
else:
    WSS_URL = RPC_URL

engine_status = {
    "status": "Running",
    "last_event": "Waiting for connection..."
}

@app.get("/")
def health_check():
    """مسار لفحص حالة السيرفر والحفاظ عليه نشطاً على Render"""
    return {
        "status": "online",
        "engine": "Solana Pump.fun Sniper Radar",
        "details": engine_status
    }

async def sniper_mempool_worker():
    """خلفية للاتصال بـ WebSocket ومراقبة العقود اللحظية"""
    while True:
        try:
            print(f"🔄 جاري الاتصال بشبكة البلوكتشين عبر الـ WebSocket...")
            async with websockets.connect(WSS_URL) as websocket:
                # اشتراك في عقود إنشاء التوكنات الجديدة (Logs Subscription)
                subscription_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "logsSubscribe",
                    "params": [
                        {"mentions": ["6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"]}, # عقد برنامج Pump.fun
                        {"commitment": "processed"}
                    ]
                }
                await websocket.send(json.dumps(subscription_payload))
                print("✅ تم الاتصال بنجاح وبدأت مراقبة الـ Mempool!")
                
                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    
                    # التحقق من وجود بيانات عقد جديد
                    if "params" in data:
                        result = data["params"].get("result", {})
                        value = result.get("value", {})
                        signature = value.get("signature", "")
                        logs = value.get("logs", [])
                        
                        # فحص ما إذا كانت اللوقز تخص إنشاء توكن جديد
                        is_created = any("Create" in log or "initialize" in log for log in logs)
                        if is_created and signature:
                            event_msg = f"🚨 تم رصد عقد جديد على Pump.fun! التوقيع: {signature}"
                            engine_status["last_event"] = event_msg
                            print(event_msg)
                            
        except Exception as e:
            err_msg = f"⚠️ خطأ في المحرك: {e}"
            engine_status["last_event"] = err_msg
            print(err_msg)
            await asyncio.sleep(5)  # انتظار قبل إعادة المحاولة

@app.on_event("startup")
async def startup_event():
    """تشغيل رادار الميمبول في الخلفية فور إقلاع السيرفر"""
    asyncio.create_task(sniper_mempool_worker())

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=10000)
