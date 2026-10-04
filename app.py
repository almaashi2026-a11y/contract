import os
import time
import html
import threading
import requests
from datetime import datetime
from collections import defaultdict
from flask import Flask, render_template_string

TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT = os.environ.get("TG_CHAT", "")
NETWORKS = os.environ.get("NETWORKS", "solana,base,eth,bsc").split(",")

MIN_BUY_USD = 2000             # الحد الأدنى لشراء الحوت الواحد
MIN_LIQ = 2000                 # سيولة مناسبة للتوكنات الناشئة
MAX_MC = 8000000               # قيمة سوقية منخفضة إلى متوسطة لضمان فرص الصعود المبكر
REFRESH = 15                   
CALL_GAP = 1.0

wallet_accumulation = defaultdict(lambda: {"tokens": set(), "total_usd": 0, "tx_count": 0})
alerted_accumulations = set()
recent_alerts = []             
_last = [0.0]
last_status = "Starting..."

web = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>Debot Smart Money & Early Accumulation Tracker</title>
    <meta http-equiv="refresh" content="10">
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: Tahoma, sans-serif; padding: 20px; margin: 0; }
        h1 { color: #58a6ff; text-align: center; margin-bottom: 5px; }
        .subtitle { text-align: center; color: #8b949e; margin-bottom: 25px; font-size: 0.95em; }
        .stats { background: #161b22; padding: 15px 20px; border-radius: 8px; margin-bottom: 25px; display: flex; justify-content: space-around; border: 1px solid #30363d; flex-wrap: wrap; gap: 10px; }
        .stats div { font-size: 1.05em; }
        .stats span { color: #3fb950; font-weight: bold; }
        table { width: 100%
        table { width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; border: 1px solid #30363d; }
        th, td { padding: 12px 15px; text-align: right; border-bottom: 1px solid #30363d; font-size: 0.9em; }
        th { background: #21262d; color: #58a6ff; }
        tr:hover { background: #1f242c; }
        a { color: #58a6ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .badge { background: #1f6feb33; color: #58a6ff; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; border: 1px solid #1f6feb66; }
        .copy-btn { background: #21262d; color: #f0883e; border: 1px solid #30363d; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-family: monospace; font-size: 0.9em; }
        .copy-btn:hover { background: #30363d; color: #ffa657; }
        .price { color: #3fb950; font-weight: bold; font-size: 1.05em; }
        #toast { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: #238636; color: #fff; padding: 10px 20px; border-radius: 6px; display: none; font-weight: bold; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
    </style>
</head>
<body>
    <h1>🎯 رادار تتبع تجمع المحافظ الكبرى (Early Whale Accumulation)</h1>
    <div class="subtitle">رصد التوجه المبكر للحيتان والسيولة الذكية قبل الصعود (تحديث تلقائي كل 10 ثوانٍ)</div>
    
    <div class="stats">
        <div>حالة الرادار: <span>{{ status }}</span></div>
        <div>إجمالي إشارات التراكم: <strong>{{ alerts|length }}</strong></div>
        <div>الشبكات المفعلة: <strong>{{ networks }}</strong></div>
    </div>
    
    <h2>📊 جدول التوجه المبكر للمحافظ الثقيلة:</h2>
    <table>
        <thead>
            <tr>
                <th>الوقت</th>
                <th>الشبكة</th>
                <th>التوكن</th>
                <th>حجم الشراء القوي</th>
                <th>السيولة</th>
                <th>المحفظة الذكية</th>
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
                <td>
                    <button class="copy-btn" onclick="copyText('{{ item.wallet }}', 'تم نسخ المحفظة!')" title="انقر لنسخ المحفظة">
                        {{ item.wallet[:6] }}...{{ item.wallet[-4:] }} 📋
                    </button>
                </td>
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
                <td colspan="8" style="text-align: center; color: #8b949e; padding: 30px;">جاري ترصد توجهات الحيتان ومحفظة التراكم المبكر... انتظر رصد أول إشارة.</td>
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
    return f"OK - {last_status} | Signals: {len(recent_alerts)}"

def tg(msg):
    print("[TELEGRAM ACCUMULATION ALERT]:", msg[:60])
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
    print("[*] Smart Money & Early Accumulation Tracker started.")
    tg("🎯 **رادار التوجه المبكر وتراكم الحيتان (Smart Money) بدأ العمل!**")
    
    while True:
        try:
            total_checked = 0
            for net in NETWORKS:
                last_status = f"فحص التوجه المبكر على شبكة {net.upper()}..."
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
                            
                            if usd >= MIN_BUY_USD and wallet and token:
                                # تتبع تراكم المحفظة
                                w_data = wallet_accumulation[wallet]
                                w_data["total_usd"] += usd
                                w_data["tx_count"] += 1
                                w_data["tokens"].add(token)
                                
                                # إذا كانت المحفظة تجمع في هذا التوكن أو قامت بضخ مبكر قوي ولم ننبه عنه بعد
                                key = (wallet, token)
                                if key not in alerted_accumulations:
                                    alerted_accumulations.add(key)
                                    
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
                                    if len(recent_alerts) > 50:
                                        recent_alerts.pop()
                                    
                                    msg = (
                                        f"🎯⚡ <b>رصد دخول مبكر لحوت / محفظة ذكية (Smart Money)</b>\n\n"
                                        f"🌐 الشبكة: {net.upper()}\n"
                                        f"🪙 التوكن: {html.escape(name)}\n"
                                        f"💰 حجم الشراء المبكر: <b>${usd:,.0f}</b>\n"
                                        f"💧 سيولة البول: ${liq:,.0f}\n\n"
                                        f"🔑 عقد التوكن (CA):\n<code>{token}</code>\n\n"
                                        f"👛 المحفظة المتراكمة:\n<code>{wallet}</code>\n\n"
                                        f"🤖 <a href='https://debots.io'>Debot</a> | 🫧 <a href='https://bubblemaps.io'>BubbleMaps</a> | 📈 <a href='https://dexscreener.com/{net}/{addr}'>DexScreener</a>"
                                    )
                                    tg(msg)
                                    break
            
            last_status = f"يعمل بكفاءة - تم فحص {total_checked} بول لتوجهات الحيتان."
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
