import os, time, json, html, requests
from datetime import datetime
from collections import defaultdict

TG_TOKEN = os.environ["TG_TOKEN"]
TG_CHAT = os.environ["TG_CHAT"]
NETWORKS = os.environ.get(
    "NETWORKS", "solana,base,eth,bsc,arbitrum,polygon_pos,avax,ronin,tron").split(",")
MIN_WINS = int(os.environ.get("MIN_WINS", "2"))   # ابدأ بـ 1 أول ساعات
PUMP_X = 3.0              # صعود 3x بعد دخول المحفظة = فوز
MIN_WIN_USD = 50          # أقل شراء يُحسب فوز
MIN_BUY_USD = 50          # أقل شراء يطلّع تنبيه
MIN_LIQ = 3000            # أقل سيولة للبول
MAX_WALLET_TRADES = 40    # فوق هذا = بوت، نتجاهله
PER_NET = int(os.environ.get("PER_NET", "12"))    # بولات لكل سلسلة
ALERT_WINDOW = 600        # ثواني
REFRESH = 300
CALL_GAP = 2.3            # حد GeckoTerminal المجاني
BOARD_FILE = "board.json"

GT = "https://api.geckoterminal.com/api/v2"
DEX = {"eth": "ethereum", "polygon_pos": "polygon", "avax": "avalanche"}
GOPLUS = {"eth": 1, "bsc": 56, "base": 8453, "arbitrum": 42161,
          "polygon_pos": 137, "avax": 43114}

board = {}               # "net:wallet" -> {"wins": {token: ts}}
alerted = set()
sec_cache = {}
_last = [0.0]

try:
    board = json.load(open(BOARD_FILE))
except Exception:
    pass


def tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML",
                            "disable_web_page_preview": True}, timeout=10)
    except Exception as e:
        print("tg err", e)


def gt(path, **p):
    wait = CALL_GAP - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    try:
        r = requests.get(GT + path, params=p, timeout=15,
                         headers={"Accept": "application/json;version=20230302"})
        if r.status_code == 429:
            time.sleep(30)
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("gt err", path, e)
        return None


def ts_of(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def refresh_pools():
    out = []
    for net in NETWORKS:
        pools = {}
        for ep in ("trending_pools", "new_pools"):
            j = gt(f"/networks/{net}/{ep}")
            for x in (j or {}).get("data", []):
                a = x["attributes"]
                if float(a.get("reserve_in_usd") or 0) < MIN_LIQ:
                    continue
                pools[a["address"]] = {
                    "net": net, "addr": a["address"], "name": a.get("name", "?"),
                    "liq": float(a["reserve_in_usd"]),
                    "created": a.get("pool_created_at"),
                    "vol": float((a.get("volume_usd") or {}).get("h1") or 0)}
        top = sorted(pools.values(), key=lambda p: -p["vol"])[:PER_NET]
        out += top
    return out


def security(net, token):
    cid = GOPLUS.get(net)
    if not cid:
        return "غير مدعوم لهذي السلسلة، افحص العقد يدوي"
    k = (net, token)
    if k in sec_cache:
        return sec_cache[k]
    try:
        r = requests.get(f"https://api.gopluslabs.io/api/v1/token_security/{cid}",
                         params={"contract_addresses": token}, timeout=10).json()
        d = r["result"][token.lower()]
        s = ("🚨 HONEYPOT" if d.get("is_honeypot") == "1" else "ما فيه honeypot ظاهر") + \
            f" | ضريبة شراء {d.get('buy_tax') or '?'} / بيع {d.get('sell_tax') or '?'}"
    except Exception:
        s = "ما قدرت أفحص، افحص يدوي"
    sec_cache[k] = s
    return s


def is_smart(key):
    return len(board.get(key, {}).get("wins", {})) >= MIN_WINS


def alert(p, w, token, usd, price):
    net = p["net"]
    sym = html.escape(p["name"].split(" / ")[0])
    age = ""
    if p["created"]:
        age = f" | عمر: {(time.time() - ts_of(p['created'])) / 3600:.1f}س"
    wins = len(board[f"{net}:{w}"]["wins"])
    tg(f"🧠 <b>محفظة ذكية اشترت</b>\n"
       f"🪙 {html.escape(p['name'])} | {net.upper()}\n"
       f"📜 العقد:\n<code>{token}</code>\n"
       f"💰 اشترت ${usd:,.0f} @ ${price:.8g}\n"
       f"💧 سيولة ${p['liq']:,.0f}{age}\n"
       f"👛 <code>{w}</code> (انتصارات: {wins})\n"
       f"🛡️ {security(net, token)}\n"
       f"https://dexscreener.com/{DEX.get(net, net)}/{p['addr']}")


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
        if (now - ts <= ALERT_WINDOW and usd >= MIN_BUY_USD and is_smart(key)
                and (key, token) not in alerted):
            alerted.add((key, token))
            alert(p, w, token, usd, price)
        if w not in firsts:
            firsts[w] = (i, usd, price, token)
    for w, (i, usd, price, token) in firsts.items():
        if (usd >= MIN_WIN_USD and cnt[w] <= MAX_WALLET_TRADES
                and sufmax[i] / price >= PUMP_X):
            board.setdefault(f"{net}:{w}", {"wins": {}})["wins"][token] = now


if __name__ == "__main__":
    tg("✅ رادار المحافظ الذكية شغّال (عملات الميم)")
    queue, last = [], 0
    while True:
        if time.time() - last > REFRESH:
            queue, last = refresh_pools(), time.time()
        for p in queue:
            scan_pool(p)
        try:
            json.dump(board, open(BOARD_FILE, "w"))
        except Exception:
            pass
        if len(alerted) > 50000:
            alerted.clear()
        time.sleep(5)
