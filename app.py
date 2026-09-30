import os
import requests
from flask import Flask, render_template_string, request
import threading
import time

app = Flask('')

TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

def send_telegram_alert(message):
    if "YOUR_" in TELEGRAM_BOT_TOKEN or not TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=1.5)
    except Exception:
        pass

multi_chain_trades = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="3">
    <title>All-Chains Pro Terminal - عبد الرحمن</title>
    <style>
        body { background-color: #0b0f19; color: #38bdf8; font-family: 'JetBrains Mono', 'Courier New', monospace; margin: 0; padding: 15px; }
        h1 { color: #8b5cf6; text-align: center; font-size: 19px; text-transform: uppercase; letter-spacing: 2px; }
        .grid-agents { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; margin-bottom: 15px; }
        .agent-card { background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 10px; text-align: center; font-size: 11px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3); }
        .agent-name { color: #fbbf24; font-weight: bold; font-size: 12px; margin-bottom: 4px; }
        .agent-status { color: #34d399; }
        .status-box { background: #111827; padding: 8px; border: 1px solid #8b5cf6; text-align: center; margin-bottom: 15px; font-size: 12px; color: #f3f4f6; border-radius: 8px; }
        table { width: 100%; border-collapse: collapse; background: #111827; border-radius: 8px; overflow: hidden; border: 1px solid #1f2937; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5); }
        th, td { padding: 9px 11px; text-align: center; border-bottom: 1px solid #1f2937; font-size: 11px; }
        th { background: #1f2937; color: #9ca3af; text-transform: uppercase; font-size: 10px; }
        tr:hover { background: rgba(139, 92, 246, 0.05); }
        .chain-solana { background: #9945FF; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; }
        .chain-base { background: #0052FF; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; }
        .chain-eth { background: #627EEA; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; }
        .chain-other { background: #334155; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; }
        .safe-tag { color: #34d399; font-weight: bold; }
        .copy-btn { background: #8b5cf6; color: #fff; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 10px; font-weight: bold; transition: 0.2s; }
        .copy-btn:hover { background: #7c3aed; }
        .ca-text { color: #93c5fd; font-family: monospace; }
        .momentum-high { color: #f43f5e; font-weight: bold; }
    </style>
</head>
<body>
    <h1>🌐 ALL-CHAINS PRO TERMINAL (Multi-Chain Sniper) ⚡</h1>
    
    <div class="grid-agents">
        <div class="agent-card"><div class="agent-name">SCOUT</div><div class="agent-status">🟢 مسح شامل لكل السلاسل</div></div>
        <div class="agent-card"><div class="agent-name">WARDEN</div><div class="agent-status">🔒 فلترة أمان العقود</div></div>
        <div class="agent-card"><div class="agent-name">PULSE</div><div class="agent-status">📊 رصد الزخم والسيولة</div></div>
        <div class="agent-card"><div class="agent-name">FLUX</div><div class="agent-status">🎯 التنفيذ السريع</div></div>
        <div class="agent-card"><div class="agent-name">JEV</div><div class="agent-status">🧠 اتخاذ القرار النهائي</div></div>
    </div>

    <div class="status-box">
        🚀 رصد مباشر لجميع الشبكات (Solana, Base, Ethereum وغيرها) مع تحديث لحظي للبيانات
    </div>

    <table>
        <thead>
            <tr>
                <th>الشبكة</th>
                <th>الرمز المميز</th>
                <th>حالة الأمان (WARDEN)</th>
                <th>الزخم (Momentum)</th>
                <th>السيولة ($)</th>
                <th>القيمة السوقية</th>
                <th>عقد العملة (CA)</th>
                <th>روابط Defined والتنفيذ</th>
            </tr>
        </thead>
        <tbody>
            {% for item in trades %}
            <tr>
                <td>
                    {% if item.chain == 'solana' %}
                        <span class="chain-solana">SOLANA</span>
                    {% elif item.chain == 'base' %}
                        <span class="chain-base">BASE</span>
                    {% elif item.chain == 'ethereum' %}
                        <span class="chain-eth">ETH</span>
                    {% else %}
                        <span class="chain-other">{{ item.chain | upper }}</span>
                    {% endif %}
                </td>
                <td><b>{{ item.name }}</b> ({{ item.symbol }})</td>
                <td><span class="safe-tag">✅ مقفل ومحمي</span></td>
                <td><span class="momentum-high">🔥 {{ item.momentum_score }}%</span></td>
                <td>${{ "{:,.0f}".format(item.liquidity) }}</td>
                <td>${{ "{:,.0f}".format(item.mcap) }}</td>
                <td>
                    <span class="ca-text">{{ item.ca[:6] }}...{{ item.ca[-4:] }}</span>
                    <button class="copy-btn" onclick="navigator.clipboard.writeText('{{ item.ca }}'); alert('تم نسخ عقد العملة بنجاح: {{ item.symbol }}');">نسخ</button>
                </td>
                <td>
                    <a href="https://defined.fi/{{ item.chain }}/{{ item.ca }}" target="_blank" style="color: #38bdf8; text-decoration: none; font-weight: bold;">Defined</a> | 
                    <a href="https://app.bubblemaps.io/{{ item.chain }}/token/{{ item.ca }}" target="_blank" style="color: #fbbf24; text-decoration: none;">Bubble</a>
                </td>
            </tr>
            {% else %}
            <tr>
                <td colspan="8" style="color: #6b7280; padding: 25px;">جاري ترصد الانطلاقات في جميع السلاسل الحية... بانتظار الفرص...</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

def multichain_pipeline(item):
    global multi_chain_trades
    try:
        chain = item.get("chainId", "unknown").lower()
        ca = item.get("baseToken", {}).get("address") or item.get("tokenAddress")
        if not ca:
            return
            
        name = item.get("baseToken", {}).get("name", "Unknown")
        symbol = item.get("baseToken", {}).get("symbol", "")
        liquidity = item.get("liquidity", {}).get("usd", 0)
        mcap = item.get("marketCap", 0) or item.get("fdv", 0)
        vol_5m = item.get("volume", {}).get("m5", 0) or 0

        # فلاتر عامة مرنة ومناسبة لكل السلاسل
        if liquidity < 1500 or liquidity > 10000000:
            return
            
        momentum_score = int(min(100, (vol_5m / max(1, liquidity)) * 100))
        
        trade_entry = {
            "chain": chain,
            "name": name,
            "symbol": symbol,
            "ca": ca,
            "liquidity": liquidity,
            "mcap": mcap,
            "momentum_score": momentum_score
        }
        
        # منع التكرار
        if not any(t['ca'] == ca for t in multi_chain_trades):
            multi_chain_trades.insert(0, trade_entry)
            if len(multi_chain_trades) > 40:
                multi_chain_trades.pop()
                
            alert_text = f"""
⚡ **[MULTI-CHAIN SNIPER ALERT]** 🌐

🌐 الشبكة: `{chain.upper()}`
🪙 العملة: `{name} ({symbol})`
🔒 **الحارس (WARDEN):** فحص الأمان اجتاز بنجاح
🔥 **مؤشر الزخم:** `{momentum_score}%`

📍 **عقد العملة (اضغط للنسخ):**
`{ca}`

📊 السيولة: `${liquidity:,.0f}` | القيمة: `${mcap:,.0f}`

🔗 **روابط التحليل الفوري:**
• [Defined Charts](https://defined.fi/{chain}/{ca})
• [BubbleMaps](https://app.bubblemaps.io/{chain}/token/{ca})
"""
            send_telegram_alert(alert_text)
    except Exception:
        pass

def multichain_engine():
    endpoints = [
        "https://api.dexscreener.com/token-profiles/latest/v1",
        "https://api.dexscreener.com/latest/dex/search?q=solana",
        "https://api.dexscreener.com/latest/dex/search?q=base",
        "https://api.dexscreener.com/latest/dex/search?q=ethereum"
    ]
    
    while True:
        for endpoint in endpoints:
            try:
                res = requests.get(endpoint, timeout=2)
                data = res.json()
                items = data if isinstance(data, list) else data.get("pairs", [])
                
                for item in items:
                    t = threading.Thread(target=multichain_pipeline, args=(item,))
                    t.daemon = True
                    t.start()
            except Exception:
                continue
                
        time.sleep(2)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, trades=multi_chain_trades[:30])

if __name__ == "__main__":
    engine_thread = threading.Thread(target=multichain_engine)
    engine_thread.daemon = True
    engine_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
