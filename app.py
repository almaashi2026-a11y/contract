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
    "last_event": "Second-One High Liquidity & Strong Buy Sniper Active..."
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Second-One Strong Flow & Liquidity Sniper",
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

def check_liquidity_and_strong_buys(token_address: str, chain_id: str = "solana") -> dict:
    """فحص السيولة وقوة الشراء من الثانية الأولى بدقة"""
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    
    for _ in range(4):
        try:
            res = requests.get(url, timeout=3)
            if res.status_code == 200:
                data = res.json()
                pairs = data.get("pairs", [])
                if pairs:
                    target_pairs = [p for p in pairs if p.get("chainId") == chain_id or chain_id == "solana"]
                    pair = target_pairs[0] if target_pairs else pairs[0]
                    
                    liq = pair.get("liquidity", {}).get("usd", 0)
                    txns = pair.get("txns", {})
                    m5_txns = txns.get("m5", {})
                    buys = m5_txns.get("buys", 0)
                    sells = m5_txns.get("sells", 0)
                    volume_m5 = pair.get("volume", {}).get("m5", 0)
                    
                    symbol = pair.get("baseToken", {}).get("symbol", "PUMP")
                    name = pair.get("baseToken", {}).get("name", "New Token")
                    pair_url = pair.get("url", f"https://dexscreener.com/{chain_id}/{token_address}")
                    
                    return {
                        "valid": True,
                        "liquidity": liq,
                        "volume_m5": volume_m5,
                        "buys": buys,
                        "sells": sells,
                        "symbol": symbol,
                        "name": name,
                        "url": pair_url
                    }
        except Exception:
            pass
        time.sleep(0.6)
        
    return {"valid": False}

last_sol_sig = ""

def run_strict_sniper():
    global last_sol_sig, processed_tokens
    
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
                                
                            metrics = check_liquidity_and_strong_buys(mint, "solana")
                            if metrics.get("valid"):
                                liq = metrics.get("liquidity", 0)
                                vol = metrics.get("volume_m5", 0)
                                buys = metrics.get("buys", 0)
                                sells = metrics.get("sells", 0)
                                symbol = metrics.get("symbol", "PUMP")
                                name = metrics.get("name", "Token")
                                url = metrics.get("url", f"https://dexscreener.com/solana/{mint}")
                                
                                if buys >= sells:
                                    event_msg = (
                                        f"🔥⚡ *صيد فوري (من الثانية الأولى + سيولة وشراء قوي)*\n\n"
                                        f"🪙 الاسم: *{name}* (`{symbol}`)\n"
                                        f"💧 السيولة الأولية: *${liq:,.2f}*\n"
                                        f"📊 حجم التداول الأولي: *${vol:,.2f}*\n"
                                        f"🛒 الصفقات: *{buys} شراء* 🟢 | *{sells} بيع* 🔴\n\n"
                                        f"🔑 العقد:\n`{mint}`\n\n"
                                        f"🔗 [DexScreener الفوري]({url})\n"
                                        f"🛡️ [BubbleMaps](https://app.bubblemaps.io/solana/{mint})"
                                    )
                                    engine_status["last_event"] = event_msg
                                    print(f"🚀 تم رصد واستيفاء شروط القنص للتوكن: {symbol} | سيولة: {liq}")
                                    send_telegram_alert(event_msg)
        except Exception as e:
            print(f"❌ خطأ في رصد السيرفر: {e}")

def worker_loop():
    while True:
        run_strict_sniper()
        time.sleep(0.4)

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    print("✅ تم تفعيل رادار السيولة والشراء القوي من الثانية الأولى بنجاح!")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=10000)
