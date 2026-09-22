import os
import time
import requests
from fastapi import FastAPI
import uvicorn
import threading

app = FastAPI()

TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

engine_status = {
    "status": "Running",
    "last_event": "Smart Money & Whale Cluster Sniper Active..."
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Smart Money Cluster Sniper",
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

processed_tokens = set()

def evaluate_smart_money_cluster(token_address: str) -> dict:
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            data = res.json()
            pairs = data.get("pairs", [])
            if pairs:
                sol_pairs = [p for p in pairs if p.get("chainId") == "solana"]
                if not sol_pairs:
                    return {"valid": False}
                
                pair = sol_pairs[0]
                liq = pair.get("liquidity", {}).get("usd", 0)
                fdv = pair.get("fdv", 0)
                
                txns = pair.get("txns", {})
                m5 = txns.get("m5", {})
                buys = m5.get("buys", 0)
                sells = m5.get("sells", 0)
                volume = pair.get("volume", {}).get("m5", 0)
                
                symbol = pair.get("baseToken", {}).get("symbol", "SMART")
                name = pair.get("baseToken", {}).get("name", "Token")
                pair_url = pair.get("url", f"https://dexscreener.com/solana/{token_address}")
                
                # معايير رصد تجمعات المال الذكي واكتشاف الدخول المبكر:
                # 1. عمليات شراء متعددة ومكثفة (buys >= 6) تؤكد تكدس المحافظ
                # 2. انعدام المبيعات تماماً (sells == 0) لضمان الاحتفاظ التام وعدم التفريط بالتوكن
                # 3. سيولة أمان أولية مناسبة ($3,000 إلى $40,000)
                if buys >= 6 and sells == 0 and 3000 <= liq <= 40000:
                    
                    grade = "🧠💎 [تقاطع المال الذكي] تجميع مبكر للحيتان (Smart Money Cluster)"
                    
                    return {
                        "valid": True,
                        "grade": grade,
                        "liquidity": liq,
                        "fdv": fdv,
                        "buys": buys,
                        "sells": sells,
                        "volume": volume,
                        "symbol": symbol,
                        "name": name,
                        "url": pair_url
                    }
    except Exception:
        pass
    return {"valid": False}

def run_smart_money_engine():
    global processed_tokens
    while True:
        try:
            trending_url = "https://api.dexscreener.com/token-boosts/latest/v1"
            res = requests.get(trending_url, timeout=4)
            if res.status_code == 200:
                items = res.json()
                if isinstance(items, list):
                    for item in items:
                        if item.get("chainId") != "solana":
                            continue
                        
                        token_address = item.get("tokenAddress", "")
                        if token_address and token_address not in processed_tokens:
                            processed_tokens.add(token_address)
                            if len(processed_tokens) > 3000:
                                processed_tokens.clear()
                            
                            opp = evaluate_smart_money_cluster(token_address)
                            if opp.get("valid"):
                                grade = opp.get("grade")
                                liq = opp.get("liquidity", 0)
                                fdv = opp.get("fdv", 0)
                                buys = opp.get("buys", 0)
                                sells = opp.get("sells", 0)
                                vol = opp.get("volume", 0)
                                symbol = opp.get("symbol", "SMART")
                                name = opp.get("name", "Token")
                                url = opp.get("url", f"https://dexscreener.com/solana/{token_address}")
                                
                                alert_message = (
                                    f"🧠⚡ *رصد تقاطع وتجميع المال الذكي (Smart Money)*\n\n"
                                    f"📌 التقييم: *{grade}*\n"
                                    f"🪙 التوكن: {name} (`{symbol}`)\n\n"
                                    f"📊 *مقاييس التدفق والسيولة:*\n"
                                    f"💧 السيولة المؤمنة: `${liq:,.2f}`\n"
                                    f"📈 القيمة السوقية (FDV): `${fdv:,.2f}`\n"
                                    f"⚡ حجم الشراء (5 دقائق): `${vol:,.2f}`\n"
                                    f"🛒 صفقات الشراء المكثف: `{buys}` شراء 🟢 | البيع: `0` (تكتل محفظي صارم)\n\n"
                                    f"🔑 *عقد التوكن (للتحليل والدراسة):*\n`{token_address}`\n\n"
                                    f"🛡️ *روابط التحقق والتحليل الإجباري (قبل اتخاذ قرار الدخول):*\n"
                                    f"🔗 [DexScreener]({url})\n"
                                    f"🗺️ [BubbleMaps (فحص توزيع وتركز المحافظ)](https://app.bubblemaps.io/solana/{token_address})\n"
                                    f"🎯 [GMGN (تتبع سجل محافظ المتداولين الأوائل)](https://gmgn.ai/solana/token/{token_address})"
                                )
                                engine_status["last_event"] = alert_message
                                send_telegram_alert(alert_message)
        except Exception:
            pass
        
        time.sleep(1.2)

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=run_smart_money_engine, daemon=True)
    t.start()
    print("🚀 Smart Money Cluster Sniper Started Successfully!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
