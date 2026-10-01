import os, time, json, requests
from collections import defaultdict

TG_TOKEN = os.environ["TG_TOKEN"]   # من Environment في Render، لا تكتبه بالكود
TG_CHAT = os.environ["TG_CHAT"]
GAMMA = "https://gamma-api.polymarket.com"
DATA = "https://data-api.polymarket.com"

ARB_MAX_SUM = 0.98     # مجموع YES+NO أقل من هذا = فرصة
MIN_LIQ = 1000         # حد أدنى للسيولة
MIN_TRADES = 20        # حد أدنى لصفقات المحفظة لتدخل المراقبة
MIN_VOL = 5000         # حد أدنى لحجم المحفظة بالدولار
ALERT_MIN_USD = 50     # لا تنبّه على صفقات أصغر

SEEN = set()
wallets = defaultdict(lambda: {"n": 0, "vol": 0.0})


def tg(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg,
                  "disable_web_page_preview": True},
            timeout=10)
    except Exception as e:
        print("tg err", e)


def get(url, **params):
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("api err", url, e)
        return []


def scan_arb():
    markets = get(f"{GAMMA}/markets", active="true", closed="false", limit=500)
    for m in markets:
        try:
            prices = [float(x) for x in json.loads(m["outcomePrices"])]
            liq = float(m.get("liquidityNum") or 0)
        except Exception:
            continue
        if len(prices) != 2 or liq < MIN_LIQ:
            continue
        s = sum(prices)
        if s < ARB_MAX_SUM:
            key = ("arb", m["id"], round(s, 2))
            if key in SEEN:
                continue
            SEEN.add(key)
            tg(f"🎯 فرصة تحكيم محتملة\n{m.get('question')}\n"
               f"YES+NO = {s:.3f} (ربح نظري {(1 - s) * 100:.1f}%)\n"
               f"السيولة: ${liq:,.0f}\n"
               f"https://polymarket.com/market/{m.get('slug')}\n"
               f"⚠️ تأكد من الرسوم والـ spread قبل أي دخول")


def poll_trades():
    for t in get(f"{DATA}/trades", limit=500):
        key = (t.get("transactionHash"), t.get("asset"), t.get("side"))
        if key in SEEN:
            continue
        SEEN.add(key)
        w = t.get("proxyWallet")
        if not w:
            continue
        usd = float(t.get("size", 0)) * float(t.get("price", 0))
        st = wallets[w]
        st["n"] += 1
        st["vol"] += usd
        watched = st["n"] >= MIN_TRADES and st["vol"] >= MIN_VOL
        if watched and usd >= ALERT_MIN_USD:
            tg(f"👛 {w[:6]}…{w[-4:]}\n"
               f"{t.get('side')} {t.get('outcome')} @ {t.get('price')}\n"
               f"{t.get('title')}\n"
               f"الحجم: ${usd:,.0f} | صفقات: {st['n']} | حجم كلي: ${st['vol']:,.0f}")
    if len(SEEN) > 100000:
        SEEN.clear()


if __name__ == "__main__":
    tg("✅ Polymarket monitor شغّال")
    last_arb = 0
    while True:
        poll_trades()
        if time.time() - last_arb > 60:
            scan_arb()
            last_arb = time.time()
        time.sleep(10)
