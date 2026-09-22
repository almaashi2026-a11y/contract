# smart_money_tracker.py
# متتبع المال الذكي - متعدد السلاسل (Solana + EVM + Ronin + Tron)
# تشغيل واحد: worker + dashboard على Render

import os
import time
import json
import logging
import threading
import requests
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template_string
from collections import defaultdict

# ==================== الإعدادات ====================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# السلاسل المدعومة
CHAINS = {
    "solana": {"dexscreener_id": "solana"},
    "ethereum": {"dexscreener_id": "ethereum"},
    "bsc": {"dexscreener_id": "bsc"},
    "base": {"dexscreener_id": "base"},
    "arbitrum": {"dexscreener_id": "arbitrum"},
    "polygon": {"dexscreener_id": "polygon"},
    "ronin": {"dexscreener_id": "ronin"},
    "tron": {"dexscreener_id": "tron"},
}

SCAN_INTERVAL = 60          # ثانية بين كل دورة فحص
MIN_SMART_WALLETS = 2       # أقل عدد محافظ "ذكية" لإطلاق تنبيه
MIN_LIQUIDITY_USD = 20000   # أقل سيولة للتوكن حتى نعتبره
WALLET_WIN_RATE_THRESHOLD = 0.55  # نسبة نجاح تاريخية دنيا لاعتبار المحفظة "ذكية"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("smart_money")

# ذاكرة داخلية (بديل بسيط لقاعدة بيانات - ينفع تستبدلها بـ Postgres لاحقاً)
wallet_cache = {}       # wallet_address -> {win_rate, trades, last_checked}
alerted_tokens = {}     # token_address -> timestamp آخر تنبيه
recent_signals = []     # آخر الإشارات للعرض بالـ dashboard

# ==================== طبقة جلب البيانات ====================

