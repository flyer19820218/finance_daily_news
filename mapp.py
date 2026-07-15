import streamlit as st
import yfinance as yf
import json
import os
import requests
import pandas as pd
from urllib.parse import urlparse
from datetime import datetime, time
import pytz
import edge_tts
import asyncio
import io
import re
import base64
import streamlit.components.v1 as components

# 1. 頁面配置
st.set_page_config(page_title="財經AI快報-手機特務版", page_icon="📱", layout="wide")

# 2. 核心 CSS
st.markdown("""
<style>
/* 隱藏基本的首尾與選單 */
footer {visibility: hidden !important;}
header {visibility: hidden !important;}
#MainMenu {visibility: hidden !important;}

/* 隱藏新版 Streamlit 的標籤 */
[data-testid="stHeader"] {display: none !important;}
[data-testid="stFooter"] {display: none !important;}
[data-testid="stBottom"] {display: none !important;}

/* 專門狙擊右下角的氣球標籤 */
div[class^="viewerBadge"] {display: none !important;}

:root { color-scheme: light !important; --up:#ef4444; --down:#16a34a; --text:#0f172a; --muted:#64748b; --border:#e7ebf3; }
.block-container { padding: 0.8rem 0.6rem !important; }
html, body, [data-testid="stAppViewContainer"] { 
    background-color: #FFFFFF !important; 
    color: #000000 !important; 
    font-family: "HanziPen SC", "翩翩體", "PingFang TC", sans-serif !important; 
    font-size: 18px !important; 
}
p, span, h1, h2, h3, label { color: #000000 !important; }

/* 金色星星專屬樣式 */
.gold-star {
    color: #FFD700 !important; 
    text-shadow: 0px 0px 2px rgba(255, 215, 0, 0.5); 
    font-weight: bold;
    margin: 0 1px;
}

.brand { font-size: 28px; font-weight: 900; color: var(--text); letter-spacing: -0.5px; margin-bottom: 2px;}
.sub { color: var(--muted); font-size: 13px; margin-bottom: 8px; }
.update-time { font-size: 11px; color: #94a3b8; margin-bottom: 12px; }
.combined-table { width: 100%; border-collapse: collapse; text-align: center; margin-bottom: 20px; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 6px rgba(0,0,0,0.08); }
.combined-table th { background: #1e293b; padding: 10px 4px; color: #ffffff !important; font-size: 12px; font-weight: 700; letter-spacing: 1px; }
.combined-table td { padding: 8px 4px; border-bottom: 1px solid #e2e8f0; }
.m-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 20px; }
.m-tile { background: #ffffff; border: 1px solid var(--border); border-radius: 10px; padding: 8px 2px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); transition: all 0.3s ease; }
.m-tile.up-bg { background: #fef2f2 !important; border-color: #fecaca; }
.m-tile.down-bg { background: #f0fdf4 !important; border-color: #bbf7d0; }
.m-name { color: var(--muted) !important; font-size: 9px; white-space: nowrap; letter-spacing: -0.3px; font-weight: 700; }
.m-price { font-size: 16px; font-weight: 900; margin: 3px 0; color: #0f172a !important; letter-spacing: -0.5px; }
.m-pct { font-size: 11px; font-weight: 800; }
.up { color: var(--up) !important; } .down { color: var(--down) !important; }
.timeline-container { border-left: 1px solid #e2e8f0; margin-left: 10px; padding-left: 14px; position: relative; margin-bottom: 20px; }
.timeline-item { position: relative; margin-bottom: 18px; }
.timeline-item::before { content: ''; position: absolute; left: -18.5px; top: 5px; width: 8px; height: 8px; border-radius: 50%; background-color: #000000; border: 2px solid #ffffff; }
.timeline-time { font-size: 11px; color: #94a3b8 !important; font-weight: 700; margin-bottom: 2px; font-family: monospace; }
.timeline-title { font-size: 14px; font-weight: 800; color: #000000 !important; line-height: 1.4; margin-bottom: 0px; text-decoration: none; display: block; }
.timeline-title:hover { color: #000000 !important; text-decoration: underline; }
.timeline-summary { display: none !important; }
</style>
""", unsafe_allow_html=True)

