import os
import time
import json
import html
import threading
import requests
from datetime import datetime
from collections import defaultdict
from flask import Flask

TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT = os.environ.get("TG_CHAT", "")
NETWORKS = os.environ.get("NETWORKS", "solana,base,eth,bsc").split(",")

# تم تخفيف الفلاتر قليلاً لضمان ظهور نتائج ورصد سريع
MIN_WINS = int(os.environ.get("MIN_WINS", "1"))        # تخفيض الانتصارات المطلوبة مبدئياً لاختبار الرصد
PUMP_X = 2.0                  # نسبة صعود أقل لضمان تسجيل الانتصارات بسرعة
MIN_WIN_USD = 30              
MIN_BUY_USD = 20              # تقليل الحد الأدنى للشراء لالتقاط الصفقات الصغيرة
MIN_LIQ = 1000                # تقليل الحد الأدنى للسيولة ($1000) لرصد البولات الناشئة فوراً
MAX_MC = 1000000              # رفع القيمة السوقية العظمى لزيادة نطاق البحث
PER_NET = int(os.environ.get("PER_NET", "20"))        
ALERT_WINDOW = 600            # توسيع النافذة الزمنية إلى 10 دقائق لضمان عدم تفويت أي إشارة
REFRESH = 60                  
CALL_GAP = 1.0                
BOARD_FILE = "board_elite_pro.json"

GT = "https://api.geckoterminal.com/api/v2"

board = {}
alerted = set()
_last = [0.0]

try:
    if os.path.exists(BOARD_FILE):
        board = json.load(open(BOARD_FILE, "r"))
        print(f"[*] Loaded {len(board)} tracked wallets from disk.")
except Exception as e:
    print("[!] Error loading board:", e)

web = Flask(__name__)

@web.route("/")
def home():
    return "🚀 Debot Scanner Active & Debugging Mode On!"

@web.route("/health")
def health():
    return f"Status: OK | Tracked Wallets: {len(board)} | Alerted Cache: {len(alerted)}"

def tg(msg):
    print("[TELEGRAM MSG]:", msg[:60], "...")
    if not TG_TOKEN or not TG_CHAT:
        print("[!] Telegram Token or Chat ID is missing!")
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
            print("[!] Rate limited (429), sleeping...")
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
    print("[*] Refreshing pools across networks:", NETWORKS)
    for net in NETWORKS:
        pools = {}
        for ep in ("trending_pools", "new_pools"):
            j = gt(f"/networks/{net}/{ep}")
            items = (j or {}).get("data", [])
            print(f"    -> Network {net} [{ep}]: fetched {len(items)} pools")
            for x in items:
                a = x["attributes"]
                liq = float(a.get("reserve_in_usd") or 0)
                mc = float(a.get("fdv_usd") or 0)
                
                if liq < MIN_LIQ or (0 < mc > MAX_MC):
                    continue
                    
                addr = a["address"]
                pools[addr] = {
                    "net": net,
                    "addr": addr,
                    "name": a.get("name", "?"),
                    "liq": liq,
                    "mc": mc,
                    "vol": float((a.get("volume_usd") or {}).get("h1") or 0)
                }
        top = sorted(pools.values(), key=lambda p: -p["vol"])[:PER_NET]
        out.extend(top)
    print(f"[*] Total active pools selected for scanning: {len(out)}")
    return out

def alert(p, w, token, usd, price):
    net = p["net"].upper()
    token_name = html.escape(p['name'])
    mc_val = f"${p['mc']:,.0f}" if p['mc'] > 0 else "غير متوفر"
    
    msg = (
        f"🚨🔥 <b>رصد فرصة مبكرة (Debot Scanner)</b>\n\n"
        f"🌐 <b>السلسلة:</b> {net}\n"
        f"🪙 <b>التوكن:</b> {token_name}\n"
        f"🚀 <b>القيمة السوقية (MC):</b> {mc_val}\n"
        f"💧 <b>السيولة:</b> ${p['liq']:,.0f}\n"
        f"💰 <b>قيمة الشراء:</b> ${usd:,.0f} @ ${price:.8g}\n\n"
        f"🔑 <b>العقد (CA):</b>\n"
        f"<code>{token}</code>\n\n"
        f"👛 <b>المحفظة:</b> <code>{w}</code>\n\n"
        f"🛡️ <b>الروابط السريعة:</b>\n"
        f"🤖 <a href='https://debots.io'>Debot</a> | "
        f"🫧 <a href='https://bubblemaps.io'>BubbleMaps</a> | "
        f"📈 <a href='https://dexscreener.com/{p.get('net', 'solana')}/{p['addr']}'>DexScreener</a>"
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
        
    now = time.time()
    for i, (ts, w, buy, usd, price, token) in enumerate(rows):
        if not buy or price <= 0:
            continue
        key = f"{net}:{w}"
        
        # للتأكد من الرصد السريع، سيتم التنبيه فوراً إذا كانت الصفقة ضمن النافذة وتجاوزت الحد الأدنى
        if (now - ts <= ALERT_WINDOW and usd >= MIN_BUY_USD and (key, token) not in alerted):
            # كمحاولة أولية لاختبار ظهور التنبيهات، سنقوم بإرسال إشارة فورية لكل شراء حقيقي ضمن المعايير
            alerted.add((key, token))
            alert(p, w, token, usd, price)
            break # تنبيه واحد كافي لكل بول تفادياً للإزعاج

def main():
    tg("⚡ **رادار Debot يعمل الآن بنجاح وفي وضع الفحص المباشر!**")
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
        time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=main, daemon=True).start()
    web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
