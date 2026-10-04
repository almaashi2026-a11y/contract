import os
import time
import json
import html
import threading
import requests
from datetime import datetime
from collections import defaultdict
from flask import Flask

# الإعدادات الاحترافية المتقدمة
TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT = os.environ.get("TG_CHAT", "")
NETWORKS = os.environ.get(
    "NETWORKS", "solana,base,eth,bsc,arbitrum,polygon_pos,avax,ronin,tron"
).split(",")

MIN_WINS = int(os.environ.get("MIN_WINS", "3"))        # معيار صارم: 3 انتصارات سابقة مثبتة للمحفظة
PUMP_X = 3.2                  # نسبة الصعود الأدنى لاحتساب الصفقة انتصاراً (3.2x)
MIN_WIN_USD = 80              # الحد الأدنى لحجم شراء الفوز للتأكد من قوة رأس مال المحفظة
MIN_BUY_USD = 50              # أقل مبلغ شراء يسمح بإطلاق التنبيه الفوري
MIN_LIQ = 5000                # السيولة الأدنى للبول ($5000) لضمان عمق السوق
MAX_MC = 250000               # الحد الأقصى للقيمة السوقية (MC) لاستهداف العملات المبكرة جداً
MAX_WALLET_TRADES = 25        # استبعاد البوتات الآلية والمحافظ التي تداول بجنون (Spam)
PER_NET = int(os.environ.get("PER_NET", "30"))        # عدد البولات المرصودة لكل شبكة لزيادة الشمول
ALERT_WINDOW = 120            # نافذة زمنية فائقة القصر (دقيقتان) لضمان الدخول قبل الصعود
REFRESH = 100                 # تحديث سريع للبولات والاتجاهات
CALL_GAP = 1.0                # أقصى سرعة ممكنة للطلبات مع حماية الكود من الحظر
BOARD_FILE = "board_elite_pro.json"

GT = "https://api.geckoterminal.com/api/v2"
DEX = {"eth": "ethereum", "polygon_pos": "polygon", "avax": "avalanche"}

board = {}                   # قاعدة بيانات المحافظ النخبة
alerted = set()              # منع تكرار التنبيهات لنفس العملة ونفس المحفظة
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
    return "🚀 Elite Smart Money & Debot Radar is Running!"

@web.route("/health")
def health():
    elite_count = sum(1 for v in board.values() if len(v.get("wins", {})) >= MIN_WINS)
    return f"Status: OK | Total Wallets: {len(board)} | Elite Smart Wallets: {elite_count}"

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
            time.sleep(15)
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
                mc = float(a.get("fdv_usd") or 0)
                
                # فلاتر النخبة: سيولة ممتازة وقيمة سوقية منخفضة للدخول قبل الانفجار
                if liq < MIN_LIQ or (0 < mc > MAX_MC):
                    continue
                    
                addr = a["address"]
                pools[addr] = {
                    "net": net,
                    "addr": addr,
                    "name": a.get("name", "?"),
                    "liq": liq,
                    "mc": mc,
                    "created": a.get("pool_created_at"),
                    "vol": float((a.get("volume_usd") or {}).get("h1") or 0)
                }
        top = sorted(pools.values(), key=lambda p: -p["vol"])[:PER_NET]
        out.extend(top)
    return out

def is_elite_smart(key):
    return len(board.get(key, {}).get("wins", {})) >= MIN_WINS

def alert(p, w, token, usd, price):
    net = p["net"].upper()
    token_name = html.escape(p['name'])
    mc_val = f"${p['mc']:,.0f}" if p['mc'] > 0 else "غير متوفر"
    wins_count = len(board[f"{net.lower()}:{w}"].get("wins", {}))
    
    msg = (
        f"🚨🔥 <b>رصد نخبة المال الذكي (دخول احترافي مبكر)</b>\n"
        f"🎯 <b>اقتناص الصفقة قبل الانفجار السعري الكبير</b>\n\n"
        f"🌐 <b>السلسلة:</b> {net}\n"
        f"🪙 <b>التوكن:</b> {token_name}\n"
        f"🚀 <b>القيمة السوقية (MC):</b> {mc_val}\n"
        f"💧 <b>السيولة الحقيقية:</b> ${p['liq']:,.0f}\n"
        f"💰 <b>قيمة الشراء المرصودة:</b> ${usd:,.0f} @ ${price:.8g}\n"
        f"🏆 <b>سجل نجاح المحفظة:</b> {wins_count} انتصارات موثقة\n\n"
        f"🔑 <b>العقد (CA):</b>\n"
        f"<code>{token}</code>\n\n"
        f"👛 <b>المحفظة الذكية:</b> <code>{w}</code>\n\n"
        f"🛡️ <b>أدوات الفحص والتنفيذ السريع:</b>\n"
        f"🤖 <a href='https://debots.io'>تنفيذ ومتابعة عبر Debot</a>\n"
        f"🫧 <a href='https://bubblemaps.io'>فحص المحافظ BubbleMaps</a>\n"
        f"📊 <a href='https://defined.fi'>Defined.fi</a>\n"
        f"⚡ <a href='https://www.okx.com/web3'>شراء OKX DEX</a>\n"
        f"📈 <a href='https://dexscreener.com/{p.get('net', 'solana')}/{p['addr']}'>رابط DexScreener</a>"
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
        
    cnt = defaultdict(int)
    for r in rows:
        cnt[r[1]] += 1
        
    now, firsts = time.time(), {}
    for i, (ts, w, buy, usd, price, token) in enumerate(rows):
        if not buy or price <= 0:
            continue
        key = f"{net}:{w}"
        
        # الرصد الاحترافي الفوري للمحافظ النخبة ضمن النافذة الزمنية الضيقة
        if (now - ts <= ALERT_WINDOW and usd >= MIN_BUY_USD and is_elite_smart(key)
                and (key, token) not in alerted):
            alerted.add((key, token))
            alert(p, w, token, usd, price)
            
        if w not in firsts:
            firsts[w] = (i, usd, price, token)
            
    # تحديث وتصنيف أداء المحافظ بدقة عالية في الخلفية
    for w, (i, usd, price, token) in firsts.items():
        if (usd >= MIN_WIN_USD and cnt[w] <= MAX_WALLET_TRADES
                and sufmax[i] / price >= PUMP_X):
            board.setdefault(f"{net}:{w}", {"wins": {}})["wins"][token] = now

def main():
    tg("⚡ **رادار النخبة الاحترافي مع ربط Debot جاهز للعمل!**")
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
        time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=main, daemon=True).start()
    web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
