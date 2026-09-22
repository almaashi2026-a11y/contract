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
    "last_event": "Ultra Confirmed Smart Money Sniper Active..."
}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "engine": "Ultra Confirmed Smart Money Sniper",
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

def evaluate_ultra_confirmation(token_address: str) -> dict:
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
                
                # نسبة السيولة إلى القيمة السوقية لصحة الانطلاقة
                ratio = (liq / fdv) if fdv > 0 else 0
                
                symbol = pair.get("baseToken", {}).get("symbol", "ULTRA")
                name = pair.get("baseToken", {}).get("name", "Token")
                pair_url = pair.get("url", f"https://dexscreener.com/solana/{token_address}")
                
                # شروط التأكيد القوي جداً للصعود وشيك الانفجار:
                # 1. عمليات شراء مكثفة (أكثر من أو يساوي 5) لتأكيد بدء الزخم
                # 2. صفر مبيعات نهائياً لتأكيد سيطرة الحيتان والاحتفاظ التام
                # 3. سيولة مدروسة بين $3k و $35k لضمان سرعة الصعود
                if buys >= 5 and sells == 0 and 3000 <= liq <= 35000:
                    
                    # تقييم عالي التأكيد
                    grade = "🚀🔥 [تأكيد صارم] جاهز للانفجار الصعودي (Ultra Grade A+)"
                    
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

def run_ultra_confirmed_engine():
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
                            
                            opp = evaluate_ultra_confirmation(token_address)
                            if opp.get("valid"):
                                grade = opp.get("grade")
                                liq = opp.get("liquidity", 0)
                                fdv = opp.get("fdv", 0)
                                buys = opp.get("buys", 0)
                                sells = opp.get("sells", 0)
                                ratio = opp.get("ratio", 0)
                                symbol = opp.get("symbol", "ULTRA")
                                name = opp.get("name", "Token")
                                url = opp.get("url", f"https://dexscreener.com/solana/{token_address}")
                                
                                # صياغة تنبيه النخبة المؤكد بدقة متناهية
                                confirmed_msg = (
                                    f"💎⚡ *رصد اشارة انطلاقة الصعود المؤكدة*\n\n"
                                    f"📌 التقييم: *{grade}*\n"
                                    f"🪙 التوكن: {name} (`{symbol}`)\n\n"
                                    f"📊 *بيانات الزخم والتأكيد الفعلي:*\n"
                                    f"💧 السيولة الحالية: `${liq:,.2f}`\n"
                                    f"📈 القيمة السوقية (FDV): `${fdv:,.2f}`\n"
                                    f"⚖️ نسبة السيولة: `{ratio:.1f}%`\n"
                                    f"🛒 عمليات الشراء المكثف: `{buys}` شراء 🟢 | البيع: `0` (تجميع حيتان صارم)\n\n"
                                    f"🔑 *عقد التوكن (للتحرك الفوري):*\n`{token_address}`\n\n"
                                    f"🛡️ *روابط التحقق والاعتماد الإجباري قبل الدخول:*\n"
                                    f"🔗 [DexScreener]({url})\n"
                                    f"🗺️ [BubbleMaps (فحص تركز المحافظ)](https://app.bubblemaps.io/solana/{token_address})\n"
                                    f"⚡ [GMGN (تتبع حيتان الشراء)](https://gmgn.ai/solana/token/{token_address})"
                                )
                                engine_status["last_event"] = confirmed_msg
                                send_telegram_alert(confirmed_msg)
        except Exception:
            pass
        
        time.sleep(1.2)

@app.on_event("startup")
def startup_event():
    t = threading.Thread(target=run_ultra_confirmed_engine, daemon=True)
    t.start()
    print("🚀 Ultra Confirmed Smart Money Engine Started Successfully!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
