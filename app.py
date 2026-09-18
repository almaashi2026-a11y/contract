import os
import time
import requests
from FastAPI import FastAPI
import uvicorn
import threading

app = FastAPI()

RPC_URL = os.environ.get("SOLANA_RPC_URL", "")
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

engine_status = {
    "status": "Running",
    "last_event": "Waiting for high-momentum tokens..."
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Solana Momentum & Volume Pump Radar",
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
    """استخراج عنوان التوكن الفعلي من تفاصيل المعاملة"""
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

def check_momentum_and_liquidity(mint_address: str) -> dict:
    """فحص دقيق للسيولة والزخم (عدد الصفقات وحجم الشراء) لاستبعاد العملات الميتة"""
    url = f"https://api.dexscreener.com/latest/dex/tokens/{mint_address}"
    
    # نعطي محاولات قصيرة بانتظار تحديث المؤشرات من الدكس سكرينير
    for _ in range(3):
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                pairs = data.get("pairs", [])
                if pairs:
                    sol_pairs = [p for p in pairs if p.get("chainId"] == "solana"]
                    if sol_pairs:
                        pair = sol_pairs[0]
                        liq = pair.get("liquidity", {}).get("usd", 0)
                        
                        # الحصول على معلومات حجم التداول والصفقات (شراء/بيع) خلال آخر ساعة أو 5 دقائق
                        txns = pair.get("txns", {})
                        h1_txns = txns.get("h1", {})
                        buys = h1_txns.get("buys", 0)
                        sells = h1_txns.get("sells", 0)
                        
                        h1_volume = pair.get("volume", {}).get("h1", 0)
                        
                        # شرط الزخم: يجب أن تحتوي على سيولة أكبر من الصفر ولديها عمليات شراء فعلية (حركة نشطة)
                        if liq > 500 and buys > 0:
                            return {
                                "is_active": True,
                                "liquidity": liq,
                                "volume": h1_volume,
                                "buys": buys,
                                "sells": sells,
                                "symbol": pair.get("baseToken", {}).get("symbol", "PUMP"),
                                "name": pair.get("baseToken", {}).get("name", "Token"),
                                "url": pair.get("url", f"https://dexscreener.com/solana/{mint_address}")
                            }
        except Exception:
            pass
        time.sleep(1.5)
        
    return {"is_active": False}

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
            "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
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
                    
                    # فحص الزخم والسيولة الشرائية
                    metrics = check_momentum_and_liquidity(mint_address)
                    
                    if metrics.get("is_active"):
                        liq = metrics.get("liquidity", 0)
                        vol = metrics.get("volume", 0)
                        buys = metrics.get("buys", 0)
                        sells = metrics.get("sells", 0)
                        symbol = metrics.get("symbol")
                        name = metrics.get("name")
                        pair_url = metrics.get("url")
                        
                        event_msg = (
                            f"🚀 *رصد عقد بذخم شرائي قوي (Pump.fun)*\n\n"
                            f"🪙 الاسم: *{name}* (`{symbol}`)\n"
                            f"💧 السيولة: *${liq:,.2f}*\n"
                            f"📈 عمليات الشراء (ساعة): *{buys} شراء* مقابل *{sells} بيع*\n"
                            f"📊 حجم التداول: *${vol:,.2f}*\n\n"
                            f"🔑 العقد:\n`{mint_address}`\n\n"
                            f"🔗 [DexScreener]({pair_url})\n"
                            f"🛡️ [BubbleMaps](https://app.bubblemaps.io/solana/{mint_address})"
                        )
                        engine_status["last_event"] = event_msg
                        print(f"✅ تم رصد توكن ذو زخم نشط: {symbol} | سيولة: {liq}")
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
    print("✅ تم تفعيل رادار الزخم والسيولة بنجاح!")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=10000)
