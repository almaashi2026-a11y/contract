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

REFRESH = 0.5                  
CALL_GAP = 0.01                

# شروط الأمان والبمب اللحظي
MIN_LIQ = 1000                 # الحد الأدنى للسيولة (بالدولار) لضمان عدم سحبها أو تفريغها بسهولة
MIN_MC = 5000                  # الحد الأدنى للقيمة السوقية المبدئية
MAX_MC = 500000                # أقصى قيمة سوقية لضمان أن العملة في بدايتها وتحتمل البمب القوي

alerted_pools = set()
recent_alerts = []             
_last = [0.0]
last_status = "Initializing Safe Pump Sniper..."

web = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>Debot Safe Pump 1s Sniper</title>
    <meta http-equiv="refresh" content="1">
    <style>
        body { background-color: #06080c; color: #e6edf3; font-family: Tahoma, sans-serif; padding: 20px; margin: 0; }
        h1 { color: #3fb950; text-align: center; margin-bottom: 5px; }
        .subtitle { text-align: center; color: #8b949e; margin-bottom: 25px; font-size: 0.95em; }
        .stats { background: #161b22; padding: 15px 20px; border-radius: 8px; margin-bottom: 25px; display: flex; justify-content: space-around; border: 1px solid #30363d; flex-wrap: wrap; gap: 10px; }
        .stats div { font-size: 1.05em; }
        .stats span { color: #3fb950; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; border: 1px solid #30363d; }
        th, td { padding: 12px 15px; text-align: right; border-bottom: 1px solid #30363d; font-size: 0.9em; }
        th { background: #21262d; color: #58a6ff; }
        tr:hover { background: #1f242c; }
        a { color: #58a6ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .badge { background: #3fb95033; color: #3fb950; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; border: 1px solid #3fb95066; }
        .copy-btn { background: #21262d; color: #58a6ff; border: 1px solid #30363d; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-family: monospace; font-size: 0.9em; }
        .copy-btn:hover { background: #30363d; color: #79c0ff; }
        .price { color: #3fb950; font-weight: bold; font-size: 1.05em; }
        #toast { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: #238636; color: #fff; padding: 10px 20px; border-radius: 6px; display: none; font-weight: bold; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
    </style>
</head>
<body>
    <h1>🛡️🚀 رادار العملات الآمنة والبمبات اللحظية (Safe 1s Sniper)</h1>
    <div class="subtitle">فلترة متقدمة لاستبعاد العملات الضعيفة ورصد الانطلاقات الآمنة في أول ثانية</div>
    
    <div class="stats">
        <div>حالة الرادار: <span>{{ status }}</span></div>
        <div>إجمالي العملات الآمنة: <strong>{{ alerts|length }}</strong></div>
        <div>الشبكات المفعلة: <strong>{{ networks }}</strong></div>
    </div>
    
    <h2>📊 جدول رصد البمبات الآمنة:</h2>
    <table>
        <thead>
            <tr>
                <th>الوقت</th>
                <th>الشبكة</th>
                <th>التوكن / البول</th>
                <th>القيمة السوقية (MC)</th>
                <th>السيولة الآمنة</th>
                <th>عقد التوكن (CA)</th>
                <th>أدوات الفحص والتحليل</th>
            </tr>
        </thead>
        <tbody>
            {% for item in alerts %}
            <tr>
                <td>{{ item.time }}</td>
                <td><span class="badge">{{ item.net }}</span></td>
                <td><strong>{{ item.name }}</strong></td>
                <td class="price">${{ "{:,.0f}".format(item.mc) }}</td>
                <td>${{ "{:,.0f}".format(item.liq) }}</td>
                <td>
                    <button class="copy-btn" onclick="copyText('{{ item.token }}', 'تم نسخ العقد!')" title="انقر لنسخ العقد">
                        {{ item.token[:6] }}...{{ item.token[-4:] }} 📋
                    </button>
                </td>
                <td>
                    <a href="https://debots.io" target="_blank">Debot</a> | 
                    <a href="https://bubblemaps.io" target="_blank">BubbleMaps</a> | 
                    <a href="https://dexscreener.com/{{ item.net_raw }}/{{ item.pool_addr }}" target="_blank">DexScreener</a>
                </td>
            </tr>
            {% else %}
            <tr>
                <td colspan="7" style="text-align: center; color: #8b949e; padding: 30px;">جاري ترقب العملات الآمنة ذات البمب القوي في أول ثانية...</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div id="toast">تم النسخ بنجاح!</div>

    <script>
        function copyText(text, message) {
            navigator.clipboard.writeText(text).then(function() {
                showToast(message);
            }, function(err) {
                console.error('فشل النسخ: ', err);
            });
        }

        function showToast(msg) {
            var toast = document.getElementById("toast");
            toast.innerText = msg;
            toast.style.display = "block";
            setTimeout(function() {
                toast.style.display = "none";
            }, 2000);
        }
    </script>
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
    return f"OK - {last_status} | Alerts: {len(recent_alerts)}"

def tg(msg):
    print("[TELEGRAM SAFE ALERT]:", msg[:60])
    if not TG_TOKEN or not TG_CHAT:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=2
        )
    except Exception as e:
        print("[!] Telegram error:", e)

def gt(path, **p):
    wait = CALL_GAP - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    try:
        r = requests.get(f"https://api.geckoterminal.com/api/v2{path}", params=p, timeout=2.5,
                         headers={
                             "Accept": "application/json;version=20230302",
                             "Cache-Control": "no-cache, no-store, must-revalidate",
                             "Pragma": "no-cache"
                         })
        if r.status_code == 429:
            time.sleep(0.2)
            return None
        return r.json()
    except Exception as e:
        return None

def scan_network(net):
    global recent_alerts
    try:
        j = gt(f"/networks/{net}/new_pools", page=1)
        items = (j or {}).get("data", [])
        
        for x in items:
            a = x["attributes"]
            liq = float(a.get("reserve_in_usd") or 0)
            mc = float(a.get("fdv_usd") or 0)
            addr = a["address"]
            name = a.get("name", "?")
            
            if addr in alerted_pools:
                continue
            
            # تطبيق فلتر الأمان والقوة اللحظية:
            # 1. التأكد أن السيولة أكبر من الحد الأدنى (تمنع العملات الفارغة أو المسحوبة)
            # 2. التأكد أن القيمة السوقية ضمن النطاق الآمن للانفجار (البمب)
            if liq < MIN_LIQ or mc < MIN_MC or mc > MAX_MC:
                continue
                
            alerted_pools.add(addr)
            
            token = addr
            try:
                relationships = x.get("relationships", {})
                token_data = relationships.get("base_token", {}).get("data", {})
                if token_data:
                    token = token_data.get("id", addr).split("_")[-1]
            except:
                pass

            alert_item = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "net": net.upper(),
                "net_raw": net,
                "name": name,
                "mc": mc,
                "liq": liq,
                "token": token,
                "pool_addr": addr
            }
            
            recent_alerts.insert(0, alert_item)
            if len(recent_alerts) > 100:
                recent_alerts.pop()
            
            msg = (
                f"🛡️🚀🔥 <b>رصد بمب آمن (Safe 1s Sniper)</b>\n\n"
                f"🌐 الشبكة: {net.upper()}\n"
                f"🪙 التوكن: {html.escape(name)}\n"
                f"💧 السيولة الآمنة: ${liq:,.0f}\n"
                f"📊 القيمة السوقية: ${mc:,.0f}\n\n"
                f"🔑 عقد التوكن (CA):\n<code>{token}</code>\n\n"
                f"🤖 <a href='https://debots.io'>Debot</a> | 🫧 <a href='https://bubblemaps.io'>BubbleMaps</a> | 📈 <a href='https://dexscreener.com/{net}/{addr}'>DexScreener</a>"
            )
            tg(msg)
    except Exception as e:
        pass

def main_loop():
    global last_status
    print("[*] Safe Pump Sniper Engine started.")
    tg("🛡️🟢 **رادار العملات الآمنة والبمبات اللحظية بدأ العمل!**")
    
    while True:
        try:
            last_status = "جاري فحص وبفلترة السيولة الآمنة..."
            
            threads = []
            for net in NETWORKS:
                t = threading.Thread(target=scan_network, args=(net,))
                threads.append(t)
                t.start()
                
            for t in threads:
                t.join()
                
            time.sleep(REFRESH)
            
        except Exception as e:
            last_status = "إعادة ضبط الفلتر..."
            time.sleep(0.2)

if __name__ == "__main__":
    t = threading.Thread(target=main_loop, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 10000))
    web.run(host="0.0.0.0", port=port)
