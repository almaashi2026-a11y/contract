# smart_alpha_sniper.py
# بوت صيد عقود Alpha والـ Pump على شبكة سولانا - محدث وفوري

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

SCAN_INTERVAL = 20          # فحص سريع كل 20 ثانية

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("alpha_sniper")

alerted_tokens = {}
recent_signals = []

# ==================== جلب التوكنات عبر نقطة Boosts النشطة ====================

def get_solana_alpha_tokens():
    """جلب أحدث التوكنات النشطة والمدعومة على شبكة سولانا مباشرة"""
    try:
        url = "https://api.dexscreener.com/token-boosts/latest/v1"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        items = r.json()
        
        tokens_to_check = []
        if isinstance(items, list):
            for item in items:
                if item.get("chainId") == "solana":
                    addr = item.get("tokenAddress")
                    if addr:
                        tokens_to_check.append(addr)
        
        # جلب تفاصيل كل توكن من واجهة DexScreener المباشرة للعقد
        valid_pairs = []
        for addr in tokens_to_check[:15]: # فحص أول 15 توكن لسرعة الاستجابة
            detail_url = f"https://api.dexscreener.com/latest/dex/tokens/{addr}"
            res = requests.get(detail_url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                pairs = data.get("pairs", [])
                if pairs:
                    sol_pairs = [p for p in pairs if p.get("chainId") == "solana"]
                    if sol_pairs:
                        valid_pairs.append(sol_pairs[0])
            time.sleep(0.1)
            
        return valid_pairs
    except Exception as e:
        log.warning(f"خطأ بجلب بيانات سولانا: {e}")
        return []

# ==================== إرسال تنبيه الـ VIP على التيليجرام ====================

def send_vip_alert(token):
    symbol = token.get("baseToken", {}).get("symbol", "UNKNOWN")
    name = token.get("baseToken", {}).get("name", "Meme Token")
    token_address = token.get("baseToken", {}).get("address", "")
    fdv = float(token.get("fdv") or 0)
    liquidity = float((token.get("liquidity") or {}).get("usd") or 0)
    pair_url = token.get("url", f"https://dexscreener.com/solana/{token_address}")
    
    if fdv >= 1000000:
        fdv_str = f"{fdv / 1000000:.1f}M"
    else:
        fdv_str = f"{fdv / 1000:.1f}K"

    message = (
        f"🚨🔥 **MR YÚMĂ CHAD ☎️ PRIVATE (CALLS):**\n"
        f"Everyone get ready imma drop a free ca SOLANA chain form the vip group turn on your notifications\n\n"
        f"🪙 **التوكن:** {name} (`{symbol}`)\n"
        f"🚀 **القيمة السوقية (FDV):** `{fdv_str} 🚀🚀`\n"
        f"💧 **السيولة:** `${liquidity:,.0f}`\n\n"
        f"🔑 **عقد التوكن (CA):**\n`{token_address}`\n\n"
        f"🛡️ **روابط الفحص والتنفيذ السريع:**\n"
        f"🔗 [DexScreener]({pair_url})\n"
        f"🎯 [GMGN (تتبع الأوائل)](https://gmgn.ai/solana/token/{token_address})\n"
        f"🗺️ [BubbleMaps (تحليل المحافظ)](https://app.bubblemaps.io/solana/{token_address})"
    )

    signal = {
        "symbol": symbol, "fdv": fdv_str, "liquidity": liquidity,
        "address": token_address, "url": pair_url,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }
    recent_signals.insert(0, signal)
    if len(recent_signals) > 50:
        recent_signals.pop()

    log.info(f"إشارة VIP جديدة: {symbol} بقيمة {fdv_str}")

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
            tokens = get_solana_alpha_tokens()
            for token in tokens:
                token_address = token.get("baseToken", {}).get("address", "")
                if not token_address:
                    continue
                
                last_alert = alerted_tokens.get(token_address)
                if last_alert and (datetime.utcnow() - last_alert) < timedelta(hours=1):
                    continue
                
                send_vip_alert(token)
                alerted_tokens[token_address] = datetime.utcnow()
                time.sleep(1)
        except Exception as e:
            log.error(f"خطأ في حلقة الرصد: {e}")
            
        time.sleep(SCAN_INTERVAL)

# ==================== لوحة التحكم المرئية (Dashboard) ====================

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<title>Alpha Sniper VIP - لوحة الصيد</title>
<meta http-equiv="refresh" content="15">
<style>
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f1115; color: #eee; padding: 20px; }
  h1 { color: #facc15; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; }
  th, td { padding: 12px; text-align: right; border-bottom: 1px solid #2a2d34; }
  th { color: #888; font-weight: normal; }
  tr:hover { background: #1a1d24; }
  .ca { color: #38bdf8; font-family: monospace; font-size: 14px; }
  a { color: #4ade80; text-decoration: none; }
  a:hover { text-decoration: underline; }
</style>
</head>
<body>
  <h1>🔥 صقر صيد Alpha (VIP Calls) - سولانا</h1>
  <p>يتم تحديث الإشارات تلقائياً كل 15 ثانية | إجمالي الإشارات النشطة: {{ signals|length }}</p>
  <table>
    <tr><th>الوقت (UTC)</th><th>العملة</th><th>القيمة السوقية</th><th>السيولة</th><th>عقد التوكن (CA)</th><th>الرابط</th></tr>
    {% for s in signals %}
    <tr>
      <td>{{ s.time }}</td>
      <td><b>{{ s.symbol }}</b></td>
      <td style="color: #facc15;">{{ s.fdv }} 🚀</td>
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
