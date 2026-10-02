import os
import time
import json
import html
import threading
import requests
from datetime import datetime
from flask import Flask

# الإعدادات الأساسية
TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT = os.environ.get("TG_CHAT", "")
NETWORKS = os.environ.get(
    "NETWORKS", "solana,base,eth,bsc,arbitrum,polygon_pos,avax,ronin,tron"
).split(",")

MIN_WINS = int(os.environ.get("MIN_WINS", "2"))        # عدد الانتصارات المطلوبة لاعتماد المحفظة كذكية
PUMP_X = 3.0                  # نسبة الصعود المطلوب لاحتساب الصفقة انتصاراً للمحفظة
MIN_WIN_USD = 50              # الحد الأدنى لشراء الفوز
MIN_BUY_USD = 40              # أقل مبلغ شراء يطلق التنبيه الفوري
MIN_LIQ = 3000                # أقل سيولة مقبولة للبول
PER_NET = int(os.environ.get("PER_NET", "20"))        # عدد البولات المرصودة لكل شبكة (لزيادة السرعة والشمول)
ALERT_WINDOW = 300            # نافذة زمنية قصيرة للحرص على فورية التنبيه (بالثواني)
REFRESH = 180                 # تحديث أسرع لقائمة البولات النشطة
CALL_GAP = 1.5                # تقليل الفاصل الزمني للطلبات لضمان السرعة القصوى
BOARD_FILE = "board_instant.json"

GT = "https://api.geckoterminal.com/api/v2"
DEX = {"eth": "ethereum", "polygon_pos": "polygon", "avax": "avalanche"}
GOPLUS = {"eth": 1, "bsc": 56, "base": 8453, "arbitrum": 42161,
          "polygon_pos": 137, "avax": 43114}

board = {}                   # قاعدة بيانات المحافظ والانتصارات
alerted = set()              # منع التكرار الفوري لنفس التنبيه
sec_cache = {}               # ذاكرة مؤقتة لفحص الأمان
_last = [0.0]

# تحميل السجلات السابقة
try:
    if os.path.exists(BOARD_FILE):
        board = json.load(open(BOARD_FILE, "r"))
except Exception:
    pass

web = Flask(__name__)

@web.route("/")
def home():
    return "⚡ Instant Smart Money Radar is Active!"

@web.route("/health")
def health():
    smart_count = sum(1 for v in board.values() if len(v.get("wins", {})) >= MIN_WINS)
    return f"Status: OK | Tracked Wallets: {len(board)} | Confirmed Smart: {smart_count}"

def tg(msg):
    if not TG_TOKEN or not TG_CHAT:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={
                "chat_id": TG_CHAT,
                "text": msg,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=10
        )
    except Exception as e:
        print("Telegram error:", e)

def gt(path, **p):
    wait = CALL_GAP - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    try:
        r = requests.get(GT + path, params=p, timeout=12,
                         headers={"Accept": "application/json;version=20230302"})
        if r.status_code == 429:
            time.sleep(20)
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("GeckoTerminal error on", path, e)
        return None

