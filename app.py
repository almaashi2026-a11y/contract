import os
import time
import html
import threading
import requests
from datetime import datetime
from flask import Flask, render_template_string

TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT = os.environ.get("TG_CHAT", "")
NETWORKS = os.environ.get("NETWORKS", "solana,base,eth,bsc").split(",")

REFRESH = 2                    
CALL_GAP = 0.3                 

MIN_LIQ = 3000                 
MIN_MC = 10000                 
MAX_MC = 250000                

alerted_pools = set()
recent_alerts = []             
_last = [0.0]
last_status = "Multi-Wallet Sniper Pro Active..."

web = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>Debot Multi-Wallet Sniper Pro</title>
    <meta http-equiv="refresh" content="3">
    <style>
        body { background-color: #06080c; color: #e6edf3; font-family: Tahoma, sans-serif; padding: 20px; margin: 0; }
        h1 { color: #3fb950; text-align: center; margin-bottom: 5px; }
        .subtitle { text-align: center; color: #8b949e; margin-bottom: 25px; font-size: 0.95em; }
        .stats { background: #161b22; padding: 15px 20px; border-radius: 8px; margin-bottom: 25px; display: flex; justify-content: space-around; border: 1px solid #30363d; flex-wrap: wrap; gap: 10px; }
        .stats div { font-size: 1.05em; }
        .stats span { color: #3fb950; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; border: 1px solid #30363d; }
        th, td { padding: 12px 15px; text-align: right; border-bottom: 1px solid #30363d; font-size: 0.9em; }
        th { background: #21262d; color: #58a6ff; }
        tr:hover { background: #1f242c; }
        a { color: #58a6ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .badge { background: #3fb95033; color: #3fb950; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; border: 1px solid #3fb95066; }
        .wallets-tag { background: #1f6feb33; color: #58a6ff; padding: 3px 6px; border-radius: 4px; font-size: 0.8em; border: 1px solid #58a6ff55; font-weight: bold; }
        .copy-btn { background: #21262d; color: #58a6ff; border: 1px solid #30363d; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-family: monospace; font-size: 0.9em; }
        .copy-btn:hover { background: #30363d; color: #79c0ff; }
        .price { color: #3fb950; font-weight: bold; font-size: 1.05em; }
        #toast { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: #238636; color: #fff; padding: 10px 20px; border-radius: 6px; display: none; font-weight: bold; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
    </style>
</head>
<body>
    <h1>🎯👥 رادار تراكم المحافظ المتعددة (Multi-Wallet Sniper)</h1>
    <div class="subtitle">رصد العملات عند دخول أكثر من محفظة حقيقية قبل الارتفاع والانفجار</div>
    
    <div class="stats">
        <div>حالة الرادار: <span>{{ status }}</span></div>
        <div>الصفقات المؤكدة بمحافظ متعددة: <strong>{{ alerts|length }}</strong></div>
        <div>الشبكات المفعلة: <strong>{{ networks }}</strong></div>
    </div>
    
    <h2>📊 جدول رصد تراكم السيولة الحقيقية للمحافظ:</h2>
    <table>
        <thead>
            <tr>
                <th>الوقت</th>
                <th>الشبكة</th>
                <th>التوكن / حالة التراكم</th>
                <th>القيمة السوقية (MC)</th>
                <th>السيولة الحقيقية</th>
                <th>عقد التوكن (CA)</th>
                <th>روابط التحليل</th>
            </tr>
        </thead>
        <tbody>
            {% for item in alerts %}
            <tr>
                <td>{{ item.time }}
