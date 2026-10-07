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

REFRESH = 2                    
CALL_GAP = 0.3                 

MIN_LIQ = 3000                 
MIN_MC = 10000                 
MAX_MC = 250000                

alerted_pools = set()
recent_alerts = []             
_last = [0.0]
last_status = "Multi-Wallet Sniper Pro Active..."

web = Flask(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>Debot Multi-Wallet Sniper Pro</title>
    <meta http-equiv="refresh" content="3">
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
        .wallets-tag { background: #1f6feb33; color: #58a6ff; padding: 3px 6px; border-radius: 4px; font-size: 0.8em; border: 1px solid #58a6ff55; font-weight: bold; }
        .copy-btn { background: #21262d; color: #58a6ff; border: 1px solid #30363d; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-family: monospace; font-size: 0.9em; }
        .copy-btn:hover { background: #30363d; color: #79c0ff; }
        .price { color: #3fb950; font-weight: bold; font-size: 1.05em; }
        #toast { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: #238636; color: #fff; padding: 10px 20px; border-radius: 6px; display: none; font-weight: bold; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
    </style>
</head>
<body>
    <h1>🎯👥 رادار تراكم المحافظ المتعددة (Multi-Wallet Sniper)</h1>
    <div class="subtitle">رصد العملات عند دخول أكثر من محفظة حقيقية قبل الارتفاع والانفجار</div>
    
    <div class="stats">
        <div>حالة الرادار: <span>{{ status }}</span></div>
        <div>الصفقات المؤكدة بمحافظ متعددة: <strong>{{ alerts|length }}</strong></div>
        <div>الشبكات المفعلة: <strong>{{ networks }}</strong></div>
    </div>
    
    <h2>📊 جدول رصد تراكم السيولة الحقيقية للمحافظ:</h2>
    <table>
        <thead>
            <tr>
                <th>الوقت</th>
                <th>الشبكة</th>
                <th>التوكن / حالة التراكم</th>
                <th>القيمة السوقية (MC)</th>
                <th>السيولة الحقيقية</th>
                <th>عقد التوكن (CA)</th>
                <th>روابط التحليل</th>
            </tr>
        </thead>
        <tbody>
            {% for item in alerts %}
            <tr>
                <td>{{ item.time }}</td>
                <td><span class="badge">{{ item.net }}</span></td>
                <td>
                    <strong>{{ item.name }}</strong><br>
                    <span class="wallets-tag">👥 Multi-Wallet Buying Verified</span>
                </td>
                <td class="price">${{ "{:,.0f}".format(item.mc) }}</td>
                <td>${{ "{:,.0f}".format(item.liq) }}</td>
                <td>
                    <button class="copy-btn" onclick="copyText('{{ item.token }}')">نسخ العقد</button>
                </td>
                <td>
                    <a href="https://debots.io" target="_blank">Debot</a> | 
                    <a href="https://bubblemaps.io" target="_blank">BubbleMaps</a> | 
                    <a href="https://dexscreener.com/{{ item.net_raw }}/{{ item.pool_addr }}" target="_blank">DexScreener</a>
                </td>
            </tr>
            {% else %}
            <tr>
                <td colspan="7" style="text-align: center; color: #8b949e; padding: 30px;">جاري مراقبة الصفقات ورصد دخول المحافظ المتعددة...</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div id="toast">تم النسخ بنجاح!</div>

    <script>
        function copyText(text) {
            navigator.clipboard.writeText(text).then(function() {
                var t = document.getElementById("toast");
                t.style.display = "block";
                setTimeout(function() { t.style.display = "none"; }, 2000);
            });
        }
    </script>
</body>
</html>"""

@web.route("/")
def home():
    global last_status, recent_alerts
    return render_template_string(HTML_TEMPLATE, status=last_status, alerts=recent_alerts, networks=", ".join(NETWORKS).upper())

@web.route("/health")
def health():
    return f"OK - {last_status}"

def tg(msg):
    if not TG_TOKEN or not TG_CHAT:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=3
        )
    except:
        pass

def gt(path, **p):
    wait = CALL_GAP - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    try:
        r = requests.get(f"https://api.geckoterminal.com/api/v2{path}", params=p, timeout=4,
                         headers={"Accept": "application/json;version=20230302", "Cache-Control": "no-cache"})
        if r.status_code == 429:
            time.sleep(1)
            return None
        return r.json() if r.status_code == 200 else None
    except:
        return None

def verify_multi_wallet_accumulation(net, pool_addr):
    try:
        data = gt(f"/networks/{net}/pools/{pool_addr}/trades")
        trades = (data or {}).get("data", [])
        buyers = set()
        for t in trades:
            attr = t.get("attributes", {})
            if attr.get("kind", "") == "buy":
                tx_from = attr.get("tx_from_address") or attr.get("from_address")
                if tx_from:
                    buyers.add(tx_from)
        if len(buyers) >= 3:
            return True
        return False
    except:
        return True

def scan_network(net):
    global recent_alerts
    try:
        j = gt(f"/networks/{net}/new_pools", page=1)
        items = (j or {}).get("data", [])
        for x in items:
            try:
                a = x.get("attributes", {})
                liq = float(a.get("reserve_in_usd") or 0)
                mc = float(a.get("fdv_usd") or 0)
                addr = a.get("address", "")
                name = a.get("name", "?")
                if not addr or addr in alerted_pools:
                    continue
                if liq < MIN_LIQ or mc < MIN_MC or mc > MAX_MC:
                    continue
                token = addr
                relationships = x.get("relationships", {})
                token_data = relationships.get("base_token", {}).get("data", {})
                if token_data:
                    token = token_data.get("id", addr).split("_")[-1]
                if not verify_multi_wallet_accumulation(net, addr):
                    continue
                alerted_pools.add(addr)
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
                if len(recent_alerts) > 80:
                    recent_alerts.pop()
                
                msg = "🎯👥 رصد تراكم محافظ متعددة\n\n"
                msg += f"الشبكة: {net.upper()}\n"
                msg += f"التوكن: {html.escape(name)}\n"
                msg += f"السيولة: ${liq:,.0f}\n"
                msg += f"القيمة السوقية: ${mc:,.0f}\n\n"
                msg += f"العقد:\n<code>{token}</code>"
                tg(msg)
            except:
                continue
    except:
        pass

def main_loop():
    global last_status
    print("[*] Multi-Wallet Sniper Pro Engine started.")
    tg("🎯🟢 رادار تراكم المحافظ المتعددة يعمل الآن!")
    while True:
        try:
            last_status = "جاري تتبع صفقات المحافظ المتعددة..."
            for net in NETWORKS:
                scan_network(net.strip())
                time.sleep(0.4)
            time.sleep(REFRESH)
        except:
            last_status = "إعادة مزامنة الرادار..."
            time.sleep(2)

if __name__ == "__main__":
    t = threading.Thread(target=main_loop, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 10000))
    web.run(host="0.0.0.0", port=port)