def ts_of(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return time.time()

def refresh_pools():
    out = []
    for net in NETWORKS:
        pools = {}
        for ep in ("trending_pools", "new_pools"):
            j = gt(f"/networks/{net}/{ep}")
            for x in (j or {}).get("data", []):
                a = x["attributes"]
                liq = float(a.get("reserve_in_usd") or 0)
                if liq < MIN_LIQ:
                    continue
                addr = a["address"]
                pools[addr] = {
                    "net": net,
                    "addr": addr,
                    "name": a.get("name", "?"),
                    "liq": liq,
                    "created": a.get("pool_created_at"),
                    "vol": float((a.get("volume_usd") or {}).get("h1") or 0)
                }
        top = sorted(pools.values(), key=lambda p: -p["vol"])[:PER_NET]
        out.extend(top)
    return out

def security(net, token):
    cid = GOPLUS.get(net)
    if not cid:
        return "⚠️ فحص الأمان اليدوي مطلوب لهذه الشبكة"
    k = (net, token)
    if k in sec_cache:
        return sec_cache[k]
    try:
        r = requests.get(
            f"https://api.gopluslabs.io/api/v1/token_security/{cid}",
            params={"contract_addresses": token},
            timeout=8
        ).json()
        d = r.get("result", {}).get(token.lower(), {})
        is_hp = d.get("is_honeypot") == "1"
        buy_t = d.get("buy_tax", "?")
        sell_t = d.get("sell_tax", "?")
        status_icon = "🚨 تنبيه: محتمل Honeypot!" if is_hp else "🛡️ العقد نظيف"
        s = f"{status_icon} | شراء: {buy_t}% / بيع: {sell_t}%"
    except Exception:
        s = "⚠️ تعذر الفحص الأمني السريع"
    sec_cache[k] = s
    return s

def is_smart(key):
    # التحقق مما إذا كانت المحفظة مسجلة ولديها الحد الأدنى من الانتصارات السابقة
    return len(board.get(key, {}).get("wins", {})) >= MIN_WINS

def alert(p, w, token, usd, price):
    net = p["net"]
    age_str = ""
    if p["created"]:
        age_hours = (time.time() - ts_of(p['created'])) / 3600
        age_str = f" | ⏳ العمر: {age_hours:.1f}س"
    
    wins = len(board[f"{net}:{w}"].get("wins", {}))
    dex_link = f"https://dexscreener.com/{DEX.get(net, net)}/{p['addr']}"
    
    msg = (
        f"🚨⚡ <b>رصد شراء مال ذكي فوري!</b> ⚡🚨\n"
        f"🪙 <b>العملة:</b> {html.escape(p['name'])} [{net.upper()}]\n"
        f"📜 <b>العقد:</b>\n<code>{token}</code>\n"
        f"💰 <b>قيمة الشراء:</b> ${usd:,.0f} @ ${price:.8g}\n"
        f"💧 <b>السيولة:</b> ${p['liq']:,.0f}{age_str}\n"
        f"👛 <b>المحفظة:</b> <code>{w}</code>\n"
        f"🏆 <b>سجل الانتصارات:</b> {wins} صفقات ناجحة\n"
        f"🔍 {security(net, token)}\n"
        f"📊 <a href='{dex_link}'>رابط المنصة (DexScreener)</a>"
    )
    tg(msg)

def scan_pool(p):
    net = p["net"]
    j = gt(f"/networks/{net}/pools/{p['addr']}/trades")
    rows = []
    for x in (j or {}).get("data", []):
        a = x["attributes"]
        try:
            buy = a["kind"] == "buy"
            price = float(a["price_to_in_usd" if buy else "price_from_in_usd"] or 0)
            token = a["to_token_address"] if buy else a["from_token_address"]
            rows.append((ts_of(a["block_timestamp"]), a["tx_from_address"], buy,
                         float(a["volume_in_usd"] or 0), price, token))
        except Exception:
            continue
            
    if not rows:
        return
        
    rows.sort()
    n = len(rows)
    sufmax, m = [0.0] * n, 0.0
    for i in range(n - 1, -1, -1):
        m = max(m, rows[i][4])
        sufmax[i] = m
        
    now, firsts = time.time(), {}
    for i, (ts, w, buy, usd, price, token) in enumerate(rows):
        if not buy or price <= 0:
            continue
        key = f"{net}:{w}"
        
        # ⚡ الرصد الفوري: إذا كانت المحفظة مصنفة ذكية وتم الشراء حديثاً، أرسل فوراً دون انتظار!
        if (now - ts <= ALERT_WINDOW and usd >= MIN_BUY_USD and is_smart(key)
                and (key, token) not in alerted):
            alerted.add((key, token))
            alert(p, w, token, usd, price)
            
        if w not in firsts:
            firsts[w] = (i, usd, price, token)
            
    # تحديث الأرباح في الخلفية لتطوير الأداء المستقبلي للمحافظ
    for w, (i, usd, price, token) in firsts.items():
        if usd >= MIN_WIN_USD and sufmax[i] / price >= PUMP_X:
            board.setdefault(f"{net}:{w}", {"wins": {}})["wins"][token] = now

def main():
    tg("⚡ **تم تفعيل رادار المال الذكي (وضع الرصد الفوري اللحظي)** بنجاح!")
    queue, last = [], 0
    while True:
        try:
            if time.time() - last > REFRESH:
                queue, last = refresh_pools(), time.time()
            for p in queue:
                scan_pool(p)
            try:
                json.dump(board, open(BOARD_FILE, "w"))
            except Exception:
                pass
            if len(alerted) > 30000:
                alerted.clear()
        except Exception as e:
            print("Main loop error:", e)
        time.sleep(3)  # دورة تكرار أسرع (3 ثوانٍ فقط) لضمان الفورية

if __name__ == "__main__":
    threading.Thread(target=main, daemon=True).start()
    web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
