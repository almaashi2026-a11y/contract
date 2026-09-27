# jev_alpha_trader.py
# بوت صيد Alpha متعدد السلاسل مع معمارية اتخاذ القرار السريع (Jev-Trader Architecture)

import os
import time
import logging
import threading
import requests
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template_string

# ==================== الإعدادات ====================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

SCAN_INTERVAL = 15          # فحص ذكي دوري كل 15 ثانية

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("jev_sniper")

alerted_tokens = {}
recent_signals = []

SUPPORTED_CHAINS = ["solana", "ethereum", "base", "arbitrum", "bsc"]

# ==================== طبقة اتخاذ القرار السريع (Jev Decision Gate) ====================

def jev_decision_engine(token):
    """
    طبقة قرار سريعة وثنائية (نعم/لا) تحاكي هندسة Jev:
    تتحقق من أن العملة تستحق التصعيد والإرسال بناءً على شروط السيولة والزخم الحقيقي.
    """
    try:
        liq = float((token.get("liquidity") or {}).get("usd") or 0)
        fdv = float(token.get("fdv") or 0)
        
        price_change = token.get("priceChange", {})
        h1_change = float(price_change.get("h1") or 0) if isinstance(price_change, dict) else 0.0
        
        # 1. شروط الأمان المبدئي والسيولة
        if not (3000 <= liq <= 400000):
            return False, "سيولة غير مناسبة"
            
        # 2. القيمة السوقية المقبولة لفرص النمو
        if not (0 < fdv <= 2000000):
            return False, "قيمة سوقية تتجاوز الحد المسموح"
            
        # 3. التأكد من أن الزخم صاعد وليس هابطاً
        if h1_change <= 1.0:
            return False, "لا يوجد زخم صاعد كافٍ (أو في مسار هبوط)"
            
        return True, "تم اجتياز القرار بنجاح"
    except Exception as e:
        return False, f"خطأ في تقييم القرار: {str(e)}"

# ==================== جلب ورصد التوكنات ====================

def fetch_and_evaluate_tokens():
    """جلب الأزواج وتطبيق قرار Jev الفوري عليها"""
    approved_tokens = []
    
    for chain in SUPPORTED_CHAINS:
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q={chain}"
            r = requests.get(url, timeout=8)
            if r.status_code != 200:
                continue
            data = r.json()
            pairs = data.get("pairs", []) or []
            
            for p in pairs:
                if p.get("chainId") == chain:
                    # تمرير التوكن عبر طبقة القرار السريع (Jev Decision Gate)
                    passed, reason = jev_decision_engine(p)
                    if passed:
                        approved_tokens.append(p)
            time.sleep(0.2)
        except Exception as e:
            log.warning(f"خطأ في فحص سلسلة {chain}: {e}")
            
    # ترتيب حسب الأقوى صعوداً
    approved_tokens.sort(key=lambda x: float((x.get("priceChange", {}) or {}).get("h1") or 0), reverse=True)
    return approved_tokens[:10]

# ==================== إرسال التنبيهات وإدارة الصفقات ====================

