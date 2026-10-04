import os
import time
import html
import threading
import requests
from datetime import datetime
from flask import Flask, render_template_string

TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT = os.environ.get("TG_CHAT", "")
NETWORKS = os.environ.get("NETWORKS", "solana,base,eth,bsc").split(",")

MIN_BUY_USD = 10               # الحد الأدنى لشراء المحفظة لإطلاق التنبيه
MIN_LIQ = 500                  
MAX_MC = 10000000              
REFRESH = 15                   
CALL_GAP = 1.0

alerted = set()
recent_alerts = []             # تخزين الصفقات والنتائج لعرضها مباشرة على الصفحة
_last = [0.0]
last_status = "Starting..."

web = Flask(__name__)

# قالب صفحة الويب الاحترافية لعرض النتائج والتفاصيل مباشرة
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>Debot Live Wallet Tracker - لوحة النتائج</title>
    <meta http-equiv="refresh" content="10">
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: Tahoma, sans-serif; padding: 20px; margin: 0; }
        h1 { color: #58a6ff; text-align: center; margin-bottom: 5px; }
        .subtitle { text-align: center; color: #8b949e; margin-bottom: 25px; font-size: 0.95em; }
        .stats { background: #161b22; padding: 15px 20px; border-radius: 8px; margin-bottom: 25px; display: flex; justify-content: space-around; border: 1px solid #30363d; }
        .stats div { font-size: 1.05em; }
        .stats span { color: #3fb950; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; border: 1px solid #30363d; }
        th, td { padding: 12px 15px; text-align: right; border-bottom: 1px solid #30363d; font-size: 0.9em; }
        th { background: #21262d; color: #58a6ff; }
        tr:hover { background: #1f242c; }
        a { color: #58a6ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .badge { background: #1f6feb33; color: #58a6ff; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; border: 1px solid #1f6feb66; }
        code { background: #0d1117; padding: 2px 6px; border-radius: 4px; color: #f0883e; font-family: monospace; }
        .price { color: #3fb950; font-weight: bold; }
    </style>
</head>
<body>
    <h1>🚀 لوحة رادار Debot لتتبع المحافظ والصفقات</h1>
    <div class="subtitle">تحديث تلقائي مباشر للصفحة كل 10 ثوانٍ</div>
    
    <div class="stats">
        <div>حالة الرادار: <span>{{ status }}</span></div>
        <div>إجمالي الصفقات المرصودة: <strong>{{ alerts|length }}</strong></div>
        <div>الشبكات المفعلة: <strong>{{ networks }}</strong></div>
    </div>
    
    <h2>📊 جدول الصفقات والمحافظ اللحظية:</h2>
    <table>
        <thead>
            <tr>
                <th>الوقت</th>
                <th>الشبكة</th>
                <th>التوكن</th>
                <th>حجم الشراء</th>
                <th>السيولة</th>
                <th>المحفظة</th>
                <th>العقد (CA)</th>
                <th>أدوات الفحص والتحليل</th>
            </tr>
        </thead>
        <tbody>
            {% for item in alerts %}
            <tr>
                <td>{{ item.time }}</td>
                <td><span class="badge">{{ item.net }}</span></td>
                <td><strong>{{ item.name }}</strong></td>
                <td class="price">${{ "{:,.0f}".format(item.usd) }}</td>
                <td>${{ "{:,.0f}".format(item.liq) }}</td>
                <td><code>{{ item.wallet[:6] }}...{{ item.wallet[-4:] }}</code></td>
                <td><code>{{ item.token[:6] }}...{{ item.token[-4:] }}</code></td>
                <td>
                    <a href="https://debots.io" target="_blank">Debot</a> | 
                    <a href="https://bubblemaps.io" target="_blank">BubbleMaps</a> | 
                    <a href="https://dexscreener.com/{{ item.net_raw }}/{{ item.pool_addr }}" target="_blank">DexScreener</a>
                </td>
            </tr>
            {% else %}
            <tr>
                <td colspan="8" style="text-align: center; color: #8b949e; padding: 30px;">جاري فحص البولات والشبكات وسيتم عرض النتائج هنا فور رصد أول صفقة... انتظر قليلاً.</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

@web.route("/")
def home():
    global last_status, recent_alerts
    return render_template_string(
        HTML_TEMPLATE, 
        status=last_status, 
        alerts=recent_alerts, 
        networks=", ".join(NETWORKS).upper()
    )

@web.route("/health")
def health():
    return f"OK - {last_status} | Alerts count: {len(recent_alerts)}"

def tg(msg):
    print("[TELEGRAM ALERT]:", msg[:60])
    if not TG_TOKEN or not TG_CHAT:
        print("[!] Telegram credentials missing!")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        print("[!] Telegram error:", e)

def gt(path, **p):
    wait = CALL_GAP - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    try:
        r = requests.get(f"https://api.geckoterminal.com/api/v2{path}", params=p, timeout=10,
                         headers={"Accept": "application/json;version=20230302"})
        if r.status_code == 429:
            time.sleep(10)
            return None
        return r.json()
    except Exception as e:
        print("[!] API Error:", e)
        return None

def main_loop():
    global last_status, recent_alerts
    print("[*] Debot Dashboard & Tracker started.")
    tg("⚡ **رادار Debot ولوحة التحكم المباشرة بدآ العمل بنجاح!**")
    
    while True:
        try:
            total_checked = 0
            for net in NETWORKS:
                last_status = f"جاري فحص شبكة {net.upper()}..."
                j = gt(f"/networks/{net}/trending_pools")
                items = (j or {}).get("data", [])
                
                for x in items:
                    a = x["attributes"]
                    liq = float(a.get("reserve_in_usd") or 0)
                    mc = float(a.get("fdv_usd") or 0)
                    
                    if liq < MIN_LIQ or (0 < mc > MAX_MC):
                        continue
                        
                    addr = a["address"]
                    name = a.get("name", "?")
                    total_checked += 1
                    
                    trades_j = gt(f"/networks/{net}/pools/{addr}/trades")
                    trades = (trades_j or {}).get("data", [])
                    
                    for t in trades:
                        ta = t["attributes"]
                        if ta.get("kind") == "buy":
                            usd = float(ta.get("volume_in_usd") or 0)
                            token = ta.get("to_token_address")
                            wallet = ta.get("tx_from_address")
                            
                            if usd >= MIN_BUY_USD and wallet and (wallet, token) not in alerted:
                                alerted.add((wallet, token))
                                
                                # إضافة النتيجة إلى قائمة لوحة التحكم المباشرة
                                alert_item = {
                                    "time": datetime.now().strftime("%H:%M:%S"),
                                    "net": net.upper(),
                                    "net_raw": net,
                                    "name": name,
                                    "usd": usd,
                                    "liq": liq,
                                    "wallet": wallet,
                                    "token": token,
                                    "pool_addr": addr
                                }
                                recent_alerts.insert(0, alert_item)
                                if len(recent_alerts) > 50:  # الاحتفاظ بأحدث 50 نتيجة فقط
                                    recent_alerts.pop()
                                
                                # إرسال التنبيه إلى تليجرام
                                msg = (
                                    f"🚨👛 <b>رصد شراء محفظة جديدة (Debot Tracker)</b>\n\n"
                                    f"🌐 الشبكة: {net.upper()}\n"
                                    f"🪙 التوكن: {html.escape(name)}\n"
                                    f"💰 حجم شراء المحفظة: ${usd:,.0f}\n"
                                    f"💧 السيولة: ${liq:,.0f}\n\n"
                                    f"🔑 عقد التوكن (CA):\n<code>{token}</code>\n\n"
                                    f"👛 عنوان المحفظة:\n<code>{wallet}</code>\n\n"
                                    f"🤖 <a href='https://debots.io'>Debot</a> | 🫧 <a href='https://bubblemaps.io'>BubbleMaps</a> | 📈 <a href='https://dexscreener.com/{net}/{addr}'>DexScreener</a>"
                                )
                                tg(msg)
                                break
            
            last_status = f"يعمل بنجاح - تم فحص {total_checked} بول نشط."
            time.sleep(REFRESH)
            
        except Exception as e:
            last_status = f"خطأ مؤقت: {str(e)}"
            print("[!] Loop error:", e)
            time.sleep(10)

if __name__ == "__main__":
    t = threading.Thread(target=main_loop, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 10000))
    web.run(host="0.0.0.0", port=port)
