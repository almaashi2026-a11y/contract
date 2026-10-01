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

# مصادر رصد عملات الميم والسيولة (مثل DexScreener / Pump / APIs المخصصة)
DEX_API = "https://api.dexscreener.com/latest/dex/tokens/"
TRENDING_DEX = "https://api.dexscreener.com/latest/dex/trending/tokens"

MIN_LIQ_MEME = 5000    # حد أدنى للسيولة القوية لعملات الميم ($)
MIN_VOL_MEME = 10000   # حد أدنى لحجم التداول القوي ($)
ALERT_MIN_USD = 50     # الحد الأدنى لقيمة الصفقة المرصودة

# ذاكرة ذكية لمنع تكرار التنبيهات
SEEN = OrderedDict()
MAX_SEEN_SIZE = 20000

# سجلات العرض في لوحة التحكم الخاصة بعملات الميم
stats = {
    "status": "🟢 نظام صيد ومراقبة عملات الميم وحيتانها يعمل بنجاح...",
    "meme_count": 0,
    "whale_alerts": 0,
    "last_update": "لم يتم التحديث بعد",
    "recent_memes": []
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

def get(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"API Error [{url}]:", e)
        return {}

def scan_memecoins():
    global stats
    data = get(TRENDING_DEX)
    pairs = data.get("pairs", [])
    if not isinstance(pairs, list):
        return

    for p in pairs:
        try:
            # التركيز على شبكات الميم الكبرى مثل Solana, Base, Ethereum
            chain = p.get("chainId", "")
            if chain not in ["solana", "base", "ethereum"]:
                continue
                
            liq = float(p.get("liquidity", {}).get("usd", 0) or 0)
            vol = float(p.get("volume", {}).get("h24", 0) or 0)
            
            if liq < MIN_LIQ_MEME or vol < MIN_VOL_MEME:
                continue
                
            token_addr = p.get("baseToken", {}).get("address", "")
            symbol = p.get("baseToken", {}).get("symbol", "UNKNOWN")
            name = p.get("baseToken", {}).get("name", "Unknown Meme")
            price_change = float(p.get("priceChange", {}).get("h1", 0) or 0)
            
            if price_change <= 3.0: # نبحث عن العملات التي تبدأ بالانفجار والزخم (أكثر من 3% في ساعة)
                continue
                
            key = ("meme_pump", token_addr, round(price_change, 1))
            if add_to_seen(key):
                continue
                
            dex_url = p.get("url", "https://dexscreener.com")
            
            msg = (
                f"🐸🚀 **[انفجار عملة ميم جديدة - MEME ALERT]**\n"
                f"🪙 **العملة:** `{symbol}` ({name})\n"
                f"🌐 **الشبكة:** `{chain.upper()}`\n"
                f"🔥 **زخم (ساعة):** `+{price_change}%`\n"
                f"💧 **السيولة القوية:** `${liq:,.0f}`\n"
                f"📊 **حجم التداول:** `${vol:,.0f}`\n"
                f"🔗 [رابط DexScreener]({dex_url})"
            )
            tg(msg)
            
            stats["meme_count"] += 1
            stats["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
            stats["recent_memes"].insert(0, {
                "symbol": symbol,
                "name": name,
                "chain": chain.upper(),
                "change": f"+{price_change}%",
                "liq": f"${liq:,.0f}",
                "vol": f"${vol:,.0f}",
                "link": dex_url
            })
            if len(stats["recent_memes"]) > 15:
                stats["recent_memes"].pop()
        except Exception:
            continue

def background_monitor():
    global stats
    tg("✅ **Meme Sniper Bot** تم تفعيل نظام رصد عملات الميم والسيولة بنجاح...")
    while True:
        try:
            scan_memecoins()
        except Exception as e:
            print("Monitor Loop Error:", e)
        time.sleep(30) # فحص دوري كل 30 ثانية لعملات الميم

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>Meme Sniper Dashboard - عبد الرحمن</title>
        <meta http-equiv="refresh" content="15">
        <style>
            body { background: #0b0f19; color: #f8fafc; font-family: Tahoma, sans-serif; margin: 0; padding: 20px; }
            .container { max-width: 1100px; margin: auto; }
            header { text-align: center; padding: 20px; background: #1e293b; border-radius: 12px; border: 1px solid #334155; margin-bottom: 20px; }
            h1 { color: #f43f5e; margin: 0 0 10px 0; font-size: 24px; }
            .status { color: #34d399; font-weight: bold; font-size: 14px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 15px; margin-bottom: 25px; }
            .card { background: #1e293b; padding: 20px; border-radius: 10px; border: 1px solid #334155; text-align: center; }
            .card h3 { margin: 0 0 10px 0; color: #94a3b8; font-size: 14px; }
            .card .val { font-size: 24px; font-weight: bold; color: #38bdf8; }
            section { background: #1e293b; padding: 20px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 20px; }
            h2 { color: #f43f5e; font-size: 18px; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-top: 0; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
            th, td { padding: 10px; text-align: right; border-bottom: 1px solid #334155; }
            th { color: #94a3b8; }
            .token-name { direction: ltr; text-align: right; unicode-bidi: plaintext; font-weight: bold; color: #f8fafc; }
            a { color: #38bdf8; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .footer { text-align: center; color: #64748b; font-size: 12px; margin-top: 30px; }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🐸🔥 Meme Sniper Sentinel (رصد انفجارات عملات الميم)</h1>
                <div class="status">{{ stats.status }}</div>
                <div style="color: #94a3b8; font-size: 12px; margin-top: 5px;">آخر تحديث: {{ stats.last_update }} (تحديث تلقائي كل 15 ثانية)</div>
            </header>

            <div class="grid">
                <div class="card">
                    <h3>فرص الميم المرصودة</h3>
                    <div class="val" style="color: #34d399;">{{ stats.meme_count }}</div>
                </div>
                <div class="card">
                    <h3>حالة الذاكرة (SEEN)</h3>
                    <div class="val" style="color: #fbbf24;">{{ seen_count }}</div>
                </div>
            </div>

            <section>
                <h2>🚀 أحدث عملات الميم المكتشفة بالسيولة القوية</h2>
                {% if stats.recent_memes %}
                <table>
                    <tr>
                        <th>العملة / الرمز</th>
                        <th>الشبكة</th>
                        <th>الزخم (ساعة)</th>
                        <th>السيولة القوية</th>
                        <th>حجم التداول</th>
                        <th>الرابط</th>
                    </tr>
                    {% for item in stats.recent_memes %}
                    <tr>
                        <td class="token-name"><span style="color: #f43f5e; font-weight: bold;">{{ item.symbol }}</span> ({{ item.name }})</td>
                        <td style="font-weight: bold; color: #fbbf24;">{{ item.chain }}</td>
                        <td style="color: #34d399; font-weight: bold; direction: ltr;">{{ item.change }}</td>
                        <td style="color: #38bdf8; font-weight: bold; direction: ltr;">{{ item.liq }}</td>
                        <td style="direction: ltr;">{{ item.vol }}</td>
                        <td><a href="{{ item.link }}" target="_blank">DexScreener ↗</a></td>
                    </tr>
                    {% endfor %}
                </table>
                {% else %}
                <p style="color: #94a3b8; text-align: center;">جاري البحث عن عملات ميم تنفجر بالسيولة الآن...</p>
                {% endif %}
            </section>

            <div class="footer">
                تم التطوير خصيصاً لـ عبد الرحمن | Meme Sniper Sentinel 2026
            </div>
        </div>
    </body>
    </html>
    """, stats=stats, seen_count=len(SEEN))

if __name__ == "__main__":
    t = threading.Thread(target=background_monitor)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
