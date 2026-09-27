# hyper_fast_sniper.py
# بوت صيد الألفا الفائق السرعة - سرعة استجابة لحظية

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

SCAN_INTERVAL = 2           # فحص فائق السرعة كل ثانيتين فقط!

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("hyper_sniper")

alerted_tokens = {}
recent_signals = []

# ==================== الجلب فائق السرعة ====================

def get_hyper_fast_tokens():
    """جلب أحدث الأزواج دفعة واحدة وبأعلى سرعة ممكنة بدون تأخير الطلبات المتعددة"""
    approved_tokens = []
    
    try:
        # استخدام نقطة النهاية المباشرة للأزواج الجديدة كلياً
        url = "https://api.dexscreener.com/latest/dex/search?q=solana"  # أو شبكات متعددة
        r = requests.get(url, timeout=4)
        
        if r.status_code == 200:
            data = r.json()
            pairs = data.get("pairs", []) or []
            
            for p in pairs:
                liq = float((p.get("liquidity") or {}).get("usd") or 0)
                fdv = float(p.get("fdv") or 0)
                pair_created = p.get("pairCreatedAt", 0)
                
                # فحص ما إذا كان التوكن تم إنشاؤه حديثاً جداً (في آخر ساعة مثلاً) مع سيولة مقبولة
                now_ts = time.time() * 1000
                is_fresh = (pair_created == 0) or ((now_ts - pair_created) < 3600000)
                
                if is_fresh and 500 <= liq <= 400000 and 0 < fdv <= 1000000:
                    approved_tokens.append(p)
                    
    except Exception as e:
        log.error(f"خطأ في السرعة الفائقة للجلب: {e}")
        
    return approved_tokens[:10]

# ==================== الإرسال الفوري ====================

def send_genesis_alert(token):
    chain = token.get("chainId", "solana").lower()
    chain_upper = chain.upper()
    symbol = token.get("baseToken", {}).get("symbol", "UNKNOWN")
    name = token.get("baseToken", {}).get("name", "Token")
    token_address = token.get("baseToken", {}).get("address", "")
    fdv = float(token.get("fdv") or 0)
    liquidity = float((token.get("liquidity") or {}).get("usd") or 0)
    
    defined_url = f"https://www.defined.fi/{chain}/{token_address}"
    okx_trade_url = f"https://www.okx.com/web3/dex-market?chainId={chain}&tokenAddress={token_address}"
    
    if fdv >= 1000000:
        fdv_str = f"{fdv / 1000000:.1f}M"
    else:
        fdv_str = f"{fdv / 1000:.1f}K"

    message = (
        f"⚡🚀 **HYPER FAST GENESIS ({chain_upper})**\n"
        f"🔥 Instant Speed Catch\n\n"
        f"🌐 **السلسلة:** `{chain_upper}`\n"
        f"🪙 **التوكن:** {name} (`{symbol}`)\n"
        f"🚀 **FDV:** `{fdv_str} 🚀`\n"
        f"💧 **السيولة:** `${liquidity:,.0f}`\n\n"
        f"🔑 **العقد (CA):**\n`{token_address}`\n\n"
        f"🛡️ **التنفيذ والتحليل:**\n"
        f"📊 [Defined.fi]({defined_url})\n"
        f"⚡ [شراء مباشر OKX DEX]({okx_trade_url})\n"
        f"🎯 [GMGN](https://gmgn.ai/{chain}/token/{token_address})"
    )

    signal = {
        "chain": chain_upper, "symbol": symbol, "fdv": fdv_str, "liquidity": liquidity,
        "address": token_address, "defined_url": defined_url, "okx_url": okx_trade_url,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }
    recent_signals.insert(0, signal)
    if len(recent_signals) > 60:
        recent_signals.pop()

    log.info(f"صيد فائق السرعة [{chain_upper}]: {symbol}")

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
            tokens = get_hyper_fast_tokens()
            for token in tokens:
                token_address = token.get("baseToken", {}).get("address", "")
                if not token_address:
                    continue
                
                last_alert = alerted_tokens.get(token_address)
                if last_alert and (datetime.utcnow() - last_alert) < timedelta(hours=2):
                    continue
                
                send_genesis_alert(token)
                alerted_tokens[token_address] = datetime.utcnow()
        except Exception as e:
            log.error(f"خطأ في الحلقة السريعة: {e}")
            
        time.sleep(SCAN_INTERVAL)

# ==================== لوحة التحكم ====================

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<title>Hyper Fast Genesis Sniper</title>
<meta http-equiv="refresh" content="3">
<style>
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f1115; color: #eee; padding: 20px; }
  h1 { color: #facc15; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; }
  th, td { padding: 12px; text-align: right; border-bottom: 1px solid #2a2d34; }
  th { color: #888; font-weight: normal; }
  tr:hover { background: #1a1d24; }
  .ca { color: #38bdf8; font-family: monospace; font-size: 14px; }
  .badge { background: #1e293b; color: #38bdf8; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
  .btn-okx { background: #2563eb; color: #fff; padding: 4px 10px; border-radius: 4px; text-decoration: none; font-size: 13px; }
  .btn-def { background: #059669; color: #fff; padding: 4px 10px; border-radius: 4px; text-decoration: none; font-size: 13px; }
</style>
</head>
<body>
  <h1>⚡🚀 Hyper Fast Genesis Sniper (2s Refresh)</h1>
  <p>يعمل بأعلى سرعة استجابة ممكنة | الصفقات المتاحة: {{ signals|length }}</p>
  <table>
    <tr><th>الوقت (UTC)</th><th>السلسلة</th><th>العملة</th><th>FDV</th><th>السيولة</th><th>العقد (CA)</th><th>Defined</th><th>OKX DEX</th></tr>
    {% for s in signals %}
    <tr>
      <td>{{ s.time }}</td>
      <td><span class="badge">{{ s.chain }}</span></td>
      <td><b>{{ s.symbol }}</b></td>
      <td style="color: #facc15;">{{ s.fdv }} 🚀</td>
      <td>${{ "%.0f"|format(s.liquidity) }}</td>
      <td class="ca">{{ s.address }}</td>
      <td><a href="{{ s.defined_url }}" target="_blank" class="btn-def">Defined ↗</a></td>
      <td><a href.="{{ s.okx_url }}" target="_blank" class="btn-okx">شراء OKX ⚡</a></td>
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

if __name__ == "__main__":
    t = threading.Thread(target=run_sniper_loop, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
