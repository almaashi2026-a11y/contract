# genesis_sniper_v7_active.py
# بوت صيد الألفا - تصفية العملات الميتة والتركيز على العملات النشطة فور ولادتها

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

SCAN_INTERVAL = 3

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("active_sniper_v7")

alerted_tokens = set()
active_positions = []

# ==================== جلب العملات النشطة والجديدة ====================

def get_active_genesis_tokens():
    """جلب العملات الجديدة التي تمتلك حركة تداول حقيقية وسيولة نشطة"""
    approved_tokens = []
    
    try:
        url = "https://api.dexscreener.com/latest/dex/search?q=solana"
        r = requests.get(url, timeout=4)
        
        if r.status_code == 200:
            data = r.json()
            pairs = data.get("pairs", []) or []
            
            now_ts = time.time() * 1000
            
            for p in pairs:
                pair_created = p.get("pairCreatedAt", 0)
                liq = float((p.get("liquidity") or {}).get("usd") or 0)
                fdv = float(p.get("fdv") or 0)
                
                # التحقق من الصفقات والنشاط (لمنع العملات الميتة ذات الـ 0 صفقات)
                txns = p.get("txns", {}).get("h1", {})
                h1_buys = int(txns.get("buys", 0))
                h1_sells = int(txns.get("sells", 0))
                total_txns = h1_buys + h1_sells
                
                base_token = p.get("baseToken", {})
                symbol = base_token.get("symbol")
                address = base_token.get("address")
                
                # شروط دقيقة: عمر الزوج جديد (أقل من ساعتين) + سيولة مقبولة + صفقات نشطة وليست ميتة
                is_new = (pair_created > 0) and ((now_ts - pair_created) < 7200000)
                
                if symbol and address and is_new and liq >= 1000 and fdv > 0 and total_txns > 2:
                    approved_tokens.append(p)
                    
    except Exception as e:
        log.error(f"خطأ في جلب العملات النشطة: {e}")
        
    return approved_tokens[:10]

# ==================== الإرسال الفوري ====================

def send_active_alert(token):
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
        f"⚡🚀 **ACTIVE GENESIS TOKEN ({chain_upper})**\n"
        f"🎯 *فلوس الميم في الدوران، مش في الإيمان.*\n\n"
        f"🌐 **السلسلة:** `{chain_upper}`\n"
        f"🪙 **التوكن:** {name} (`{symbol}`)\n"
        f"🚀 **FDV:** `{fdv_str}`\n"
        f"💧 **السيولة:** `${liquidity:,.0f}`\n\n"
        f"🔑 **العقد (CA):**\n`{token_address}`\n\n"
        f"🛡️ **روابط التحليل:**\n"
        f"📊 [Defined.fi]({defined_url})\n"
        f"⚡ [شراء OKX DEX]({okx_trade_url})"
    )

    position = {
        "chain": chain_upper, "symbol": symbol, "fdv": fdv_str, "liquidity": liquidity,
        "address": token_address, "defined_url": defined_url, "okx_url": okx_trade_url,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "نشط وله تداولات"
    }
    
    if token_address not in alerted_tokens:
        alerted_tokens.add(token_address)
        active_positions.insert(0, position)
        if len(active_positions) > 30:
            active_positions.pop()

        log.info(f"اكتشاف عملة نشطة [{chain_upper}]: {symbol}")

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
            tokens = get_active_genesis_tokens()
            for token in tokens:
                token_address = token.get("baseToken", {}).get("address", "")
                if token_address:
                    send_active_alert(token)
        except Exception as e:
            log.error(f"خطأ في حلقة الرصد: {e}")
            
        time.sleep(SCAN_INTERVAL)

# ==================== لوحة التحكم ====================

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<title>Active Genesis Sniper</title>
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
  <h1>⚡ Active Genesis Sniper (No Dead Coins)</h1>
  <p>فلوس الميم في الدوران | العملات النشطة حديثاً فقط: {{ positions|length }}</p>
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
