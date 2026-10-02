import os, time, threading, requests
from datetime import date
from concurrent.futures import ThreadPoolExecutor
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

TG_TOKEN = os.environ["TG_TOKEN"]
TG_CHAT = os.environ["TG_CHAT"]
DRY_RUN = os.environ.get("DRY_RUN", "1") == "1"   # 1 = تنبيه فقط
PK = os.environ.get("PK")                          # المفتاح الخاص (Render فقط)
FUNDER = os.environ.get("FUNDER")                  # عنوان محفظة بولي ماركت
SIG_TYPE = int(os.environ.get("SIG_TYPE", "1"))    # 1 إيميل/Magic، 2 متصفح

BUY_USD = float(os.environ.get("BUY_USD", "5"))
DAILY_CAP = float(os.environ.get("DAILY_CAP", "30"))
MAX_SLIPPAGE = 0.03       # أقصى فرق بين سعره وسعرك
MAX_PRICE = 0.85
MIN_LEADER_USD = 100
ELITE_PNL, ELITE_WIN, ELITE_MIN_CLOSED = 3000, 0.60, 15
MAX_ELITE = 25
POLL_EVERY = 1.5

DATA = "https://data-api.polymarket.com"
HOST = "https://clob.polymarket.com"

pub = ClobClient(HOST)
trader = None
if not DRY_RUN:
    trader = ClobClient(HOST, key=PK, chain_id=137,
                        signature_type=SIG_TYPE, funder=FUNDER)
    trader.set_api_creds(trader.create_or_derive_api_creds())

elite = {}               # wallet -> pnl
score_cache = {}
seen_disc, seen_w, warmed = set(), set(), set()
held = {}                # asset -> سعر دخولنا
spent = {"day": date.today(), "usd": 0.0}


def tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": TG_CHAT, "text": msg,
                            "disable_web_page_preview": True}, timeout=10)
    except Exception as e:
        print("tg err", e)


def get(url, **p):
    try:
        r = requests.get(url, params=p, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("api err", url, e)
        return None


def score(w):
    c = score_cache.get(w)
    if c and time.time() - c[0] < 6 * 3600:
        return c
    d = get(f"{DATA}/closed-positions", user=w, limit=50)
    if d is None:
        return None
    pnl = sum(float(x.get("realizedPnl", 0) or 0) for x in d)
    win = sum(1 for x in d if float(x.get("realizedPnl", 0) or 0) > 0) / max(len(d), 1)
    ok = len(d) >= ELITE_MIN_CLOSED and pnl >= ELITE_PNL and win >= ELITE_WIN
    score_cache[w] = (time.time(), ok, pnl, win)
    return score_cache[w]


def discovery():
    while True:
        try:
            calls = 0
            for t in reversed(get(f"{DATA}/trades", limit=500) or []):
                k = (t.get("transactionHash"), t.get("asset"), t.get("side"), t.get("size"))
                if k in seen_disc:
                    continue
                seen_disc.add(k)
                w = t.get("proxyWallet")
                usd = float(t.get("size", 0) or 0) * float(t.get("price", 0) or 0)
                if not w or t.get("side") != "BUY" or usd < MIN_LEADER_USD or w in elite:
                    continue
                if w not in score_cache and calls >= 15:
                    continue
                calls += 1
                s = score(w)
                if s and s[1]:
                    elite[w] = s[2]
                    if len(elite) > MAX_ELITE:
                        elite.pop(min(elite, key=elite.get))
            if len(seen_disc) > 200000:
                seen_disc.clear()
        except Exception as e:
            print("disc err", e)
        time.sleep(15)


def best_ask(asset):
    try:
        r = pub.get_price(asset, "BUY")
        return float(r["price"] if isinstance(r, dict) else r)
    except Exception as e:
        print("price err", e)
        return None


def handle(w, t):
    asset, side = t.get("asset"), t.get("side")
    price = float(t.get("price", 0) or 0)
    usd = float(t.get("size", 0) or 0) * price
    delay = time.time() - int(t.get("timestamp") or time.time())
    tag = f"{w[:6]}…{w[-4:]}"
    if side == "SELL":
        if asset in held:
            tg(f"⚠️ الـ elite {tag} يبيع شي عندك!\n{t.get('title')}\nفكّر تطلع.")
        return
    if usd < MIN_LEADER_USD or price > MAX_PRICE or asset in held:
        return
    ask = best_ask(asset)
    if ask is None or ask - price > MAX_SLIPPAGE:
        tg(f"⏭️ تخطيت (السعر طار): {t.get('title')}\nهو {price:.2f} | الحين {ask}")
        return
    if spent["day"] != date.today():
        spent.update(day=date.today(), usd=0.0)
    if spent["usd"] + BUY_USD > DAILY_CAP:
        tg("🛑 وصلت الحد اليومي")
        return
    head = (f"{t.get('title')}\n{t.get('outcome')} | دخل {price:.2f} (${usd:,.0f})\n"
            f"سعرك الحين: {ask:.2f} | تأخير: {delay:.0f}ث | {tag} (ربح ${elite.get(w, 0):,.0f})")
    if DRY_RUN:
        tg("🧪 [تجربة] كان بيشتري\n" + head)
        held[asset] = ask
        return
    try:
        signed = trader.create_market_order(
            MarketOrderArgs(token_id=asset, amount=BUY_USD, side=BUY))
        resp = trader.post_order(signed, OrderType.FOK)
        ok = bool(resp.get("success"))
        if ok:
            held[asset] = ask
            spent["usd"] += BUY_USD
        tg(("✅ اشتريت $%.0f\n" % BUY_USD if ok else "❌ فشل الشراء\n") + head + f"\n{resp}")
    except Exception as e:
        tg(f"❌ خطأ بالتنفيذ: {e}\n{head}")


def poll_wallet(w):
    d = get(f"{DATA}/trades", user=w, limit=10)
    if not d:
        return
    for t in reversed(d):
        k = (t.get("transactionHash"), t.get("asset"), t.get("side"), t.get("size"))
        if k in seen_w:
            continue
        seen_w.add(k)
        if w in warmed:
            handle(w, t)
    warmed.add(w)


if __name__ == "__main__":
    tg(f"✅ v3 شغّال | {'تجربة DRY_RUN' if DRY_RUN else '⚡ تنفيذ حقيقي'}")
    threading.Thread(target=discovery, daemon=True).start()
    with ThreadPoolExecutor(max_workers=8) as ex:
        while True:
            t0 = time.time()
            list(ex.map(poll_wallet, list(elite)))
            time.sleep(max(0, POLL_EVERY - (time.time() - t0)))