# 3. 數據抓取
@st.cache_data(ttl=60)
def fetch_yf_data(symbol, name):
    try:
        t = yf.Ticker(symbol)
        info = getattr(t, "fast_info", None)
        if info:
            last = getattr(info, "last_price", getattr(info, "lastPrice", None))
            prev = getattr(info, "previous_close", getattr(info, "previousClose", None))
            if last and prev: return {"name": name, "ok": True, "price": last, "pct": ((last-prev)/prev)*100}
    except: pass
    return {"name": name, "ok": False}

@st.cache_data(ttl=600)
def fetch_histock_tables():
    url = "https://histock.tw/stock/three.aspx"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        res.encoding = 'utf-8'
        tables = pd.read_html(io.StringIO(res.text)) 
        
        df_inst, df_fut = None, None
        for tbl in tables:
            if isinstance(tbl.columns, pd.MultiIndex): 
                tbl.columns = [col[-1] for col in tbl.columns]
                
            cols = list(tbl.columns)
            if '外資' in cols and '投信' in cols and '日期' in cols:
                if '自營(總)' in cols: 
                    df_inst = tbl.head(3) # 🌟 縮編回 3 天
                elif '自營' in cols and len(cols) <= 6: 
                    df_fut = tbl.head(3)  # 🌟 縮編回 3 天
                    
        return df_inst, df_fut
    except Exception as e: 
        print(f"⚠️ 抓取外資籌碼失敗: {e}") 
        return None, None

def render_combined_foreign_table(df_inst, df_fut):
    if df_inst is None or df_fut is None: return ""
    
    # 🌟 標題改回近三日
    html = '<div style="font-size:16px; font-weight:900; margin:15px 0 8px 0; color:#1e293b;">🏦 外資籌碼動向 (近三日)</div><table class="combined-table"><tr><th>日期</th><th>現貨買賣(億)</th><th>期貨未平倉(口)</th></tr>'
    
    # 🌟 限制只顯示 3 行
    max_rows = min(3, len(df_inst), len(df_fut))
    
    for i in range(max_rows):
        date_str = df_inst.iloc[i].get('日期', '')
        spot_val = df_inst.iloc[i].get('外資', '')
        fut_val = df_fut.iloc[i].get('外資', '')
        
        def get_color(val_str):
            try: return "#16a34a" if float(str(val_str).replace(',', '')) < 0 else "#ef4444"
            except: return "#0f172a"
            
        spot_color = get_color(spot_val)
        fut_color = get_color(fut_val)
        
        row_style = "font-weight: 900; font-size: 15px; background: linear-gradient(90deg, #fffbeb 0%, #fef3c7 100%);" if i == 0 else "font-size: 13px;"
        date_weight = "font-weight: 900; color: #b45309;" if i == 0 else "color: #64748b;"
        html += f'<tr style="{row_style}"><td style="{date_weight}">{date_str}</td><td style="color: {spot_color};">{spot_val}</td><td style="color: {fut_color};">{fut_val}</td></tr>'
        
    html += '</table>'
    return html

# 4. JSON 讀取
LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"
mode = st.radio("檢視模式", ["最新（今日）", "歷史回顧"], horizontal=True)
data = None

if mode == "最新（今日）":
    if os.path.exists(LATEST_FILE):
        with open(LATEST_FILE, "r", encoding="utf-8") as f: data = json.load(f)
else:
    if os.path.exists(HISTORY_DIR):
        hist_files = sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")], reverse=True)
        if hist_files:
            years = sorted(list(set(f[:4] for f in hist_files)), reverse=True)
            col_y, col_m = st.columns(2)
            with col_y: selected_year = st.selectbox("🗓️ 選擇年份", years, format_func=lambda x: f"{x} 年")
            months = sorted(list(set(f[5:7] for f in hist_files if f.startswith(selected_year))), reverse=True)
            with col_m: selected_month = st.selectbox("📅 選擇月份", months, format_func=lambda x: f"{int(x)} 月")
            prefix = f"{selected_year}-{selected_month}"
            filtered_hist = [f for f in hist_files if f.startswith(prefix)]
            if filtered_hist:
                pick = st.selectbox("📄 選擇報告", filtered_hist, index=0, format_func=lambda x: x.replace(".json", ""))
                with open(os.path.join(HISTORY_DIR, pick), "r", encoding="utf-8") as f: data = json.load(f)
            else: st.warning("該月份尚未產生報告。"); st.stop()
        else: st.warning("尚無歷史資料"); st.stop()

