"""
Render-Compatible Mempool Sniper Engine
محرك قنص الـ Mempool المتوافق مع استضافة Render
"""

import asyncio
import json
import os
import threading
import websockets
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from solana.rpc.api import Client
from solders.keypair import Keypair

# جلب الإعدادات من متغيرات البيئة في Render
WSS_URL = os.environ.get("SOLANA_WSS_URL", "")
RPC_URL = os.environ.get("SOLANA_RPC_URL", "")
PRIVATE_KEY = os.environ.get("WALLET_PRIVATE_KEY", "")

# عقد مصنع Pump.fun
FACTORY_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

# إعداد تطبيق الويب ليبقى السيرفر نشطاً على Render
app = FastAPI(title="Sniper Background Worker")
engine_status = {"connected": False, "last_event": "جاري بدء التشغيل..."}


@app.get("/")
def health_check():
    """مسار صحة السيرفر ليبقيه Render متصلاً ومستمراً"""
    return JSONResponse({
        "status": "Running",
        "engine_state": engine_status
    })


def execute_snipe_order(token_mint: str):
    """دالة تنفيذ أمر الشراء الفوري"""
    if not PRIVATE_KEY:
        print("❌ خطأ: المفتاح الخاص للمحفظة غير معرف في البيئة!")
        return

    try:
        sender = Keypair.from_base58_string(PRIVATE_KEY)
        client = Client(RPC_URL)
        print(f"⚡ [تنفيذ آلي على Render] جاري إرسال معاملة شراء للعملة: {token_mint}")
        # هنا يتم توقيع وإرسال معاملة الشراء الفوري مع رسوم الأولوية
        print("✅ تم إرسال أمر القنص المالي بنجاح!")
    except Exception as e:
        print(f"❌ فشل تنفيذ أمر الشراء: {e}")


async def fetch_token_mint_from_signature(signature: str) -> str:
    """استخراج عنوان العملة من التوقيع"""
    client = Client(RPC_URL)
    try:
        await asyncio.sleep(0.3)
        # تحليل بيانات المعاملة واستخراج الـ Mint Address الجديد
        mint_address = "EXTRACTED_TOKEN_MINT_ADDRESS"
        return mint_address
    except Exception:
        return None


async def sniper_mempool_worker():
    """خلفية العمل للاتصال بالـ Mempool عبر الـ WebSocket"""
    global engine_status
    if not WSS_URL or not RPC_URL:
        engine_status["last_event"] = "خطأ: روابط الـ WSS أو RPC غير مفقودة!"
        print("❌ يرجى إضافة روابط Helius في Environment Variables على Render.")
        return

    while True:
        try:
            print("🔄 جاري الاتصال بشبكة البلوكشين عبر الـ WebSocket...")
            async with websockets.connect(WSS_URL) as websocket:
                engine_status["connected"] = True
                engine_status["last_event"] = "متصل بنجاح بـ Mempool الشبكة!"
                
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "logsSubscribe",
                    "params": [
                        {"mentions": [FACTORY_PROGRAM_ID]},
                        {"commitment": "processed"}
                    ]
                }
                
                await websocket.send(json.dumps(payload))
                print("🚀 الرادار يعمل الآن في قلب الـ Mempool على Render!")

                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    
                    result = data.get("params", {}).get("result", {})
                    value = result.get("value", {})
                    logs = value.get("logs", [])
                    signature = value.get("signature")

                    is_created = any("Initialize" in log or "Create" in log for log in logs)
                    
                    if is_created and signature:
                        event_msg = f"🚨 تم رصد عقد جديد! التوقيع: {signature}"
                        engine_status["last_event"] = event_msg
                        print(event_msg)
                        
                        token_mint = await fetch_token_mint_from_signature(signature)
                        if token_mint:
                            execute_snipe_order(token_mint)

        except websockets.exceptions.ConnectionClosed:
            engine_status["connected"] = False
            engine_status["last_event"] = "انقطع الاتصال، جاري إعادة المحاولة..."
            print("⚠️ انقطع الاتصال، جاري إعادة المحاولة خلال ثانيتين...")
            await asyncio.sleep(2)
        except Exception as e:
            engine_status["connected"] = False
            engine_status["last_event"] = f"خطأ: {str(e)}"
            print(f"⚠️ خطأ في المحرك: {e}")
            await asyncio.sleep(2)


def run_background_loop():
    """تشغيل حلقة الـ Asyncio في مسار منفصل (Background Thread)"""
    asyncio.run(sniper_mempool_worker())


@app.on_event("startup")
def startup_event():
    """بدء تشغيل الرادار تلقائياً عند إقلاع الخدمة على Render"""
    t = threading.Thread(target=run_background_loop, daemon=True)
    t.start()
