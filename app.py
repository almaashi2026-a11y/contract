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

# استخدام واجهات تتبع السيفقات والتوكنات الحية لشبكات الميم
TRENDING_URL = "https://api.dexscreener.com/latest/dex/trending/tokens"
LATEST_PROFILES_URL = "https://api.dexscreener.com/token-profiles/latest/v1"

MIN_LIQ = 8000       # الحد الأدنى للسيولة القوية ($)
MIN_VOL = 15000      # الحد الأدنى لحجم التداول ($)

# ذاكرة ذكية لمنع تكرار التنبيهات
SEEN = OrderedDict()
MAX_SEEN_SIZE = 20000

# سجلات العرض في لوحة التحكم
stats = {
    "status": "🟢 نظام صيد محافظ النخبة والعملات المبكرة يعمل بكفاءة...",
    "alerts_count": 0,
    "last_update": "لم يتم التحديث بعد",
    "recent_snipes": []
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
        return []

def scan_early_memes():
    global stats
    data = get(TRENDING_URL)
    pairs = data.get("pairs", [])
    if not isinstance(pairs, list):
        return

    for p in pairs:
        try:
            chain = p.get("chainId", "")
            if chain not in ["solana", "base", "ethereum"]:
                continue
                
            liq = float(p.get("liquidity", {}).get("usd", 0) or 0)
            vol = float(p.get("volume", {}).get("h24", 0) or 0)
            
            if liq < MIN_LIQ or vol < MIN_VOL:
                continue
                
            token_addr = p.get("baseToken", {}).get("address", "")
            symbol = p.get("baseToken", {}).get("symbol", "UNKNOWN")
            name = p.get("baseToken", {}).get("name", "Unknown")
            price_change = float(p.get("priceChange", {}).get("h5m", 0) or 0) # التركيز على الزخم خلال 5 دقائق الأخيرة (صيد مبكر جداً)
            
            if price_change < 1.0: # نبحث عن العملات التي تبدأ بالحركة للتو
                continue
                
            key = ("snipe", token_addr)
            if add_to_seen(key):
                continue
                
            dex_url = p.get("url", "https://dexscreener.com")
            
            msg = (
                f"🎯🔥 **[صيد مبكر - عملة ميم جديدة بالسيولة]**\n"
                f"🪙 **العملة:** `{symbol}` ({name})\n"
                f"🌐 **الشبكة:** `{chain.upper()}`\n"
                f"🚀 **زخم (5 دقائق):** `+{price_change}%`\n"
                f"💧 **السيولة القوية:** `${liq:,.0f}`\n"
                f"📊 **حجم التداول:** `${vol:,.0f}`\n"
                f"🔗 [رابط الشاهد / DexScreener]({dex_url})\n"
                f"📋 **العنوان:** `{token_addr}`"
            )
            tg(msg)
            
            stats["alerts_count"] += 1
            stats["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
            stats["recent_snipes"].insert(0, {
                "symbol": symbol,
                "name": name,
                "chain": chain.upper(),
                "change": f"+{price_change}%",
                "liq": f"${liq:,.0f}",
                "address": token_addr,
                "link": dex_url
            })
            if len(stats["recent_snipes"]) > 15:
                stats["recent_snipes"].pop()
        except Exception:
            continue

def background_monitor():
    global stats
    tg("✅ **Meme Early Sniper** تم تفعيل نظام رصد الصفقات المبكرة والسيولة القوية بنجاح...")
    while True:
        try:
            scan_early_memes()
        except Exception as e:
            print("Monitor Loop Error:", e)
        time.sleep(20)

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>Early Meme Sniper - عبد الرحمن</title>
        <meta http-equiv="refresh" content="15">
        <style>
            body { background: #0b0f19; color: #f8fafc; font-family: Tahoma, sans-serif; margin: 0; padding: 20px; }
            .container { max-width: 1100px; margin: auto; }
            header { text-align: center; padding: 20px; background: #1e293b; border-radius: 12px; border: 1px solid #334155; margin-bottom: 20px; }
            h1 { color: #38bdf8; margin: 0 0 10px 0; font-size: 24px; }
            .status { color: #34d399; font-weight: bold; font-size: 14px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 15px; margin-bottom: 25px; }
            .card { background: #1e293b; padding: 20px; border-radius: 10px; border: 1px solid #334155; text-align: center; }
            .card h3 { margin: 0 0 10px 0; color: #94a3b8; font-size: 14px; }
            .card .val { font-size: 24px; font-weight: bold; color: #38bdf8; }
            section { background: #1e293b; padding: 20px; border-radius: 10px; border: 1px solid #334155; margin-bottom: 20px; }
            h2 { color: #38bdf8; font-size: 18px; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-top: 0; }
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
                <h1>🎯 Meme Early Sniper (رصد الصفقات المبكرة والسيولة القوية)</h1>
                <div class="status">{{ stats.status }}</div>
                <div style="color: #94a3b8; font-size: 12px; margin-top: 5px;">آخر تحديث: {{ stats.last_update }} (تحديث تلقائي كل 15 ثانية)</div>
            </header>

            <div class="grid">
                <div class="card">
                    <h3>العملات المرصودة (الصيد المبكر)</h3>
                    <div class="val" style="color: #34d399;">{{ stats.alerts_count }}</div>
                </div>
                <div class="card">
                    <h3>حالة الذاكرة (SEEN)</h3>
                    <div class="val" style="color: #fbbf24;">{{ seen_count }}</div>
                </div>
            </div>

            <section>
                <h2>🚀 أحدث عملات الميم المكتكتشفة في بدايتها بالسيولة القوية</h2>
                {% if stats.recent_snipes %}
                <table>
                    <tr>
                        <th>العملة / الرمز</th>
                        <th>الشبكة</th>
                        <th>زخم 5 دقائق</th>
                        <th>السيولة القوية</th>
                        <th>العنوان (Contract)</th>
                        <th>الرابط</th>
                    </tr>
                    {% for item in stats.recent_snipes %}
                    <tr>
                        <td class="token-name"><span style="color: #38bdf8; font-weight: bold;">{{ item.symbol }}</span> ({{ item.name }})</td>
                        <td style="font-weight: bold; color: #fbbf24;">{{ item.chain }}</td>
                        <td style="color: #34d399; font-weight: bold; direction: ltr;">{{ item.change }}</td>
                        <td style="color: #f43f5e; font-weight: bold; direction: ltr;">{{ item.liq }}</td>
                        <td style="font-family: monospace; font-size: 11px; direction: ltr;">{{ item.address[:8] }}...{{ item.address[-6:] }}</td>
                        <td><a href="{{ item.link }}" target="_blank">DexScreener ↗</a></td>
                    </tr>
                    {% endfor %}
                </table>
                {% else %}
                <p style="color: #94a3b8; text-align: center;">جاري البحث عن العملات فور ظهورها واشتعال السيولة عليها...</p>
                {% endif %}
            </section>

            <div class="footer">
                تم التطوير خصيصاً لـ عبد الرحمن | Meme Early Sniper 2026
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