if not data: st.warning("找不到資料檔案。"); st.stop()

# 5. 大標題與語音處理
raw_report = data.get("report", "") or ""

@st.cache_data(show_spinner=False)
def generate_anchor_audio(text):
    if not text: return None
    try:
        clean_text = re.sub(r'<[^>]+>', '', text) 
        clean_text = re.sub(r'作為.*?如下[：:]', '', clean_text, flags=re.DOTALL)
        clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', clean_text).replace("☆", "") 
        clean_text = re.sub(r'★+', lambda m: f"{len(m.group(0))}顆星", clean_text)
        clean_text = re.sub(r'[【】\[\]\(\)（）/\*#\-•]', ' ', clean_text)
        clean_text = clean_text.replace("重挫", "仲挫").replace("重擊", "仲擊").replace("重啟", "蟲啟")
        
        full_script = "即將通往財務自由的大家，歡迎收聽財經快報，以下是曉臻為您帶來的市場重點整理：。 " + clean_text
        
        async def _generate():
            communicate = edge_tts.Communicate(full_script, "zh-TW-HsiaoChenNeural", rate="+10%", pitch="+5Hz")
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio": audio_data += chunk["data"]
            return audio_data
        return asyncio.run(_generate())
    except Exception: return None

audio_bytes = generate_anchor_audio(raw_report)

