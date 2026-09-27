# smart_alpha_sniper.py
# بوت صيد عقود Alpha الذكي - فلترة عالية الجودة لشبكة سولانا

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

SCAN_INTERVAL = 15          # فحص ذكي كل 15 ثانية

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("alpha_sniper")

alerted_tokens = {}
recent_signals = []

# ==================== الفلترة الذكية للتوكنات القوية ====================

def get_solana_alpha_tokens():
    """جلب أحدث التوكنات وتصفيتها بناءً على معايير السيولة والزخم الحقيقي"""
    try:
        # استخدام نقطة البحث والترند النشط لجلب أحدث الأزواج
        url = "https://api.dexscreener.com/latest/dex/search?q=solana"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        pairs = data.get("pairs", []) or []
        
        filtered_pairs = []
        for p in pairs:
            if p.get("chainId") == "solana":
                # استخراج البيانات المالية
                liq = float((p.get("liquidity") or {}).get("usd") or 0)
                fdv = float(p.get("fdv") or 0)
                vol_h1 = float((p.get("volume") or {}).h1 if hasattr((p.get("volume") or {}), 'h1') else (p.get("volume") or {}).get("h1") or 0)
                
                # 🛡️ معايير الجودة الصارمة لضمان إشارات قوية:
                # 1. السيولة بين 8,000$ و 200,000$ (فرص نمو صاروخية)
                # 2. القيمة السوقية أقل من 1,000,000$
                # 3. وجود تداول حפي (حجم تداول نشط)
                if 8000 <= liq <= 200000 and 0 < fdv <= 1000000:
                    filtered_pairs.append(p)
                    
        # ترتيب حسب الأعلى حجماً وتفاعلاً
        filtered_pairs.sort(key=lambda x: float((x.get("volume") or {}).get("h1") or 0), reverse=True)
        return filtered_pairs[:10]
    except Exception as e:
        log.warning(f"خطأ بجلب بيانات سولانا الذكية: {e}")
        return []

# ==================== إرسال تنبيه النخبة على التيليجرام ====================

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

    # تنسيق احترافي ونظيف بدون عناوين وهمية، مخصص لصفقات الـ Alpha الحقيقية
    message = (
        f"🚨🔥 **ALPHA SNIPER CALLS (SOLANA):**\n"
        f"⚡ High Momentum Token Detected!\n\n"
        f"🪙 **التوكن:** {name} (`{symbol}`)\n"
        f"🚀 **القيمة السوقية (FDV):** `{fdv_str} 🚀🚀`\n"
        f"💧 **السيولة:** `${liquidity:,.0f}`\n\n"
        f"🔑 **عقد التوكن (CA):**\n`{token_address}`\n\n"
        f"🛡️ **روابط الفحص السريع:**\n"
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

    log.info(f"إشارة قوية جديدة: {symbol} بقيمة {fdv_str}")

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
                
                # عدم تكرار نفس التوكن خلال ساعتين
                last_alert = alerted_tokens.get(token_address)
                if last_alert and (datetime.utcnow() - last_alert) < timedelta(hours=2):
                    continue
                
                send_vip_alert(token)
                alerted_tokens[token_address] = datetime.utcnow()
                time.sleep(2)
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
<title>Alpha Sniper VIP - صيد العملات القوية</title>
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
  <h1>🔥 لوحة صيد Alpha المفلترة - سولانا</h1>
  <p>تحديث تلقائي كل 15 ثانية | الصفقات ذات السيولة والزخم الحقيقي: {{ signals|length }}</p>
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
