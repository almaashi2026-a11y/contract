import os
import time
import html
import threading
import requests
from flask import Flask

TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT = os.environ.get("TG_CHAT", "")
NETWORKS = os.environ.get("NETWORKS", "solana,base,eth,bsc").split(",")

MIN_BUY_USD = 10               # الحد الأدنى لشراء المحفظة لإطلاق التنبيه
MIN_LIQ = 500                  
MAX_MC = 10000000              
REFRESH = 15                   
CALL_GAP = 1.0

alerted = set()
_last = [0.0]
last_status = "Starting..."

web = Flask(__name__)

@web.route("/")
def home():
    global last_status
    return f"🚀 Debot Wallet Tracker Active | Status: {last_status} | Alerted Cache: {len(alerted)}"

@web.route("/health")
def health():
    return f"OK - {last_status}"

def tg(msg):
    print("[TELEGRAM WALLET ALERT]:", msg[:60])
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
    global last_status
    print("[*] Debot Wallet-Centric Scanner started.")
    tg("⚡ **رادار تتبع المحافظ (Debot Style) يعمل الآن!**")
    
    while True:
        try:
            total_checked = 0
            for net in NETWORKS:
                last_status = f"Scanning {net} wallets..."
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
                            wallet = ta.get("tx_from_address")  # التركيز على محفظة الشراء
                            
                            # منع التكرار والتركيز الأساسي على حركة المحفظة والتوكن
                            if usd >= MIN_BUY_USD and wallet and (wallet, token) not in alerted:
                                alerted.add((wallet, token))
                                msg = (
                                    f"🚨👛 <b>رصد شراء محفظة جديدة (Debot Tracker)</b>\n\n"
                                    f"🌐 الشبكة: {net.upper()}\n"
                                    f"🪙 التوكن: {html.escape(name)}\n"
                                    f"💰 حجم شراء المحفظة: ${usd:,.0f}\n"
                                    f"💧 السيولة: ${liq:,.0f}\n\n"
                                    f"🔑 عقد التوكن (CA):\n<code>{token}</code>\n\n"
                                    f"👛 عنوان المحفظة:\n<code>{wallet}</code>\n\n"
                                    f"🤖 <a href='https://debots.io'>Debot</a> | 🫧 <a href='https://bubblemaps.io'>BubbleMaps</a> | 📈 <a href='https://dexscreener.com/{net}/{addr}'>DexScreener</a>"
                                )
                                tg(msg)
                                break
            
            last_status = f"Idle. Tracked pools: {total_checked}."
            time.sleep(REFRESH)
            
        except Exception as e:
            last_status = f"Error: {str(e)}"
            print("[!] Loop error:", e)
            time.sleep(10)

if __name__ == "__main__":
    t = threading.Thread(target=main_loop, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 10000))
    web.run(host="0.0.0.0", port=port)
