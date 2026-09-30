import os
import requests
from flask import Flask, render_template_string, request
import threading
import time

app = Flask('')

# إعدادات تيليجرام (ضع توكن بوتك ومعرفك هنا)
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

def send_telegram_alert(message):
    if "YOUR_" in TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=3)
    except Exception as e:
        print(f"خطأ في إرسال التنبيه: {e}")

# تخزين مؤقت للفرص المرصودة فائقة السرعة
pro_scanned_tokens = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="15"> <!-- تحديث تلقائي للوحة كل 15 ثانية للسرعة المطلقة -->
    <title>Pro Institutional Flow Terminal - عبد الرحمن</title>
    <style>
        body { background-color: #0b0e14; color: #e6edf3; font-family: 'Courier New', Courier, monospace; margin: 0; padding: 20px; }
        h1 { color: #58a6ff; text-align: center; font-size: 22px; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px; }
        .stats-bar { display: flex; justify-content: space-around; background: #161b22; padding: 10px; border-radius: 6px; margin-bottom: 20px; border: 1px solid #30363d; font-size: 13px; }
        table { width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; border: 1px solid #30363d; }
        th, td { padding: 10px 12px; text-align: center; border-bottom: 1px solid #30363d; font-size: 13px; }
        th { background: #21262d; color: #8b949e; text-transform: uppercase; }
        tr:hover { background: #1f6feb20; }
        .live-tag { color: #3fb950; font-weight: bold; animation: pulse 1.5px infinite; }
        .chain-badge { background: #238636; padding: 2px 6px; border-radius: 4px; font-size: 11px; color: #fff; font-weight: bold; }
        .ca-box { color: #58a6ff; background: #0d1117; padding: 2px 6px; border-radius: 4px; border: 1px solid #30363d; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <h1>⚡ Pro Institutional Flow & Tape Terminal ⚡</h1>
    
    <div class="stats-bar">
        <span>🟢 حالة النظام: <b>متصل فائق السرعة (Real-Time)</b></span>
        <span>⚡ التحديث التلقائي: <b>مفعل (كل 15 ثانية)</b></span>
        <span>🎯 الهدف: <b>قنص التدفقات المبكرة للحيتان</b></span>
    </div>

    <table>
        <thead>
            <tr>
                <th>الشبكة</th>
                <th>الرمز المميز</th>
                <th>حالة التدفق</th>
                <th>القيمة السوقية (MCap)</th>
                <th>السيولة ($)</th>
                <th>حجم (5m)</th>
                <th>عقد العملة (CA)</th>
                <th>التحليل السريع</th>
            </tr>
        </thead>
        <tbody>
            {% for item in data %}
            <tr>
                <td><span class="chain-badge">{{ item.chain | upper }}</span></td>
                <td><b>{{ item.name }}</b> ({{ item.symbol }})</td>
                <td class="live-tag">تدفق مؤسسي صاعد 🔥</td>
                <td>${{ "{:,.0f}".format(item.mcap) }}</td>
                <td>${{ "{:,.0f}".format(item.liquidity) }}</td>
                <td style="color: #3fb950;">${{ "{:,.0f}".format(item.vol_5m) }}</td>
                <td><span class="ca-box">{{ item.ca }}</span></td>
                <td>
                    <a href="https://defined.fi/token/{{ item.ca }}" target="_blank" style="color: #58a6ff; text-decoration: none; margin-left: 8px;">Charts</a>
                    <a href="https://app.bubblemaps.io/token/{{ item.ca }}" target="_blank" style="color: #f0883e; text-decoration: none;">BubbleMaps</a>
                </td>
            </tr>
            {% else %}
            <tr>
                <td colspan="8" style="color: #8b949e; padding: 25px;">جاري رصد صفقات الشريط اللحظي عبر الشبكات...</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

def pro_lightning_scanner():
    """
    محرك فحص فائق السرعة يركز على أحدث التدفقات المضافة مباشرة لتفادي أي تأخير
    """
    global pro_scanned_tokens
    sent_alerts = set()
    
    # نقطة جلب أحدث البروفايلات والتوكنات النشطة في السوق لحظياً
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    
    while True:
        temp_list = []
        try:
            res = requests.get(url, timeout=4)
            profiles = res.json()
            
            if isinstance(profiles, list):
                for p in profiles[:15]: # فحص أحدث 15 عملة لضمان السرعة القصوى وعدم حصول Timeout
                    ca = p.get("tokenAddress")
                    chain = p.get("chainId", "solana")
                    if not ca:
                        continue
                        
                    detail_url = f"https://api.dexscreener.com/latest/dex/tokens/{ca}"
                    detail_res = requests.get(detail_url, timeout=2)
                    pairs = detail_res.json().get("pairs", [])
                    
                    for pair in pairs:
                        liquidity = pair.get("liquidity", {}).get("usd", 0)
                        mcap = pair.get("marketCap", 0)
                        vol_5m = pair.get("volume", {}).get("m5", 0)
                        if vol_5m is None:
                            vol_5m = 0
                            
                        # فلاتر الاحترافية والسرعة: سيولة مقبولة وحجم تداول نشط
                        if liquidity < 5000:
                            continue
                            
                        token_data = {
                            "chain": chain,
                            "name": pair.get("baseToken", {}).get("name", "Unknown"),
                            "symbol": pair.get("baseToken", {}).get("symbol", ""),
                            "ca": ca,
                            "liquidity": liquidity,
                            "mcap": mcap,
                            "vol_5m": vol_5m
                        }
                        temp_list.append(token_data)
                        
                        # إرسال تنبيه فوري لتليجرام بدون أي تأخير عند رصد الفرصة لأول مرة
                        if ca not in sent_alerts:
                            sent_alerts.add(ca)
                            alert_msg = f"""
⚡ **[PRO INSTITUTIONAL TAPE ALERT]** ⚡

🌐 **الشبكة:** `{chain.upper()}`
🪙 **العملة:** `{token_data['name']} ({token_data['symbol']})`
📍 **عقد العملة (CA):**
`{ca}`

📊 **مؤشرات التدفق اللحظي:**
• القيمة السوقية: `${mcap:,.0f}`
• السيولة: `${liquidity:,.0f}` 🟢
• حجم التداول (5m): `${vol_5m:,.0f}` 🔥

🔗 **روابط التنفيذ السريع:**
• [Defined Charts](https://defined.fi/token/{ca})
• [BubbleMaps](https://app.bubblemaps.io/token/{ca})

🎯 *النظام الاحترافي: رصد فوري للتدفقات.. اتخذ قرارك بحذر!*
"""
                            send_telegram_alert(alert_msg)
                            time.sleep(0.5)
                        break
        except Exception as e:
            print(f"Pro Scanner error: {e}")
            
        if temp_list:
            pro_scanned_tokens = temp_list
            
        time.sleep(15) # دورة فحص سريعة جداً كل 15 ثانية لتأمين أقصى سرعة رصد

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, data=pro_scanned_tokens)

if __name__ == "__main__":
    scanner_thread = threading.Thread(target=pro_lightning_scanner)
    scanner_thread.daemon = True
    scanner_thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
