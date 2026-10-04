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

MIN_BUY_USD = 10              
MIN_LIQ = 500                 
MAX_MC = 5000000              
PER_NET = 10                  
REFRESH = 30                  
CALL_GAP = 1.2                

board = {}
alerted = set()
_last = [0.0]
last_status = "Initializing..."

web = Flask(__name__)

@web.route("/")
def home():
    global last_status
    return f"🚀 Debot Scanner Status: {last_status} | Tracked: {len(board)}"

@web.route("/health")
def health():
    return f"OK - {last_status}"

def tg(msg):
    print("[TG]", msg[:50])
    if not TG_TOKEN or not TG_CHAT:
        print("[!] Missing TG credentials")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        print("[!] TG Error:", e)

def gt(path, **p):
    wait = CALL_GAP - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    try:
        r = requests.get(f"https://api.geckoterminal.com/api/v2{path}", params=p, timeout=10,
                         headers={"Accept": "application/json;version=20230302"})
        if r.status_code == 429:
            print("[!] Rate limit 429, waiting...")
            time.sleep(10)
            return None
        return r.json()
    except Exception as e:
        print("[!] API Error on", path, ":", e)
        return None

def main_loop():
    global last_status
    print("[*] Background scanner thread started successfully.")
    tg("⚡ **رادار Debot بدأ العمل ويقوم بالفحص الآن!**")
    
    while True:
        try:
            last_status = "Refreshing pools..."
            print(f"[{datetime.now()}] Refreshing pools for networks: {NETWORKS}")
            
            total_checked = 0
            for net in NETWORKS:
                j = gt(f"/networks/{net}/trending_pools")
                items = (j or {}).get("data", [])
                print(f" -> Network {net}: found {len(items)} trending pools")
                
                for x in items:
                    a = x["attributes"]
                    liq = float(a.get("reserve_in_usd") or 0)
                    mc = float(a.get("fdv_usd") or 0)
                    
                    if liq < MIN_LIQ or (0 < mc > MAX_MC):
                        continue
                        
                    addr = a["address"]
                    name = a.get("name", "?")
                    total_checked += 1
                    
                    # فحص الصفقات للبول النشط
                    trades_j = gt(f"/networks/{net}/pools/{addr}/trades")
                    trades = (trades_j or {}).get("data", [])
                    
                    for t in trades:
                        ta = t["attributes"]
                        if ta.get("kind") == "buy":
                            usd = float(ta.get("volume_in_usd") or 0)
                            token = ta.get("to_token_address")
                            w = ta.get("tx_from_address")
                            
                            if usd >= MIN_BUY_USD and (w, token) not in alerted:
                                alerted.add((w, token))
                                msg = (
                                    f"🚨🔥 <b>رصد صفقة جديدة (Debot)</b>\n\n"
                                    f"🌐 الشبكة: {net.upper()}\n"
                                    f"🪙 التوكن: {html.escape(name)}\n"
                                    f"💧 السيولة: ${liq:,.0f}\n"
                                    f"💰 الشراء: ${usd:,.0f}\n\n"
                                    f"🔑 العقد:\n<code>{token}</code>\n\n"
                                    f"🤖 <a href='https://debots.io'>Debot</a> | 📈 <a href='https://dexscreener.com/{net}/{addr}'>DexScreener</a>"
                                )
                                tg(msg)
                                break
            
            last_status = f"Idle. Checked {total_checked} pools."
            print(f"[*] Cycle finished. Sleeping for {REFRESH}s...")
            time.sleep(REFRESH)
            
        except Exception as e:
            last_status = f"Error: {str(e)}"
            print("[!] Critical loop error:", e)
            time.sleep(10)

if __name__ == "__main__":
    t = threading.Thread(target=main_loop, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 10000))
    web.run(host="0.0.0.0", port=port)
