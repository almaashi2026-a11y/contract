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
MIN_MC = 8000                  
MAX_MC = 350000                

alerted_pools = set()
recent_alerts = []             
_last = [0.0]
last_status = "Wave Rider Momentum Engine Active..."

web = Flask(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>Debot Wave Rider Momentum Pro</title>
    <meta http-equiv="refresh" content="3">
    <style>
        body { background-color: #06080c; color: #e6edf3; font-family: Tahoma, sans-serif; padding: 20px; margin: 0; }
        h1 { color: #58a6ff; text-align: center; margin-bottom: 5px; }
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
        .badge { background: #58a6ff33; color: #58a6ff; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; border: 1px solid #58a6ff66; }
        .wave-tag { background: #23863633; color: #3fb950; padding: 3px 6px; border-radius: 4px; font-size: 0.8em; border: 1px solid #3fb95055; font-weight: bold; }
        .copy-btn { background: #21262d; color: #58a6ff; border: 1px solid #30363d; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-family: monospace; font-size: 0.9em; }
        .copy-btn:hover { background: #30363d; color: #79c0ff; }
        .price { color: #3fb950; font-weight: bold; font-size: 1.05em; }
        #toast { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: #238636; color: #fff; padding: 10px 20px; border-radius: 6px; display: none; font-weight: bold; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
    </style>
</head>
<body>
    <h1>🚀🌊 رادار صيد الموجة والزخم الصاعد (Wave Rider Pro)</h1>
    <div class="subtitle">رصد اختراق السيولة وتأكيد ضغط الشراء العنيف لاستمرار الموجة الصاعدة</div>
    
    <div class="stats">
        <div>حالة الرادار: <span>{{ status }}</span></div>
        <div>الموجات المؤكدة: <strong>{{ alerts|length }}</strong></div>
        <div>الشبكات المفعلة: <strong>{{ networks }}</strong></div>
    </div>
    
    <h2>📊 جدول رصد الموجات الصاعدة ذات الزخم العالي:</h2>
    <table>
        <thead>
            <tr>
                <th>الوقت</th>
                <th>الشبكة</th>
                <th>التوكن / قوة الموجة</th>
                <th>القيمة السوقية (MC)</th>
                <th>السيولة</th>
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
                    <span class="wave-tag">🌊 Momentum Surge Verified</span>
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
                <td colspan="7" style="text-align: center; color: #8b949e; padding: 30px;">جاري ترصد موجات السيولة والزخم العنيف...</td>
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

def verify_wave_momentum(net, pool_addr):
    """
    فحص عزم الموجة (Wave Momentum & Buy Pressure):
    التحقق من أن حجم صفقات الشراء يغلب تماماً على البيع وأن هناك تدفقاً نقدياً تصاعدياً.
    """
    try:
        data = gt(f"/networks/{net}/pools/{pool_addr}/trades")
        trades = (data or {}).get("data", [])
        
        buy_count = 0
        sell_count = 0
        buyers = set()
        
        for t in trades:
            attr = t.get("attributes", {})
            kind = attr.get("kind", "")
            tx_from = attr.get("tx_from_address") or attr.get("from_address")
            
            if kind == "buy":
                buy_count += 1
                if tx_from:
                    buyers.add(tx_from)
            elif kind == "sell":
                sell_count += 1
                
        # شروط صيد الموجة: وجود عدد كافٍ من المشترين مع هيمنة واضحة لعمليات الشراء فوق البيع
        if len(buyers) >= 3 and buy_count > sell_count * 2:
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
                mc = float(a.get("
