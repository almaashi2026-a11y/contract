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
    "last_event": "Elite Smart Money Summary Engine Active..."
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Elite Smart Money Summary Engine",
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

def evaluate_smart_money_opportunity(token_address: str) -> dict:
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        res = requests.get(url, timeout=2)
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
                
                # حساب نسبة السيولة إلى القيمة السوقية (مؤشر على قوة التأسيس)
                ratio = (liq / fdv) if fdv > 0 else 0
                
                symbol = pair.get("baseToken", {}).get("symbol", "ELITE")
                name = pair.get("baseToken", {}).get("name", "Token")
                pair_url = pair.get("url", f"https://dexscreener.com/solana/{token_address}")
                
                # الفلتر الأقوى: شراء قوي، صفر بيع، سيولة أولية ممتازة ونسبة صحية
                if buys >= 3 and sells == 0 and 2000 <= liq <= 30000:
                    
                    # تقييم قوة الفرصة (الخلاصة الذكية)
                    grade = "🔥 فرصة ذهبية (Grade A+)" if liq >= 5000 and buys >= 5 else "💎 فرصة واعدة (Grade A)"
                    
                    return {
                        "valid": True,
                        "grade": grade,
                        "liquidity": liq,
                        "fdv": fdv,
                        "buys": buys,
                        "sells": sells,
                        "ratio": ratio * 100,
                        "symbol": symbol,
                        "name": name,
                        "url": pair_url
                    }
    except Exception:
        pass
    return {"valid": False}

def run_elite_summary_engine():
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
                            
                            opp = evaluate_smart_money_opportunity(token_address)
                            if opp.get("valid"):
                                grade = opp.get("grade")
                                liq = opp.get("liquidity", 0)
                                fdv = opp.get("fdv", 0)
                                buys = opp.get("buys", 0)
                                sells = opp.get("sells", 0)
                                ratio = opp.get("ratio", 0)
                                symbol = opp.get("symbol", "ELITE")
                                name = opp.get("name", "Token")
                                url = opp.get("url", f"https://dexscreener.com/solana/{token_address}")
                                
                                # صياغة الخلاصة التنفيذية القوية والجاهزة للقرار
                                summary_msg = (
                                    f"🧠⚡ *الخلاصة التنفيذية لمحافظ الأموال الذكية*\n\n"
                                    f"📌 التقييم: *{grade}*\n"
                                    f"🪙 التوكن: {name} (`{symbol}`)\n\n"
                                    f"📊 *المؤشرات المالية والزخم:*\n"
                                    f"💧 السيولة الأولية: `${liq:,.2f}`\n"
                                    f"📈 القيمة السوقية: `${fdv:,.2f}`\n"
                                    f"⚖️ نسبة السيولة للـ FDV: `{ratio:.1f}%`\n"
                                    f"🛒 عمليات الشراء الصافي: `{buys}` شراء 🟢 | البيع: `0` (احتفاظ وتجميع تام)\n\n"
                                    f"🔑 *عقد التوكن:*\n`{token_address}`\n\n"
                                    f"🛡️ *روابط التحقق الإجباري قبل الدخول:*\n"
                                    f"🔗 [DexScreener]({url})\n"
                                    f"🗺️ [BubbleMaps (فحص تركز الحيتان)](https://app.bubblemaps.io/solana/{token_address})\n"
                                    f"⚡ [GMGN (تتبع محافظ الصيد)](https://gmgn.ai/solana/token/{token_address})"
                                )
                                engine_status["last_event"] = summary_msg
                                send_telegram_alert(summary_msg)
        except Exception:
            pass
        
        time.sleep(1.5)

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=run_elite_summary_engine, daemon=True)
    t.start()
    print("🚀 Elite Summary Engine Started Successfully!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