if audio_bytes:
    b64_audio = base64.b64encode(audio_bytes).decode()
    components.html(f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; padding: 0; margin: 0;">
        <div style="display: flex; align-items: center; margin-bottom: 2px;">
            <div style="font-size: 28px; font-weight: 900; color: #0f172a; letter-spacing: -0.5px;">財經AI快報</div>
            <audio id="anchor-audio" src="data:audio/mp3;base64,{b64_audio}"></audio>
            <button onclick="var a = document.getElementById('anchor-audio'); a.playbackRate = 1.00; if(a.paused){{a.play(); this.innerHTML='⏸️ 暫停快報';}}else{{a.pause(); this.innerHTML='▶️ 收聽快報';}}" 
                    style="background: linear-gradient(135deg, #2563eb, #1e40af); color: white; border: none; border-radius: 50px; padding: 6px 16px; font-size: 14px; font-weight: 800; cursor: pointer; margin-left: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.15); outline: none; transition: 0.2s;">
                ▶️ 收聽快報
            </button>
        </div>
        <div style="color: #64748b; font-size: 13px; margin-bottom: 8px;">每日重點整理（重大事件｜台股影響｜投資觀察）</div>
        <div style="font-size: 11px; color: #94a3b8; margin-bottom: 12px;">最後更新（UTC）：{data.get("updated_at_utc", "")}</div>
    </div>
    """, height=100)
else:
    st.markdown(f'''
    <div class="brand">財經AI快報</div>
    <div class="sub">每日重點整理（重大事件｜台股影響｜投資觀察）</div>
    <div class="update-time">最後更新（UTC）：{data.get("updated_at_utc", "")}</div>
    ''', unsafe_allow_html=True)

# 6. 市場快照
tw_tz = pytz.timezone('Asia/Taipei')
current_tw_time = datetime.now(tw_tz).time()
is_us_market = (current_tw_time >= time(21, 30) or current_tw_time < time(9, 0))

def render_market_grid(title, targets_list):
    html = f'<div style="font-size:16px; font-weight:900; margin:15px 0 8px 0; color:#1e293b;">{title}</div><div class="m-grid">'
    for sym, name in targets_list:
        q = fetch_yf_data(sym, name)
        if q and q.get("ok"):
            pct = q["pct"]
            bg_cls = "up-bg" if pct > 0 else "down-bg" if pct < 0 else ""
            cls = "up" if pct > 0 else "down" if pct < 0 else ""
            sign = "+" if pct > 0 else ""
            html += f'<div class="m-tile {bg_cls}"><div class="m-name">{q["name"]}</div><div class="m-price">{round(q["price"], 1)}</div><div class="m-pct {cls}">{sign}{round(pct, 2)}%</div></div>'
        else: html += f'<div class="m-tile"><div class="m-name">{name}</div><div class="m-price">-</div><div class="m-pct">-</div></div>'
    html += '</div>'
    return html

if is_us_market:
    st.markdown(render_market_grid("🌍 全球市場快照 (美股時段)", [("TSM", "台積電-adr"), ("^DJI", "道瓊工業"), ("^IXIC", "納斯達克"), ("NVDA", "NVIDIA"), ("^SOX", "費半"), ("EWT", "MSCI 台灣")]), unsafe_allow_html=True)
else:
    st.markdown(render_market_grid("👑 護國神山與亞洲指數", [("^TWII", "加權指數"), ("2330.TW", "台積電"), ("2454.TW", "聯發科"), ("^N225", "日經225"), ("^KS11", "韓國綜合"), ("0050.TW", "元大台灣50")]), unsafe_allow_html=True)
    try:
        with open("hot_stocks.json", "r", encoding="utf-8") as f:
            vol_targets = [(k, v) for k, v in json.load(f).get("top_volume_pool", {}).items()][:6]
    except:
        vol_targets = [("3231.TW", "緯創"), ("2603.TW", "長榮"), ("2317.TW", "鴻海"), ("2356.TW", "英業達"), ("2409.TW", "友達"), ("3481.TW", "群創")]
    st.markdown(render_market_grid("🔥 盤中實戰：市場人氣爆量", vol_targets), unsafe_allow_html=True)

# 7. 外資籌碼表
df_inst, df_fut = fetch_histock_tables()
st.markdown(render_combined_foreign_table(df_inst, df_fut), unsafe_allow_html=True)

# 🚨 8. 市場指標橫幅 (6 個燈號微縮 20% 確保手機版不換行 + 更新至 4 月)
risk = data.get("risk_indicators", {})
vix_val = risk.get("vix", "-")
vix_trend = risk.get("vix_trend", "")
usd_val = risk.get("usd_twd", "-") 

light_val = """
<div style="display: flex; gap: 6px; align-items: flex-start; margin-top: 5px; flex-wrap: nowrap; overflow-x: auto; padding-bottom: 2px;">
    <div style="display: flex; flex-direction: column; align-items: center; gap: 4px;">
        <div style="width: 36px; height: 36px; background: radial-gradient(circle at 10px 10px, #ffb366, #e67300); border-radius: 50%; display: flex; justify-content: center; align-items: center; color: white; font-weight: bold; font-size: 14px; box-shadow: 0 4px 8px rgba(230, 115, 0, 0.4); flex-shrink: 0;">37</div>
        <div style="font-size: 11px; font-weight: 700; color: #64748b; white-space: nowrap;">11月</div>
    </div>
    <div style="display: flex; flex-direction: column; align-items: center; gap: 4px;">
        <div style="width: 36px; height: 36px; background: radial-gradient(circle at 10px 10px, #ff4d4d, #cc0000); border-radius: 50%; display: flex; justify-content: center; align-items: center; color: white; font-weight: bold; font-size: 14px; box-shadow: 0 4px 8px rgba(204, 0, 0, 0.4); flex-shrink: 0;">38</div>
        <div style="font-size: 11px; font-weight: 700; color: #64748b; white-space: nowrap;">12月</div>
    </div>
    <div style="display: flex; flex-direction: column; align-items: center; gap: 4px;">
        <div style="width: 36px; height: 36px; background: radial-gradient(circle at 10px 10px, #ff4d4d, #cc0000); border-radius: 50%; display: flex; justify-content: center; align-items: center; color: white; font-weight: bold; font-size: 14px; box-shadow: 0 4px 8px rgba(204, 0, 0, 0.4); flex-shrink: 0;">39</div>
        <div style="font-size: 11px; font-weight: 700; color: #64748b; white-space: nowrap;">1月</div>
    </div>
    <div style="display: flex; flex-direction: column; align-items: center; gap: 4px;">
        <div style="width: 36px; height: 36px; background: radial-gradient(circle at 10px 10px, #ff4d4d, #cc0000); border-radius: 50%; display: flex; justify-content: center; align-items: center; color: white; font-weight: bold; font-size: 14px; box-shadow: 0 4px 8px rgba(204, 0, 0, 0.4); flex-shrink: 0;">40</div>
        <div style="font-size: 11px; font-weight: 700; color: #64748b; white-space: nowrap;">2月</div>
    </div>
    <div style="display: flex; flex-direction: column; align-items: center; gap: 4px;">
        <div style="width: 36px; height: 36px; background: radial-gradient(circle at 10px 10px, #ff4d4d, #cc0000); border-radius: 50%; display: flex; justify-content: center; align-items: center; color: white; font-weight: bold; font-size: 14px; box-shadow: 0 4px 8px rgba(204, 0, 0, 0.4); flex-shrink: 0;">39</div>
        <div style="font-size: 11px; font-weight: 700; color: #64748b; white-space: nowrap;">3月</div>
    </div>
    <div style="display: flex; flex-direction: column; align-items: center; gap: 4px;">
        <div style="width: 36px; height: 36px; background: radial-gradient(circle at 10px 10px, #ff4d4d, #cc0000); border-radius: 50%; display: flex; justify-content: center; align-items: center; color: white; font-weight: bold; font-size: 14px; box-shadow: 0 4px 8px rgba(204, 0, 0, 0.4); flex-shrink: 0;">39</div>
        <div style="font-size: 11px; font-weight: 700; color: #64748b; white-space: nowrap;">4月</div>
    </div>
</div>
"""

market_banner_html = f'''
<div style="background-color: #f8fafc; border-left: 6px solid #1e40af; padding: 22px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 8px 22px rgba(2,6,23,0.05);">
    <div style="font-size: 24px; font-weight: 850; color: #1e40af; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 25px;">📍</span> 市場核心戰略參數
    </div>
    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 20px;">
        <div style="flex: 1.2; min-width: 250px; border-right: 1px solid #e2e8f0; padding-right: 10px;">
            <div style="font-size: 16px; color: #64748b; margin-bottom: 6px;">恐慌指標 / 匯率</div>
            <div style="font-size: 20px; font-weight: 700; color: #0f172a;">
                VIX {vix_val} <span style="font-size:16px; font-weight:normal; color:#64748b;">({vix_trend})</span> 
                <span style="color: #cbd5e1; margin: 0 10px;">|</span> 
                TWD {usd_val}
            </div>
        </div>
        <div style="flex: 1; min-width: 200px;">
            <div style="font-size: 16px; color: #64748b; margin-bottom: 6px;">台灣景氣對策信號</div>
            <div style="font-size: 25px; font-weight: 700; color: #0f172a;">{light_val}</div>
        </div>
    </div>
</div>
'''
st.markdown(market_banner_html, unsafe_allow_html=True)

# 8. 🤖 AI 摘要
st.markdown('<div style="font-size:16px; font-weight:900; margin-bottom:8px; color:#1e293b;">🤖 AI 盤勢快評</div>', unsafe_allow_html=True)

star_html = '<span class="gold-star">★</span>'
processed_report = raw_report.replace("★", star_html)

current_hour = datetime.now(tw_tz).hour
if 14 <= current_hour < 24 or 0 <= current_hour < 5:
    processed_report = processed_report.replace("一分鐘戰略速讀", "盤後戰略精華包").replace("晨報", "盤後戰略")
else:
    processed_report = processed_report.replace("一分鐘戰略速讀", "一分鐘速讀懶人包")

st.markdown(f'''
<div style="background-color: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; padding: 15px; font-size: 15px; line-height: 1.8; color: #0f172a; margin-bottom: 20px; box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);">
    {processed_report}
</div>
''', unsafe_allow_html=True)

# 9. 新聞快報
st.markdown('<div style="font-size:16px; font-weight:900; margin:24px 0 16px 0; color:#1e293b;">📰 24小時即時新聞快報</div>', unsafe_allow_html=True)
news = data.get("news", [])
if news:
    news_html = '<div class="timeline-container">'
    for n in news:
        try: time_display = datetime.fromisoformat(n.get("dt_utc", "").replace('Z', '+00:00')).astimezone(pytz.timezone('Asia/Taipei')).strftime("%H:%M")
        except: time_display = "今日" 
        news_html += f'<div class="timeline-item"><div class="timeline-time">{time_display}</div><a href="{n.get("link", "")}" target="_blank" class="timeline-title">{n.get("title", "")}</a><div class="timeline-summary">{n.get("summary", "")}</div></div>'
    st.markdown(news_html + '</div>', unsafe_allow_html=True)
else:
    st.info("目前無 24 小時內的快訊資料。")
