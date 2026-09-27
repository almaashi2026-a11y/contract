# instant_genesis_sniper.py
# بوت صيد الألفا اللحظي - جلب الأزواج الجديدة فور إنشائها (Real-Time New Pairs)

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

SCAN_INTERVAL = 5           # فحص سريع جداً كل 5 ثوانٍ لرصد أحدث التوكنات

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("genesis_sniper")

alerted_tokens = {}
recent_signals = []

# ==================== جلب أحدث الأزواج اللحظية مباشرة ====================

def get_latest_genesis_tokens():
    """جلب أحدث الأزواج المضافة في العالم لحظياً وتصفيتها"""
    approved_tokens = []
    
    try:
        # استخدام نقطة النهاية العامة لأحدث التوكنات أو البحث المباشر للجديد
        url = "https://api.dexscreener.com/latest/dex/tokens/latest"
        # إذا لم تتوفر، نستخدم جلب الـ Boosts أو الـ Latest Profiles
        r = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=6)
        
        if r.status_code == 200:
            profiles = r.json() or []
            # استخراج العناوين للتحقق السريع منها عبر DexScreener pairs API
            addresses = [p.get("tokenAddress") for p in profiles if p.get("tokenAddress")]
            
            # جلب تفاصيل الأزواج لهذه العناوين الجديدة فوراً
            for addr in addresses[:15]:
                try:
                    pair_r = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{addr}", timeout=4)
                    if pair_r.status_code == 200:
                        data = pair_r.json()
                        pairs = data.get("pairs", []) or []
                        for p in pairs:
                            liq = float((p.get("liquidity") or {}).get("usd") or 0)
                            fdv = float(p.get("fdv") or 0)
                            
                            # شروط دقيقة للسيولة والقيمة السوقية للعملات الناشئة جداً
                            if 1000 <= liq <= 500000 and 0 < fdv <= 1000000:
                                approved_tokens.append(p)
                    time.sleep(0.1)
                except:
                    continue
        
        # طريقة بديلة احتياطية لضمان عدم توقف الفحص اللحظي
        if not approved_tokens:
            fallback_url = "https://api.dexscreener.com/latest/dex/search?q=solana"
            rf = requests.get(fallback_url, timeout=6)
            if rf.status_code == 200:
                pairs = rf.json().get("pairs", []) or []
                for p in pairs:
                    # اختيار العملات ذات الإنشاء الأحدث أو النشاط المبكر
                    pair_created = p.get("pairCreatedAt", 0)
                    now_ts = time.time() * 1000
                    # إذا كانت منشأة في آخر ساعتين
                    if pair_created and (now_ts - pair_created < 7200000):
                        liq = float((p.get("liquidity") or {}).get("usd") or 0)
                        if 1000 <= liq <= 300000:
                            approved_tokens.append(p)

    except Exception as e:
        log.error(f"خطأ في جلب التوكنات اللحظية: {e}")
        
    return approved_tokens[:10]

# ==================== إرسال التنبيهات الفورية ====================

def send_genesis_alert(token):
    chain = token.get("chainId", "unknown").upper()
    symbol = token.get("baseToken", {}).get("symbol", "UNKNOWN")
    name = token.get("baseToken", {}).get("name", "Token")
    token_address = token.get("baseToken", {}).get("address", "")
    fdv = float(token.get("fdv") or 0)
    liquidity = float((token.get("liquidity") or {}).get("usd") or 0)
    
    pair_url = token.get("url", f"https://dexscreener.com/{token.get('chainId', 'solana')}/{token_address}")
    
    if fdv >= 1000000:
        fdv_str = f"{fdv / 1000000:.1f}M"
    else:
        fdv_str = f"{fdv / 1000:.1f}K"

    message = (
        f"⚡🚨 **GENESIS NEW PAIR ({chain})**\n"
        f"🔥 Fresh Token Launched (Instant Catch)\n\n"
        f"🌐 **السلسلة:** `{chain}`\n"
        f"🪙 **التوكن:** {name} (`{symbol}`)\n"
        f"🚀 **القيمة السوقية (FDV):** `{fdv_str} 🚀`\n"
        f"💧 **السيولة الأولية:** `${liquidity:,.0f}`\n\n"
        f"🔑 **عقد التوكن (CA):**\n`{token_address}`\n\n"
        f"🛡️ **روابط الفحص الفوري والتنفيذ:**\n"
        f"🔗 [DexScreener]({pair_url})\n"
        f"🎯 [GMGN (الأوائل)](https://gmgn.ai/{token.get('chainId', 'solana')}/token/{token_address})\n"
        f"🗺️ [BubbleMaps (المحافظ)](https://app.bubblemaps.io/{token.get('chainId', 'solana')}/{token_address})"
    )

    signal = {
        "chain": chain, "symbol": symbol, "fdv": fdv_str, "liquidity": liquidity,
        "address": token_address, "url": pair_url,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }
    recent_signals.insert(0, signal)
    if len(recent_signals) > 60:
        recent_signals.pop()

    log.info(f"إشارة جديدة فوريّة [{chain}]: {symbol}")

    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }, timeout=8)
        except Exception as e:
            log.warning(f"فشل إرسال تنبيه Telegram: {e}")

def run_sniper_loop():
    while True:
        try:
            tokens = get_latest_genesis_tokens()
            for token in tokens:
                token_address = token.get("baseToken", {}).get("address", "")
                if not token_address:
                    continue
                
                # عدم التكرار لمدة 3 ساعات
                last_alert = alerted_tokens.get(token_address)
                if last_alert and (datetime.utcnow() - last_alert) < timedelta(hours=3):
                    continue
                
                send_genesis_alert(token)
                alerted_tokens[token_address] = datetime.utcnow()
                time.sleep(1)
        except Exception as e:
            log.error(f"خطأ في حلقة الرصد اللحظي السريع: {e}")
            
        time.sleep(SCAN_INTERVAL)

# ==================== لوحة التحكم المرئية ====================

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<title>Genesis Instant Sniper - لوحة الصيد اللحظي</title>
<meta http-equiv="refresh" content="5">
<style>
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f1115; color: #eee; padding: 20px; }
  h1 { color: #facc15; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; }
  th, td { padding: 12px; text-align: right; border-bottom: 1px solid #2a2d34; }
  th { color: #888; font-weight: normal; }
  tr:hover { background: #1a1d24; }
  .ca { color: #38bdf8; font-family: monospace; font-size: 14px; }
  .badge { background: #1e293b; color: #38bdf8; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
  a { color: #4ade80; text-decoration: none; }
  a:hover { text-decoration: underline; }
</style>
</head>
<body>
  <h1>⚡🔥 Genesis Instant New Pairs Sniper</h1>
  <p>رصد مباشر وفوري للأزواج الجديدة كل 5 ثوانٍ | إجمالي الصفقات اللحظية: {{ signals|length }}</p>
  <table>
    <tr><th>الوقت (UTC)</th><th>السلسلة</th><th>العملة</th><th>القيمة السوقية</th><th>السيولة الأولية</th><th>عقد التوكن (CA)</th><th>الرابط</th></tr>
    {% for s in signals %}
    <tr>
      <td>{{ s.time }}</td>
      <td><span class="badge">{{ s.chain }}</span></td>
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
