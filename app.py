import os
import requests
from flask import Flask, render_template_string, request

app = Flask(__name__)

# قالب HTML بتصميم تداولي احترافي (Dark Theme) لعرض التدفقات والعقود بوضوح
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tape Flow & Sniper Terminal - عبد الرحمن</title>
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: Tahoma, sans-serif; margin: 0; padding: 20px; }
        h1 { color: #58a6ff; text-align: center; font-size: 24px; margin-bottom: 20px; }
        .filter-box { background: #161b22; padding: 15px; border-radius: 8px; margin-bottom: 20px; display: flex; gap: 15px; justify-content: center; align-items: center; border: 1px solid #30363d; }
        input, select { background: #0d1117; color: #fff; border: 1px solid #30363d; padding: 8px 12px; border-radius: 5px; }
        button { background: #238636; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-weight: bold; }
        button:hover { background: #2ea043; }
        table { width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; border: 1px solid #30363d; }
        th, td { padding: 12px 15px; text-align: center; border-bottom: 1px solid #30363d; font-size: 14px; }
        th { background: #21262d; color: #8b949e; }
        tr:hover { background: #1f6feb15; }
        .buy { color: #3fb950; font-weight: bold; }
        .sell { color: #f85149; font-weight: bold; }
        .ca-link { color: #58a6ff; text-decoration: none; font-family: monospace; }
        .ca-link:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>⚡ Tape Flow & Institutional Sniper Terminal ⚡</h1>
    
    <div class="filter-box">
        <form method="GET" action="/">
            <label>الحد الأدنى للسيولة ($):</label>
            <input type="number" name="min_liq" value="{{ min_liq }}">
            <label>نوع العملية:</label>
            <select name="action_type">
                <option value="all" {% if action_type == 'all' %}selected{% endif %}>الجميع</option>
                <option value="buy" {% if action_type == 'buy' %}selected{% endif %}>شراء فقط</option>
            </select>
            <button type="submit">تطبيق الفلتر</button>
        </form>
    </div>

    <table>
        <thead>
            <tr>
                <th>الرمز المميز (Token)</th>
                <th>الحالة / الاتجاه</th>
                <th>القيمة السوقية (MCap)</th>
                <th>السيولة ($)</th>
                <th>العقد (CA)</th>
                <th>روابط الفحص</th>
            </tr>
        </thead>
        <tbody>
            {% for item in data %}
            <tr>
                <td><b>{{ item.name }}</b> ({{ item.symbol }})</td>
                <td class="buy">شراء 🟢</td>
                <td>${{ "{:,.0f}".format(item.mcap) }}</td>
                <td>${{ "{:,.0f}".format(item.liquidity) }}</td>
                <td><span class="ca-link">{{ item.ca[:6] }}...{{ item.ca[-4:] }}</span></td>
                <td>
                    <a href="https://defined.fi/token/{{ item.ca }}" target="_blank" style="color: #58a6ff; margin-left: 10px;">Charts</a>
                    <a href="https://app.bubblemaps.io/token/{{ item.ca }}" target="_blank" style="color: #f0883e;">BubbleMaps</a>
                </td>
            </tr>
            {% else %}
            <tr>
                <td colspan="6" style="color: #8b949e; padding: 20px;">جاري جلب التدفقات الحية وتطبيق الفلاتر...</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

@app.route('/')
def index():
    min_liq = request.args.get('min_liq', '10000')
    try:
        min_liq_val = float(min_liq)
    except:
        min_liq_val = 10000.0

    action_type = request.args.get('action_type', 'all')

    # جلب البيانات الحية من DexScreener للعملات النشطة على سولانا
    url = "https://api.dexscreener.com/latest/dex/search?q=solana"
    parsed_data = []
    try:
        response = requests.get(url, timeout=5)
        pairs = response.json().get("pairs", [])
        for pair in pairs:
            if pair.get("chainId") != "solana":
                continue
            liquidity = pair.get("liquidity", {}).get("usd", 0)
            if liquidity < min_liq_val:
                continue
                
            parsed_data.append({
                "name": pair.get("baseToken", {}).get("name", "Unknown"),
                "symbol": pair.get("baseToken", {}).get("symbol", ""),
                "ca": pair.get("baseToken", {}).get("address", ""),
                "liquidity": liquidity,
                "mcap": pair.get("marketCap", 0)
            })
    except Exception as e:
        print(f"Error fetching data: {e}")

    return render_template_string(HTML_TEMPLATE, data=parsed_data[:20], min_liq=min_liq, action_type=action_type)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
