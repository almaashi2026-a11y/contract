import os
import time
import json
import requests
import threading
from flask import Flask, render_template_string
from collections import defaultdict, OrderedDict

app = Flask('')

TG_TOKEN = os.environ.get("TG_TOKEN")
TG_CHAT = os.environ.get("TG_CHAT")
GAMMA = "https://gamma-api.polymarket.com"
DATA = "https://data-api.polymarket.com"

ARB_MAX_SUM = 0.98     # مجموع YES+NO أقل من هذا = فرصة تحكيم
MIN_LIQ = 1000         # حد أدنى للسيولة
MIN_TRADES = 15        # حد أدنى لصفقات المحفظة لتصبح تحت المراقبة الذكية
MIN_VOL = 3000         # حد أدنى لحجم المحفظة بالدولار
ALERT_MIN_USD = 50     # لا تنبّه على صفقات أصغر من هذا الرقم

# نظام ذاكرة ذكي يمنع التكرار ويحمي الذاكرة من الامتلاء (Max 15000 عنصر)
SEEN = OrderedDict()
MAX_SEEN_SIZE = 15000

wallets = defaultdict(lambda: {"n": 0, "vol": 0.0})
system_status = "🔄 السكريبت بدأ العمل ويقوم بمسح أسواق Polymarket..."

def add_to_seen(key):
    if key in SEEN:
        SEEN.move_to_end(key)
        return True
    SEEN[key] = True
    if len(SEEN) > MAX_SEEN_SIZE:
        SEEN.popitem(last=False)
    return False

def tg(msg):
    if not TG_TOKEN or not TG_CHAT:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg, "disable_web_page_preview": True},
            timeout=10
        )
    except Exception as e:
        print("Telegram Error:", e)

def get(url, **params):
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, (list, dict)) else []
    except Exception as e:
        print(f"API Error [{url}]:", e)
        return []

def scan_arb():
    global system_status
    markets = get(f"{GAMMA}/markets", active="true", closed="false", limit=500)
    if not isinstance(markets, list):
        return
        
    for m in markets:
        try:
            prices_raw = m.get("outcomePrices")
            if not prices_raw:
                continue
            prices = [float(x) for x in json.loads(prices_raw)]
            liq = float(m.get("liquidityNum") or 0)
        except Exception:
            continue
            
        if len(prices) != 2 or liq < MIN_LIQ:
            continue
            
        s = sum(prices)
        if s < ARB_MAX_SUM:
            key = ("arb", m.get("id"), round(s, 2))
            if add_to_seen(key):
                continue
                
            profit_pct = (1 - s) * 100
            msg = (
                f"🎯 **[فرصة تحكيم مؤسسية - ARB]**\n"
                f"📌 السوق: {m.get('question', 'N/A')}\n"
                f"⚖️ مجموع الأسعار (YES+NO): `{s:.3f}`\n"
                f"💎 ربح نظري تقديري: `+{profit_pct:.1f}%`\n"
                f"💧 السيولة المتاحة: `${liq:,.0f}`\n"
                f"🔗 [رابط السوق على Polymarket](https://polymarket.com/market/{m.get('slug', '')})\n"
                f"⚠️ *ملاحظة:* تحقق من الرسوم وانزلاق السعر قبل التنفيذ."
            )
            tg(msg)
            system_status = f"🎯 آخر فرصة رصدت: {m.get('question', 'N/A')} (ربح: {profit_pct:.1f}%)"

def poll_trades():
    trades = get(f"{DATA}/trades", limit=500)
    if not isinstance(trades, list):
        return
        
    for t in trades:
        try:
            tx_hash = t.get("transactionHash")
            asset = t.get("asset")
            side = t.get("side")
            if not tx_hash or not asset:
                continue
                
            key = (tx_hash, asset, side)
            if add_to_seen(key):
                continue
                
            w = t.get("proxyWallet")
            if not w:
                continue
                
            size = float(t.get("size", 0) or 0)
            price = float(t.get("price", 0) or 0)
            usd = size * price
            
            st = wallets[w]
            st["n"] += 1
            st["vol"] += usd
            
            watched = st["n"] >= MIN_TRADES and st["vol"] >= MIN_VOL
            if watched and usd >= ALERT_MIN_USD:
                msg = (
                    f"🐋 **[رصد محفظة ذكية / حوت]**\n"
                    f"👛 المحفظة: `{w[:6]}…{w[-4:]}`\n"
                    f"🔄 العملية: `{side} {t.get('outcome', '')}` بسعر `{price}`\n"
                    f"📌 العنوان: {t.get('title', 'N/A')}\n"
                    f"💵 حجم الصفقة: `${usd:,.0f}`\n"
                    f"📊 إحصائيات المحفظة: {st['n']} صفقة | إجمالي الحجم: `${st['vol']:,.0f}`"
                )
                tg(msg)
        except Exception:
            continue

def background_monitor():
    tg("✅ **Polymarket Pro Sentinel** يعمل الآن بأقصى كفاءة وثبات...")
    last_arb = 0
    while True:
        try:
            poll_trades()
            current_time = time.time()
            if current_time - last_arb > 60:
                scan_arb()
                last_arb = current_time
        except Exception as e:
            print("Monitor Loop Error:", e)
        time.sleep(10)

@app.route('/')
def index():
    return f"""
    <html>
        <head><title>Polymarket Pro Sentinel - عبد الرحمن</title></head>
        <body style="background: #0f172a; color: #38bdf8; font-family: monospace; text-align: center; padding-top: 50px;">
            <h1>🚀 Polymarket Pro Sentinel is Running 24/7</h1>
            <p>حالة النظام: {system_status}</p>
            <p style="color: #34d399;">المتتبع يعمل في الخلفية ويرسل التنبيهات إلى تيليجرام بنجاح.</p>
        </body>
    </html>
    """

if __name__ == "__main__":
    # تشغيل مراقب السوق في خيط منفصل (Background Thread)
    t = threading.Thread(target=background_monitor)
    t.daemon = True
    t.start()
    
    # تشغيل سيرفر الويب لفتح المنفذ وإرضاء منصة Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