def send_jev_alert(token):
    chain = token.get("chainId", "unknown").upper()
    symbol = token.get("baseToken", {}).get("symbol", "UNKNOWN")
    name = token.get("baseToken", {}).get("name", "Token")
    token_address = token.get("baseToken", {}).get("address", "")
    fdv = float(token.get("fdv") or 0)
    liquidity = float((token.get("liquidity") or {}).get("usd") or 0)
    
    price_change = token.get("priceChange", {})
    h1_change = float(price_change.get("h1") or 0) if isinstance(price_change, dict) else 0.0
    
    pair_url = token.get("url", f"https://dexscreener.com/{token.get('chainId', 'solana')}/{token_address}")
    
    if fdv >= 1000000:
        fdv_str = f"{fdv / 1000000:.1f}M"
    else:
        fdv_str = f"{fdv / 1000:.1f}K"

    message = (
        f"⚡🧠 **JEV DECISION: ALPHA SIGNAL ({chain})**\n"
        f"🟢 Decision Gate: PASSED (Approved)\n\n"
        f"🌐 **السلسلة:** `{chain}`\n"
        f"🪙 **التوكن:** {name} (`{symbol}`)\n"
        f"🚀 **القيمة السوقية (FDV):** `{fdv_str} 🚀`\n"
        f"📈 **التغير (1h):** `+{h1_change:.1f}%`\n"
        f"💧 **السيولة:** `${liquidity:,.0f}`\n\n"
        f"🔑 **عقد التوكن (CA):**\n`{token_address}`\n\n"
        f"🛡️ **روابط الفحص والتتبع:**\n"
        f"🔗 [DexScreener]({pair_url})\n"
        f"🎯 [GMGN (صائدي الأوائل)](https://gmgn.ai/{token.get('chainId', 'solana')}/token/{token_address})\n"
        f"🗺️ [BubbleMaps (المحافظ)](https://app.bubblemaps.io/{token.get('chainId', 'solana')}/{token_address})"
    )

    signal = {
        "chain": chain, "symbol": symbol, "fdv": fdv_str, "change": f"+{h1_change:.1f}%", "liquidity": liquidity,
        "address": token_address, "url": pair_url,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }
    recent_signals.insert(0, signal)
    if len(recent_signals) > 60:
        recent_signals.pop()

    log.info(f"إشارة معتمدة من Jev [{chain}]: {symbol} بنسبة +{h1_change:.1f}%")

    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }, timeout=10)
        except Exception as e:
            log.warning(f"فشل إرسال تنبيه Telegram: {e}")

def run_sniper_loop():
    while True:
        try:
            tokens = fetch_and_evaluate_tokens()
            for token in tokens:
                token_address = token.get("baseToken", {}).get("address", "")
                if not token_address:
                    continue
                
                # منع التكرار لمدة 3 ساعات
                last_alert = alerted_tokens.get(token_address)
                if last_alert and (datetime.utcnow() - last_alert) < timedelta(hours=3):
                    continue
                
                send_jev_alert(token)
                alerted_tokens[token_address] = datetime.utcnow()
                time.sleep(2)
        except Exception as e:
            log.error(f"خطأ في حلقة القرار والتنفيذ: {e}")
            
        time.sleep(SCAN_INTERVAL)

# ==================== لوحة التحكم المرئية ====================

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<title>Jev Alpha Trader - لوحة اتخاذ القرار الذكي</title>
<meta http-equiv="refresh" content="15">
<style>
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f1115; color: #eee; padding: 20px; }
  h1 { color: #facc15; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; }
  th, td { padding: 12px; text-align: right; border-bottom: 1px solid #2a2d34; }
  th { color: #888; font-weight: normal; }
  tr:hover { background: #1a1d24; }
  .ca { color: #38bdf8; font-family: monospace; font-size: 14px; }
  .badge { background: #1e293b; color: #38bdf8; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
  .green { color: #4ade80; font-weight: bold; }
  a { color: #4ade80; text-decoration: none; }
  a:hover { text-decoration: underline; }
</style>
</head>
<body>
  <h1>⚡🧠 Jev Decision-Driven Alpha Trader</h1>
  <p>يعمل بنظام تقييم القرار السريع (Jev Architecture) | عدد الصفقات المعتمدة: {{ signals|length }}</p>
  <table>
    <tr><th>الوقت (UTC)</th><th>السلسلة</th><th>العملة</th><th>القيمة السوقية</th><th>التغير (1h)</th><th>السيولة</th><th>عقد التوكن (CA)</th><th>الرابط</th></tr>
    {% for s in signals %}
    <tr>
      <td>{{ s.time }}</td>
      <td><span class="badge">{{ s.chain }}</span></td>
      <td><b>{{ s.symbol }}</b></td>
      <td style="color: #facc15;">{{ s.fdv }} 🚀</td>
      <td class="green">{{ s.change }}</td>
      <td>${{ "%.0f"|format(s.liquidity) }}</td>
      <td class="ca">{{ s.address }}</td>
      <td><a href="{{ s.url }}" target="_blank">فحص ↗</a></td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
"""

@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML, signals=recent_signals)

@app.route("/api/signals")
def api_signals():
    return jsonify(recent_signals)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})

# ==================== التشغيل الرئيسي ====================

if __name__ == "__main__":
    t = threading.Thread(target=run_sniper_loop, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
