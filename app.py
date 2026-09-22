import os
import time
import requests
from fastapi import FastAPI
import uvicorn
import threading

app = FastAPI()

TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# روبن هود تشين العامة (Chain ID: 4663)
# سنستخدم الـ Public RPC المعتمد للشبكة لجلب أحدث المعاملات والتحويلات الكبيرة
ROBINHOOD_RPC = "https://rpc.robinhood.com"  # أو الـ RPC البديل المعتمد للشبكة

engine_status = {
    "status": "Running",
    "last_event": "Robinhood Chain Whale & Large Transfer Sniper Active..."
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Robinhood Chain Whale Transfer Sniper",
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
    except Exception:
        pass

processed_txs = set()

def fetch_robinhood_whale_transfers():
    global processed_txs
    while True:
        try:
            # طلب أحدث رقم كتلة (Block Number) من شبكة روبن هود
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": ["latest", True],
                "id": 1
            }
            res = requests.post(ROBINHOOD_RPC, json=payload, timeout=5)
            if res.status_code == 200:
                data = res.json()
                block = data.get("result", {})
                if block and "transactions" in block:
                    txs = block.get("transactions", [])
                    for tx in txs:
                        tx_hash = tx.get("hash", "")
                        value_hex = tx.get("value", "0x0")
                        
                        # تحويل قيمة المعاملة من النظام السداسي عشري إلى قيمة رقمية بـ ETH
                        value_eth = int(value_hex, 16) / 10**18
                        
                        # شرط رصد التحويلات الكبيرة جداً للحيتان والدخول المؤسسي (مثلاً أكبر من أو يساوي 2 ETH أو حسب رغبتك)
                        if value_eth >= 2.0 and tx_hash not in processed_txs:
                            processed_txs.add(tx_hash)
                            if len(processed_txs) > 2000:
                                processed_txs.clear()
                            
                            fr = tx.get("from", "Unknown")
                            to = tx.get("to", "Contract Creation")
                            
                            alert_msg = (
                                f"🚨🐋 *رصد تحويل ضخم وحركة حيتان على Robinhood Chain*\n\n"
                                f"💰 القيمة المحولة: `{value_eth:.2f} ETH`\n"
                                f"📤 من محفظة: `{fr[:6]}...{fr[-4:]}`\n"
                                f"📥 إلى العقد/المحفظة: `{to[:6] if to else 'N/A'}...{to[-4:] if to else ''}`\n\n"
                                f"🔑 *معرف المعاملة (TxHash):*\n`{tx_hash}`\n\n"
                                f"🛡️ *مستكشف شبكة روبهود (التحقق الفوري):*\n"
                                f"🔗 [رابط المستكشف](https://rbslot.com/tx/{tx_hash})"
                            )
                            engine_status["last_event"] = alert_msg
                            send_telegram_alert(alert_msg)
        except Exception:
            pass
        
        time.sleep(3)

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=fetch_robinhood_whale_transfers, daemon=True)
    t.start()
    print("🚀 Robinhood Chain Whale Tracker Started Successfully!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
