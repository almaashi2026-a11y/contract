# multi_chain_alpha_sniper.py
# بوت صيد عقود Alpha اللحظية - رصد الصعود والزخم الحقيقي بدون هبوط

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

SCAN_INTERVAL = 15          # فحص أسرع كل 15 ثانية للرصد اللحظي

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("alpha_sniper")

alerted_tokens = {}
recent_signals = []

SUPPORTED_CHAINS = ["solana", "ethereum", "base", "arbitrum", "bsc"]

# ==================== جلب التوكنات لحظياً عبر Boosts والترند الصاعد ====================

def get_live_momentum_tokens():
    """جلب العملات التي تم إطلاقها حديثاً ولديها زخم صاعد حقيقي فقط"""
    all_valid_pairs = []
    
    for chain in SUPPORTED_CHAINS:
        try:
            # استخدام نقطة الترند والـ Boosts لأحدث العملات النشطة
            url = f"https://api.dexscreener.com/latest/dex/search?q={chain}"
            r = requests.get(url, timeout=8)
            if r.status_code != 200:
                continue
            data = r.json()
            pairs = data.get("pairs", []) or []
            
            for p in pairs:
                if p.get("chainId") == chain:
                    liq = float((p.get("liquidity") or {}).get("usd") or 0)
                    fdv = float(p.get("fdv") or 0)
                    
                    # التحقق من الزخم السعري (لتجنب العملات التي تهبط)
                    price_change = p.get("priceChange", {})
                    h1_change = float(price_change.get("h1") or 0) if isinstance(price_change, dict) else 0.0
                    
                    # 🛡️ شروط الصيد اللحظي:
                    # 1. السيولة بين 5,000$ و 300,000$
                    # 2. القيمة السوقية أقل من 1,500,000$
                    # 3. التغير السعري في آخر ساعة موجب (في حالة صعود / زخم حي وليس هبوط)
                    if 5000 <= liq <= 300000 and 0 < fdv <= 1500000 and h1_change > 2.0:
                        all_valid_pairs.append(p)
            time.sleep(0.2)
        except Exception as e:
            log.warning(f"خطأ في رصد سلسلة {chain}: {e}")
            
    # ترتيب حسب أعلى تغير سعري في الساعة الأخيرة لاصطياد الأقوى والأسرع صعوداً
    all_valid_pairs.sort(key=lambda x: float((x.get("priceChange", {}) or {}).get("h1") or 0), reverse=True)
    return all_valid_pairs[:10]

# ==================== إرسال تنبيهات النخبة (VIP) ====================

def send_vip_alert(token):
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
        f"🚨🔥 **MOMENTUM BREAKOUT ({chain}):**\n"
        f"⚡ Strong Upward Momentum Detected!\n\n"
        f"🌐 **السلسلة:** `{chain}`\n"
        f"🪙 **التوكن:** {name} (`{symbol}`)\n"
        f"🚀 **القيمة السوقية (FDV):** `{fdv_str} 🚀🚀`\n"
        f"📈 **التغير (1h):** `+{h1_change:.1f}% 🟢`\n"
        f"💧 **السيولة:** `${liquidity:,.0f}`\n\n"
        f"🔑 **عقد التوكن (CA):**\n`{token_address}`\n\n"
        f"🛡️ **روابط الفحص والتنفيذ السريع:**\n"
        f"🔗 [DexScreener]({pair_url})\n"
        f"🎯 [GMGN (تتبع الأوائل)](https://gmgn.ai/{token.get('chainId', 'solana')}/token/{token_address})\n"
        f"🗺️ [BubbleMaps (تحليل المحافظ)](https://app.bubblemaps.io/{token.get('chainId', 'solana')}/{token_address})"
    )

    signal = {
        "chain": chain, "symbol": symbol, "fdv": fdv_str, "change": f"+{h1_change:.1f}%", "liquidity": liquidity,
        "address": token_address, "url": pair_url,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }
    recent_signals.insert(0, signal)
    if len(recent_signals) > 60:
        recent_signals.pop()

    log.info(f"إشارة صعود جديدة [{chain}]: {symbol} بنسبة +{h1_change:.1f}%")

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
            tokens = get_live_momentum_tokens()
            for token in tokens:
                token_address = token.get("baseToken", {}).get("address", "")
                if not token_address:
                    continue
                
                # عدم التكرار لمدة ساعتين
                last_alert = alerted_tokens.get(token_address)
                if last_alert and (datetime.utcnow() - last_alert) < timedelta(hours=2):
                    continue
                
                send_vip_alert(token)
                alerted_tokens[token_address] = datetime.utcnow()
                time.sleep(2)
        except Exception as e:
            log.error(f"خطأ في حلقة الرصد اللحظي: {e}")
            
        time.sleep(SCAN_INTERVAL)

# ==================== لوحة التحكم المرئية ====================

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<title>Momentum Alpha Sniper - لوحة الصيد اللحظي</title>
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
  <h1>🚀 لوحة صيد الزخم اللحظي (Breakout Alpha Calls)</h1>
  <p>تحديث تلقائي كل 15 ثانية | يتم رصد الصفقات في مسار الصعود فقط: {{ signals|length }}</p>
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
