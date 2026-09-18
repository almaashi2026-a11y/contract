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
    "last_event": "Exact Second-One Sniper Active..."
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Exact Second-One Token Sniper",
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
        requests.post(url, json=payload, timeout=2)
    except Exception as e:
        print(f"❌ خطأ تليجرام: {e}")

processed_tokens = set()

def get_token_mint_from_solana_tx(signature: str) -> str:
    """استخراج عنوان التوكن من معاملة سولانا فور حدوثها"""
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
        res = requests.post(RPC_URL, json=payload, timeout=2)
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

last_sol_sig = ""

def run_second_one_sniper():
    global last_sol_sig, processed_tokens
    
    # رصد عقد Pump.fun على سولانا من الثانية الأولى دون تأخير
    if RPC_URL:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [
                "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",
                {"limit": 2}
            ]
        }
        try:
            response = requests.post(RPC_URL, json=payload, timeout=3)
            if response.status_code == 200:
                txs = response.json().get("result", [])
                if txs:
                    latest_sig = txs[0].get("signature", "")
                    if latest_sig and latest_sig != last_sol_sig:
                        last_sol_sig = latest_sig
                        mint = get_token_mint_from_solana_tx(latest_sig)
                        if mint and mint not in processed_tokens:
                            processed_tokens.add(mint)
                            if len(processed_tokens) > 1000:
                                processed_tokens.clear()
                                
                            event_msg = (
                                f"⚡⏱️ *رصد فوري من الثانية الأولى (Exact Second One)*\n\n"
                                f"⛓️ الشبكة: *Solana (Pump.fun)*\n"
                                f"🔑 العقد:\n`{mint}`\n\n"
                                f"📝 توقيع المعاملة:\n`{latest_sig}`\n\n"
                                f"🔗 [DexScreener الفوري](https://dexscreener.com/solana/{mint})\n"
                                f"🛡️ [BubbleMaps](https://app.bubblemaps.io/solana/{mint})"
                            )
                            engine_status["last_event"] = event_msg
                            print(f"🚀 قنص من الثانية الأولى للتوكن: {mint}")
                            send_telegram_alert(event_msg)
        except Exception as e:
            print(f"❌ خطأ في الرصد الفوري: {e}")

def worker_loop():
    while True:
        run_second_one_sniper()
        time.sleep(0.5) # فحص فائق السرعة كل نصف ثانية للقط الثواني الأولى تماماً

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    print("✅ تم تفعيل رادار الثانية الأولى المطلقة بنجاح!")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=10000)
