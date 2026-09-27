# genesis_sniper_v5_pro.py
# بوت صيد الألفا المتقدم - إدارة آلية وسرعة تدوير الصفقة بدون عاطفة

import os
import time
import logging
import threading
import requests
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template_string

# ==================== الإعدادات الأساسية ====================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

SCAN_INTERVAL = 2           # فحص فائق السرعة كل ثانيتين

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("genesis_pro_v5")

alerted_tokens = {}
active_positions = []       # تتبع الصفقات الحالية لفرض الانضباط والحيادية

# ==================== جلب وتصفية الفرص الحية ====================

def get_pro_tokens():
    """جلب أحدث الأزواج اللحظية مع فلترة السيولة والزخم المبكر"""
    approved_tokens = []
    
    try:
        url = "https://api.dexscreener.com/latest/dex/search?q=solana"
        r = requests.get(url, timeout=4)
        
        if r.status_code == 200:
            data = r.json()
            pairs = data.get("pairs", []) or []
            
            for p in pairs:
                liq = float((p.get("liquidity") or {}).get("usd") or 0)
                fdv = float(p.get("fdv") or 0)
                
                base_token = p.get("baseToken", {})
                symbol = base_token.get("symbol")
                address = base_token.get("address")
                
                # شروط الصيد الحياد والدوران السريع
                if symbol and address and 300 <= liq <= 400000 and 0 < fdv <= 900000:
                    approved_tokens.append(p)
                    
    except Exception as e:
        log.error(f"خطأ في جلب الفرص: {e}")
        
    return approved_tokens[:15]

# ==================== إرسال التنبيهات مع استراتيجية الانضباط ====================

def send_pro_alert(token):
    chain = token.get("chainId", "solana").lower()
    chain_upper = chain.upper()
    
    base_token = token.get("baseToken", {})
    symbol = base_token.get("symbol", "UNKNOWN")
    name = base_token.get("name", "Token")
    token_address = base_token.get("address", "")
    
    fdv = float(token.get("fdv") or 0)
    liquidity = float((token.get("liquidity") or {}).get("usd") or 0)
    
    defined_url = f"https://www.defined.fi/{chain}/{token_address}"
    okx_trade_url = f"https://www.okx.com/web3/dex-market?chainId={chain}&tokenAddress={token_address}"
    
    if fdv >= 1000000:
        fdv_str = f"{fdv / 1000000:.1f}M"
    else:
        fdv_str = f"{fdv / 1000:.1f}K"

    message = (
        f"🤖⚡ **NEUTRAL BOT SIGNAL ({chain_upper})**\n"
        f"🎯 *فلوس الميم في الدوران، مش في الإيمان.*\n\n"
        f"🌐 **السلسلة:** `{chain_upper}`\n"
        f"🪙 **التوكن:** {name} (`{symbol}`)\n"
        f"🚀 **FDV:** `{fdv_str}`\n"
        f"💧 **السيولة:** `${liquidity:,.0f}`\n\n"
        f"🔑 **العقد (CA):**\n`{token_address}`\n\n"
        f"🛡️ **التنفيذ والتحليل السريع:**\n"
        f"📊 [Defined.fi (تحليل)]({defined_url})\n"
        f"⚡ [شراء مباشر OKX DEX]({okx_trade_url})\n"
        f"⚠️ *قاعدة البوت: لا تعاطف، اخرج عند الهدف أو الخسارة فوراً.*"
    )

    position = {
        "chain": chain_upper, "symbol": symbol, "fdv": fdv_str, "liquidity": liquidity,
        "address": token_address, "defined_url": defined_url, "okx_url": okx_trade_url,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "نشط (قيد التدوير)"
    }
    
    if not any(p["address"] == token_address for p in active_positions):
        active_positions.insert(0, position)
        if len(active_positions) > 50:
            active_positions.pop()

    log.info(f"إشارة ذكية [{chain_upper}]: {symbol}")

    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }, timeout=6)
        except Exception as e:
            log.warning(f"فشل إرسال التيليجرام: {e}")

def run_sniper_loop():
    while True:
        try:
            tokens = get_pro_tokens()
            for token in tokens:
                token_address = token.get("baseToken", {}).get("address", "")
                if not token_address:
                    continue
                
                last_alert = alerted_tokens.get(token_address)
                # تقليص فترة الحظر لتשجيع إعادة الدخول إذا تجدد الزخم (بدون عاطفة)
                if last_alert and (datetime.utcnow() - last_alert) < timedelta(minutes=30):
                    continue
                
                send_pro_alert(token)
                alerted_tokens[token_address] = datetime.utcnow()
        except Exception as e:
            log.error(f"خطأ في حلقة الرصد: {e}")
            
        time.sleep(SCAN_INTERVAL)

# ==================== لوحة التحكم الاحترافية ====================

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<title>Genesis Pro - Neutral Sniper</title>
<meta http-equiv="refresh" content="3">
<style>
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f1115; color: #eee; padding: 20px; }
  h1 { color: #facc15; font-size: 24px; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }
  th, td { padding: 10px; text-align: right; border-bottom: 1px solid #2a2d34; }
  th { color: #888; font-weight: normal; }
  tr:hover { background: #1a1d24; }
  .ca { color: #38bdf8; font-family: monospace; }
  .badge { background: #1e293b; color: #38bdf8; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
  .btn-okx { background: #2563eb; color: #fff; padding: 4px 8px; border-radius: 4px; text-decoration: none; }
  .btn-def { background: #059669; color: #fff; padding: 4px 8px; border-radius: 4px; text-decoration: none; }
  .status { color: #4ade80; font-weight: bold; }
</style>
</head>
<body>
  <h1>🤖⚡ Genesis Pro - Neutral Sniper</h1>
  <p>فلوس الميم في الدوران، مش في الإيمان | إجمالي الفرص المرصودة: {{ positions|length }}</p>
  <table>
    <tr><th>الوقت (UTC)</th><th>السلسلة</th><th>العملة</th><th>FDV</th><th>السيولة</th><th>الحالة</th><th>العقد (CA)</th><th>Defined</th><th>OKX DEX</th></tr>
    {% for p in positions %}
    <tr>
      <td>{{ p.time }}</td>
      <td><span class="badge">{{ p.chain }}</span></td>
      <td><b>{{ p.symbol }}</b></td>
      <td style="color: #facc15;">{{ p.fdv }} 🚀</td>
      <td>${{ "%.0f"|format(p.liquidity) }}</td>
      <td class="status">{{ p.status }}</td>
      <td class="ca">{{ p.address }}</td>
      <td><a href="{{ p.defined_url }}" target="_blank" class="btn-def">Defined ↗</a></td>
      <td><a href="{{ p.okx_url }}" target="_blank" class="btn-okx">شراء OKX ⚡</a></td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
"""

@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML, positions=active_positions)

@app.route("/api/signals")
def api_signals():
    return jsonify(active_positions)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})

if __name__ == "__main__":
    t = threading.Thread(target=run_sniper_loop, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