def get_trending_tokens(chain_id):
    """يجيب التوكنات النشطة/الترند من Dexscreener لسلسلة معينة"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/search?q={chain_id}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        pairs = data.get("pairs", []) or []
        # فلترة حسب السلسلة والسيولة
        filtered = [
            p for p in pairs
            if p.get("chainId") == chain_id
            and float((p.get("liquidity") or {}).get("usd") or 0) >= MIN_LIQUIDITY_USD
        ]
        # ترتيب حسب تغيّر الحجم خلال الساعة (إشارة تجميع)
        filtered.sort(key=lambda p: float((p.get("volume") or {}).get("h1") or 0), reverse=True)
        return filtered[:30]
    except Exception as e:
        log.warning(f"خطأ بجلب الترند لـ {chain_id}: {e}")
        return []


def get_token_holders(chain_id, token_address):
    """
    يجيب أكبر الحائزين لتوكن معين.
    ملاحظة: هذا endpoint عام يحتاج تستبدله حسب السلسلة:
    - Solana: Helius / Solscan API
    - EVM (eth/bsc/base/arb/polygon/ronin): Etherscan-family APIs أو Moralis
    - Tron: Tronscan API
    هنا مثال عام قابل للتوسعة - ضيف مفاتيح API الخاصة بك بمتغيرات البيئة
    """
    try:
        if chain_id == "solana":
            return _get_solana_holders(token_address)
        elif chain_id == "tron":
            return _get_tron_holders(token_address)
        else:
            return _get_evm_holders(chain_id, token_address)
    except Exception as e:
        log.warning(f"خطأ بجلب الحائزين {token_address} على {chain_id}: {e}")
        return []


def _get_solana_holders(token_address):
    helius_key = os.environ.get("HELIUS_API_KEY", "")
    if not helius_key:
        return []
    url = f"https://api.helius.xyz/v0/token-metadata?api-key={helius_key}"
    # استخدم getTokenLargestAccounts عبر RPC بدلاً من ذلك:
    rpc_url = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
    payload = {
        "jsonrpc": "2.0", "id": 1,
        "method": "getTokenLargestAccounts",
        "params": [token_address]
    }
    r = requests.post(rpc_url, json=payload, timeout=10)
    result = r.json().get("result", {}).get("value", [])
    return [acc["address"] for acc in result[:20]]


def _get_evm_holders(chain_id, token_address):
    # مثال باستخدام Etherscan-family (استبدل بالمفتاح ورابط API المناسب للسلسلة)
    api_key = os.environ.get(f"{chain_id.upper()}_API_KEY", "")
    explorer_base = {
        "ethereum": "https://api.etherscan.io/api",
        "bsc": "https://api.bscscan.com/api",
        "base": "https://api.basescan.org/api",
        "arbitrum": "https://api.arbiscan.io/api",
        "polygon": "https://api.polygonscan.com/api",
        "ronin": "https://explorer-kintsugi.roninchain.com/api",  # يحتاج تعديل حسب توفر API
    }.get(chain_id)
    if not explorer_base or not api_key:
        return []
    url = f"{explorer_base}?module=token&action=tokenholderlist&contractaddress={token_address}&apikey={api_key}"
    r = requests.get(url, timeout=10)
    result = r.json().get("result", [])
    return [h["TokenHolderAddress"] for h in result[:20]] if isinstance(result, list) else []


def _get_tron_holders(token_address):
    url = f"https://apilist.tronscanapi.com/api/token_trc20/holders?contract_address={token_address}&limit=20"
    r = requests.get(url, timeout=10)
    data = r.json()
    return [h["address"] for h in data.get("trc20_tokens", [])[:20]]


def get_wallet_win_rate(chain_id, wallet_address):
    """
    يحسب نسبة نجاح المحفظة التاريخية (مبسطة).
    ينصح تستبدلها بخدمة متخصصة (زي GMGN API أو Nansen) لدقة أعلى.
    """
    cache_key = f"{chain_id}:{wallet_address}"
    cached = wallet_cache.get(cache_key)
    if cached and (datetime.utcnow() - cached["last_checked"]) < timedelta(hours=6):
        return cached["win_rate"]

    # Placeholder: بدون API مدفوع، نرجع قيمة محايدة
    # للتفعيل الكامل: اربطها بـ GMGN API أو Nansen API لجلب سجل المحفظة الحقيقي
    win_rate = 0.5
    wallet_cache[cache_key] = {"win_rate": win_rate, "last_checked": datetime.utcnow()}
    return win_rate


# ==================== منطق الرصد ====================

def scan_chain(chain_id):
    tokens = get_trending_tokens(CHAINS[chain_id]["dexscreener_id"])
    for token in tokens:
        token_address = token.get("baseToken", {}).get("address")
        token_symbol = token.get("baseToken", {}).get("symbol", "?")
        if not token_address:
            continue

        holders = get_token_holders(chain_id, token_address)
        smart_wallets = []
        for wallet in holders:
            win_rate = get_wallet_win_rate(chain_id, wallet)
            if win_rate >= WALLET_WIN_RATE_THRESHOLD:
                smart_wallets.append(wallet)

        if len(smart_wallets) >= MIN_SMART_WALLETS:
            last_alert = alerted_tokens.get(token_address)
            if last_alert and (datetime.utcnow() - last_alert) < timedelta(hours=4):
                continue  # ما نكرر نفس التنبيه بسرعة

            send_alert(chain_id, token, token_symbol, smart_wallets)
            alerted_tokens[token_address] = datetime.utcnow()


def send_alert(chain_id, token, symbol, smart_wallets):
    price = token.get("priceUsd", "?")
    liquidity = (token.get("liquidity") or {}).get("usd", 0)
    volume_h1 = (token.get("volume") or {}).get("h1", 0)
    pair_url = token.get("url", "")

    message = (
        f"🐋 <b>إشارة مال ذكي جديدة</b>\n\n"
        f"السلسلة: {chain_id.upper()}\n"
        f"العملة: <b>{symbol}</b>\n"
        f"عدد المحافظ الذكية: {len(smart_wallets)}\n"
        f"السعر: ${price}\n"
        f"السيولة: ${liquidity:,.0f}\n"
        f"حجم التداول (1س): ${volume_h1:,.0f}\n\n"
        f"🔗 {pair_url}"
    )

    signal = {
        "chain": chain_id, "symbol": symbol, "smart_wallets": len(smart_wallets),
        "price": price, "liquidity": liquidity, "url": pair_url,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }
    recent_signals.insert(0, signal)
    if len(recent_signals) > 50:
        recent_signals.pop()

    log.info(f"إشارة جديدة: {symbol} على {chain_id} - {len(smart_wallets)} محفظة")

    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }, timeout=10)
        except Exception as e:
            log.warning(f"فشل إرسال تنبيه Telegram: {e}")


def run_scanner_loop():
    while True:
        for chain_id in CHAINS:
            try:
                scan_chain(chain_id)
            except Exception as e:
                log.error(f"خطأ بفحص {chain_id}: {e}")
        time.sleep(SCAN_INTERVAL)


# ==================== Dashboard بسيط ====================

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<title>متتبع المال الذكي</title>
<meta http-equiv="refresh" content="30">
<style>
  body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f1115; color: #eee; padding: 20px; }
  h1 { color: #4ade80; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; }
  th, td { padding: 10px; text-align: right; border-bottom: 1px solid #2a2d34; }
  th { color: #888; font-weight: normal; }
  tr:hover { background: #1a1d24; }
  .chain { color: #60a5fa; font-weight: bold; }
  a { color: #4ade80; text-decoration: none; }
</style>
</head>
<body>
  <h1>🐋 متتبع المال الذكي - إشارات مباشرة</h1>
  <p>آخر تحديث تلقائي كل 30 ثانية | عدد الإشارات: {{ signals|length }}</p>
  <table>
    <tr><th>الوقت</th><th>السلسلة</th><th>العملة</th><th>محافظ ذكية</th><th>السعر</th><th>السيولة</th><th>رابط</th></tr>
    {% for s in signals %}
    <tr>
      <td>{{ s.time }}</td>
      <td class="chain">{{ s.chain }}</td>
      <td>{{ s.symbol }}</td>
      <td>{{ s.smart_wallets }}</td>
      <td>${{ s.price }}</td>
      <td>${{ "%.0f"|format(s.liquidity) }}</td>
      <td><a href="{{ s.url }}" target="_blank">فتح ↗</a></td>
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


# ==================== نقطة التشغيل ====================

if __name__ == "__main__":
    scanner_thread = threading.Thread(target=run_scanner_loop, daemon=True)
    scanner_thread.start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
