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

# سجلات العرض في لوحة التحكم
stats = {
    "status": "🔄 جاري تهيئة النظام وبدء المسح...",
    "arb_count": 0,
    "whale_count": 0,
    "last_update": "لم يتم التحديث بعد",
    "recent_arbs": [],
    "recent_whales": []
}

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
    global stats
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
            q_text = m.get('question', 'N/A')
            slug = m.get('slug', '')
            
            msg = (
                f"🎯 **[فرصة تحكيم مؤسسية - ARB]**\n"
                f"📌 السوق: {q_text}\n"
                f"⚖️ مجموع الأسعار (YES+NO): `{s:.3f}`\n"
                f"💎 ربح نظري تقديري: `+{profit_pct:.1f}%`\n"
                f"💧 السيولة المتاحة: `${liq:,.0f}`\n"
                f"🔗 [رابط السوق](https://polymarket.com/market/{slug})\n"
                f"⚠️ *ملاحظة:* تحقق من الرسوم وانزلاق السعر قبل التنفيذ."
            )
            tg(msg)
            
            stats["arb_count"] += 1
            stats["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
            stats["recent_arbs"].insert(0, {
                "question": q_text,
                "sum": f"{s:.3f}",
                "profit": f"+{profit_pct:.1f}%",
                "liq": f"${liq:,.0f}",
                "link": f"https://polymarket.com/market/{slug}"
            })
            if len(stats["recent_arbs"]) > 10:
                stats["recent_arbs"].pop()

def poll_trades():
    global stats
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
                w_short = f"{w[:6]}…{w[-4:]}"
                title = t.get('title', 'N/A')
                outcome = t.get('outcome', '')
                
                msg = (
                    f"🐋 **[رصد محفظة ذكية / حوت]**\n"
                    f"👛 المحفظة: `{w_short}`\n"
                    f"🔄 العملية: `{side} {outcome}` بسعر `{price}`\n"
                    f"📌 العنوان: {title}\n"
                    f"💵 حجم الصفقة: `${usd:,.0f}`\n"
                    f"📊 إحصائيات المحفظة: {st['n']} صفقة | إجمالي الحجم: `${st['vol']:,.0f}`"
                )
                tg(msg)
                
                stats["whale_count"] += 1
                stats["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
                stats["recent_whales"].insert(0, {
                    "wallet": w_short,
                    "action": f"{side} {outcome}",
                    "title": title,
                    "usd": f"${usd:,.0f}",
                    "stats": f"{st['n']} صفقة (${st['vol']:,.0f})"
                })
                if len(stats["recent_whales"]) > 10:
                    stats["recent_whales"].pop()
        except Exception:
            continue

def background_monitor():
    global stats
    stats["status"] = "🟢 النظام يعمل بكفاءة تامة ويراقب الأسواق..."
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
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>Polymarket Pro Sentinel - عبد الرحمن</title>
        <meta http-equiv="refresh" content="15">
        <style>
            body { background: #0b0f19; color: #f8fafc; font-family: Tahoma, sans-serif; margin: 0; padding: 20px; }
            .container { max-width: 1100px; margin: auto; }
            header { text-align: center; padding: 20px; background: #1e293b; border-radius: 12px; border: 1px solid #334155; margin-bottom: 20px; }
            h1 { color: #38bdf8; margin: 0 0 10px 0; font-size: 24px; }
            .status { color: #34d399; font-weight: bold; font-size: 14px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 25px; }
            .card { background: #1e293b; padding: 20px; border-radius: 10px; border: 1px solid #334155; text-align: center; }
            .card h3 { margin: 0 0 10px 0; color: #94a3b8; font-size: 14px; }
            .card .val { font-size: 24px; font-weight: bold; color: #38bdf8; }
            section { background: #1e293b; padding: 20px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 20px; }
            h2 { color: #38bdf8; font-size: 18px; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-top: 0; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
            th, td { padding: 10px; text-align: right; border-bottom: 1px solid #334155; }
            th { color: #94a3b8; }
            a { color: #38bdf8; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .footer { text-align: center; color: #64748b; font-size: 12px; margin-top: 30px; }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🚀 Polymarket Pro Sentinel Dashboard</h1>
                <div class="status">{{ stats.status }}</div>
                <div style="color: #94a3b8; font-size: 12px; margin-top: 5px;">آخر تحديث: {{ stats.last_update }} (تحديث تلقائي كل 15 ثانية)</div>
            </header>

            <div class="grid">
                <div class="card">
                    <h3>فرص التحكيم المكتشفة</h3>
                    <div class="val" style="color: #34d399;">{{ stats.arb_count }}</div>
                </div>
                <div class="card">
                    <h3>صفقات الحيتان المرصودة</h3>
                    <div class="val" style="color: #f43f5e;">{{ stats.whale_count }}</div>
                </div>
                <div class="card">
                    <h3>المحافظ المتتبعة</h3>
                    <div class="val">{{ wallets_count }}</div>
                </div>
                <div class="card">
                    <h3>حالة الذاكرة (SEEN)</h3>
                    <div class="val" style="color: #fbbf24;">{{ seen_count }}</div>
                </div>
            </div>

            <section>
                <h2>🎯 أحدث فرص التحكيم (Arbitrage)</h2>
                {% if stats.recent_arbs %}
                <table>
                    <tr>
                        <th>السوق</th>
                        <th>المجموع</th>
                        <th>الربح التقديري</th>
                        <th>السيولة</th>
                        <th>الرابط</th>
                    </tr>
                    {% for item in stats.recent_arbs %}
                    <tr>
                        <td>{{ item.question }}</td>
                        <td style="direction: ltr;">{{ item.sum }}</td>
                        <td style="color: #34d399; font-weight: bold;">{{ item.profit }}</td>
                        <td>{{ item.liq }}</td>
                        <td><a href="{{ item.link }}" target="_blank">فتح السوق ↗</a></td>
                    </tr>
                    {% endfor %}
                </table>
                {% else %}
                <p style="color: #94a3b8; text-align: center;">جاري البحث عن فرص تحكيم مطابقة للشروط...</p>
                {% endif %}
            </section>

            <section>
                <h2>🐋 أحدث صفقات الحيتان والمحافظ الذكية</h2>
                {% if stats.recent_whales %}
                <table>
                    <tr>
                        <th>المحفظة</th>
                        <th>العملية</th>
                        <th>العنوان</th>
                        <th>حجم الصفقة</th>
                        <th>إحصائيات المحفظة</th>
                    </tr>
                    {% for item in stats.recent_whales %}
                    <tr>
                        <td style="font-family: monospace; color: #fbbf24;">{{ item.wallet }}</td>
                        <td>{{ item.action }}</td>
                        <td>{{ item.title }}</td>
                        <td style="color: #f43f5e; font-weight: bold;" style="direction: ltr;">{{ item.usd }}</td>
                        <td>{{ item.stats }}</td>
                    </tr>
                    {% endfor %}
                </table>
                {% else %}
                <p style="color: #94a3b8; text-align: center;">جاري رصد وتتبع صفقات الحيتان الكبرى...</p>
                {% endif %}
            </section>

            <div class="footer">
                تم التطوير خصخصيصاً لـ عبد الرحمن | Polymarket Pro Trading Sentinel 2026
            </div>
        </div>
    </body>
    </html>
    """, stats=stats, wallets_count=len(wallets), seen_count=len(SEEN))

if __name__ == "__main__":
    t = threading.Thread(target=background_monitor)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
