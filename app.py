# =====================================================================
# 【區塊 1】套件匯入與基礎設定
# =====================================================================
import json
import os
import math
import re
import requests
import base64
import asyncio
import edge_tts
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta, time
import pytz
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf

LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

# =====================================================================
# 【區塊 2】全域 CSS 樣式定義 (視覺規範)
# =====================================================================
st.markdown(
    """
<style>
:root{
  --bg:#ffffff;
  --panel:#f7f9fc;
  --border:#e7ebf3;
  --text:#0f172a;
  --muted:#64748b;
  --muted2:#94a3b8;
  --up:#16a34a;
  --down:#ef4444;
  --link:#2563eb;
  --pill:#eef2ff;
  --shadow: 0 10px 30px rgba(2,6,23,0.06);
  --shadow2: 0 8px 22px rgba(2,6,23,0.05);
  color-scheme: light;
}

.stApp{
  background:var(--bg);
  color:var(--text);
  font-family:
    "翩翩體",
    "PianPian",
    "PingFang TC",
    "PingFang SC",
    "Noto Sans TC",
    "Noto Sans CJK TC",
    "Microsoft JhengHei",
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;
}

html, body, [class*="css"]{
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

a{ color:var(--link) !important; text-decoration:none; }
a:hover{ text-decoration:underline; }

.block-container{
  padding-top: 1.2rem;
  padding-bottom: 2.2rem;
  max-width: 1180px;
}

.header{
  display:flex;
  justify-content:space-between;
  align-items:flex-end;
  gap:14px;
  padding: 6px 0 12px 0;
}

.brand{
  font-size: 34px;
  font-weight: 900;
  letter-spacing: -0.4px;
  line-height: 1.15;
  word-break: keep-all;
  overflow-wrap: normal;
  white-space: normal;
  max-width: 100%;
}

.sub{
  color:var(--muted);
  font-size: 13px;
  margin-top: 6px;
}

.badge{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding: 8px 12px;
  border:1px solid var(--border);
  border-radius: 999px;
  background: #fff;
  color: var(--muted);
  font-size: 12px;
  white-space: nowrap;
  box-shadow: 0 6px 18px rgba(2,6,23,0.06);
}

.hr{ height:1px; background:var(--border); margin: 18px 0; }

.section-title{
  font-size: 16px;
  font-weight: 850;
  letter-spacing: -0.1px;
  margin: 10px 0 10px 0;
}

.cards{
  border:1px solid var(--border);
  background: var(--panel);
  border-radius: 18px;
  padding: 14px;
  box-shadow: var(--shadow);
  margin-bottom: 20px;
}

.tile{
  background:#fff;
  border:1px solid var(--border);
  border-radius: 16px;
  padding: 12px 12px;
  height: 100%;
  box-shadow: var(--shadow2);
  transition: all 0.3s ease;
}
.tile:hover{
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(2,6,23,0.08);
}
.tile.up-bg { background: #f0fdf4; border-color: #bbf7d0; }
.tile.down-bg { background: #fef2f2; border-color: #fecaca; }

.name{ color:var(--muted); font-size: 12px; margin-bottom: 2px; font-weight: 700; }
.price{
  font-size: 22px;
  font-weight: 950;
  margin: 2px 0 6px 0;
  letter-spacing: -0.2px;
}
.delta{ font-size: 13px; font-weight: 800; }
.up{ color:var(--up); }
.down{ color:var(--down); }
.flat{ color:var(--muted2); }

.panel{
  border:1px solid var(--border);
  background: #fff;
  border-radius: 18px;
  padding: 16px 16px;
  box-shadow: var(--shadow);
}

.panel-blue {
  border: 1px solid #bfdbfe;
  background: #eff6ff; 
  border-radius: 18px;
  padding: 18px 20px;
  box-shadow: 0 4px 15px rgba(37, 99, 235, 0.05); 
  line-height: 1.6;
}

.news-card{
  border: none !important;
  border-bottom: 1px solid #f0f0f0 !important;
  background: transparent !important;
  border-radius: 0px !important;
  padding: 10px 0px !important;
  margin-bottom: 4px;
  box-shadow: none !important;
  transition: none !important;
}
.news-card:hover{
  transform: none !important;
  box-shadow: none !important;
}

.news-summary {
  display: none !important;
}

.small{ 
  color: #94a3b8 !important; 
  font-size: 11px; 
}

.inline-row{
  margin-top: 2px;
  font-size: 11px;
  color: #94a3b8 !important;
  line-height: 1.3;
}

.pagerline{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 4px 0 8px 0;
  padding-bottom: 4px;
  border-bottom: 2px solid #000;
}

.news-card a {
  color: #000000 !important;
  font-weight: 700 !important;
  text-decoration: none !important;
}

/* 🌟 統一按鈕風格：最美漸層藍 🌟 */
button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb, #1e40af) !important;
    color: white !important;
    border: none !important;
    border-radius: 50px !important;
    height: 44px !important; /* 🚨 強制鎖死高度 */
    padding: 0 24px !important;
    font-size: 15px !important;
    font-weight: 800 !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: all 0.2s ease !important;
}
button[kind="primary"]:hover {
    opacity: 0.9;
    transform: translateY(-2px);
    color: white !important;
    text-decoration: none !important;
}

.countdown-card {
    max-width: 320px; /* 解放寬度封印 */
    margin-left: auto; 
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 20px; 
    background-color: #ffffff;
    box-shadow: var(--shadow2);
}
.card-date {
    font-size: 13px; 
    font-weight: bold;
    color: var(--muted);
    margin-bottom: 10px; 
}
.card-main {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 10px; 
    white-space: nowrap;
}
.card-title {
    font-size: 15px; 
    font-weight: bold;
}
.card-days {
    font-size: 22px; 
    font-weight: 900;
    margin-left: 8px;
    color: var(--text);
}
.card-progress-bar {
    height: 6px; 
    background-color: var(--border);
    border-radius: 3px;
    overflow: hidden;
    margin: 14px 0 10px 0; 
}
.card-progress-fill {
    height: 100%;
    background-color: var(--text);
    transition: width 0.5s ease-in-out;
}
.card-progress-details {
    display: flex;
    justify-content: space-between;
    font-size: 12px; 
    color: var(--muted);
}

@media (max-width: 768px){
  .block-container{ padding-left: 0.9rem; padding-right: 0.9rem; }
  .header{
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  .brand{
    font-size: 28px;
    letter-spacing: -0.2px;
  }
  .sub{ font-size: 12px; }
  .badge{
    font-size: 11px;
    padding: 7px 10px;
    white-space: normal;
  }
  .section-title{ font-size: 14px; }
  .price{ font-size: 20px; }
  .delta{ font-size: 12px; }
  .inline-row{ font-size: 12px; }
  .countdown-card { max-width: 100%; width: 100%; padding: 16px; margin-top: 10px; margin-left: 0; }
}
</style>
""",
    unsafe_allow_html=True,
)

# =====================================================================
# 【區塊 3】資料讀取與快取函數定義
# =====================================================================
@st.cache_data(ttl=60)
def load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def list_history():
    if not os.path.exists(HISTORY_DIR):
        return []
    files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")]
    files.sort(reverse=True)
    return files

@st.cache_data(ttl=60)
def fetch_yf_data(symbol, name):
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="5d")
        if not hist.empty and len(hist) >= 2:
            last = float(hist['Close'].iloc[-1])
            prev = float(hist['Close'].iloc[-2])
            return {"name": name, "ok": True, "price": last, "change": last-prev, "pct": ((last-prev)/prev)*100}
    except: pass
    return {"name": name, "ok": False}

def render_tile(name, q):
    render_ok = q and q.get("ok") and q.get("price") is not None
    if not render_ok:
        return f'<div class="tile"><div class="name">{name}</div><div class="price">-</div><div class="delta flat">-</div></div>'

    ch, pct, price = q.get("change") or 0.0, q.get("pct") or 0.0, q.get("price")
    
    cls = "up" if ch > 0 else "down" if ch < 0 else "flat"
    bg_cls = "up-bg" if ch > 0 else "down-bg" if ch < 0 else ""
    arrow = "▲" if ch > 0 else "▼" if ch < 0 else "—"

    return f"""
    <div class="tile {bg_cls}">
      <div class="name">{name}</div>
      <div class="price">{round(float(price), 2)}</div>
      <div class="delta {cls}">{arrow} {round(float(ch), 2)}（{round(float(pct), 2)}%）</div>
    </div>
    """

def generate_countdown_html(start_year=2026, target_year=2035):
    tw_tz = timezone(timedelta(hours=8))
    today = datetime.now(tw_tz)
    start_date = datetime(start_year, 1, 1, tzinfo=tw_tz)
    target_date = datetime(target_year, 12, 31, tzinfo=tw_tz)
    
    if today < start_date: today = start_date
    elif today > target_date: today = target_date
        
    total_days = (target_date - start_date).days
    passed_days = (today - start_date).days
    days_remaining_int = (target_date - today).days
    
    days_remaining = f"{days_remaining_int:,}" 
    progress_percentage = round((passed_days / total_days) * 100, 2)
    today_date_str = today.strftime("%Y-%m-%d")
    
    return f"""
    <div class="countdown-card">
        <div class="card-date">📅 今日：{today_date_str}</div>
        <div class="card-main">
            <div class="card-title">🎯 {target_year} 財務自由倒數</div>
            <div class="card-days">{days_remaining} 天</div>
        </div>
        <div class="card-progress-bar">
            <div class="card-progress-fill" style="width: {progress_percentage}%;"></div>
        </div>
        <div class="card-progress-details">
            <div>起點：{start_year}</div>
            <div>進度 {progress_percentage}%</div>
        </div>
    </div>
    """

@st.cache_data(ttl=600)
def fetch_histock_tables():
    url = "https://histock.tw/stock/three.aspx"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        tables = pd.read_html(res.text)
        
        df_inst, df_fut = None, None
        for tbl in tables:
            if isinstance(tbl.columns, pd.MultiIndex):
                tbl.columns = [col[-1] for col in tbl.columns]
                
            cols = list(tbl.columns)
            if '外資' in cols and '投信' in cols and '總計' in cols:
                if '自營(總)' in cols:
                    df_inst = tbl.head(5) 
                elif '自營' in cols and len(cols) == 5:
                    df_fut = tbl.head(5)  
                    
        return df_inst, df_fut
    except Exception as e:
        return None, None

def render_table_html(df, title, icon="📊"):
    if df is None or df.empty: return ""
    col_width = 100 / len(df.columns)
        
    html = f"""
    <div class="panel" style="margin-bottom: 16px; padding: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
        <div class="section-title" style="margin-top: 0; margin-bottom: 12px;">{icon} {title}</div>
        <div style="overflow-x: auto; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: 0 2px 6px rgba(0,0,0,0.02);">
            <table style="width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 13px; text-align: right; background: #fff;">
                <thead>
                    <tr style="background-color: #1e293b; color: #ffffff;">
    """
    for col in df.columns:
        align = "center" if col == "日期" else "right"
        html += f'<th style="width: {col_width:.2f}%; padding: 10px 6px; text-align: {align}; font-weight: 700; letter-spacing: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{col}</th>'
    html += "</tr></thead><tbody>"
    
    for i, row in df.iterrows():
        if i == 0:
            bg_color = "linear-gradient(90deg, #fffbeb 0%, #fef3c7 100%)"
            date_color = "#b45309"
            row_weight = "900"
            font_size = "14px"
        else:
            bg_color = "#ffffff" if i % 2 == 0 else "#f8fafc"
            date_color = "inherit"
            row_weight = "normal"
            font_size = "13px"

        html += f'<tr style="background: {bg_color}; border-bottom: 1px solid #e2e8f0; font-weight: {row_weight}; font-size: {font_size};">'
        
        for col in df.columns:
            val = row[col]
            align = "center" if col == "日期" else "right"
            
            style = f"padding: 10px 6px; text-align: {align};"
            
            if col == "日期" and i == 0:
                 style += f" color: {date_color};"
                 
            try:
                num_str = str(val).replace(',', '')
                if num_str.replace('.', '', 1).replace('-', '', 1).isdigit():
                    num = float(num_str)
                    if num > 0:
                        style += " color: #ef4444; font-weight: 700;"
                    elif num < 0:
                        style += " color: #16a34a; font-weight: 700;"
            except: pass
                
            html += f'<td style="{style} overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{val}</td>'
        html += "</tr>"
        
    html += "</tbody></table></div></div>"
    return html

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

# =====================================================================
# 【區塊 4 & 5】佈局調整：選項、資料載入與按鈕雙子星
# =====================================================================
top_c1, top_c2, top_c3 = st.columns([5, 1.5, 1.5], gap="medium") 

with top_c1:
    st.markdown('<div class="section-title" style="margin-top: 0;">📊 檢視模式</div>', unsafe_allow_html=True)
    mode = st.radio("檢視模式", ["最新（今日）", "歷史回顧"], horizontal=True, label_visibility="collapsed")

data = None
if mode == "最新（今日）":
    current_ts = datetime.now().timestamp()
    raw_url = f"https://raw.githubusercontent.com/您的帳號/專案名稱/main/data/latest_report.json?t={current_ts}"
    try:
        res = requests.get(raw_url, timeout=5)
        if res.status_code == 200:
            data = res.json()
        else:
            data = load_json(LATEST_FILE)
    except:
        data = load_json(LATEST_FILE)
else:
    hist = list_history()
    if not hist:
        st.warning("尚無歷史資料"); st.stop()
    years = []
    for f in hist:
        y = f[:4] 
        if y not in years: years.append(y)
    col_y, col_m, col_d = st.columns(3)
    with col_y: selected_year = st.selectbox("🗓️ 選擇年份", years, format_func=lambda x: f"{x} 年")
    months = []
    for f in hist:
        if f.startswith(selected_year):
            m = f[5:7] 
            if m not in months: months.append(m)
    with col_m: selected_month = st.selectbox("📅 選擇月份", months, format_func=lambda x: f"{int(x)} 月")
    prefix = f"{selected_year}-{selected_month}"
    filtered_hist = [f for f in hist if f.startswith(prefix)]
    with col_d:
        if filtered_hist:
            pick = st.selectbox("📄 選擇報告", filtered_hist, index=0, format_func=lambda x: x.replace(".json", ""))
            data = load_json(os.path.join(HISTORY_DIR, pick))
        else:
            st.warning("該月份尚未產生報告。"); st.stop()

if not data: st.warning("尚未產生報告"); st.stop()

raw_report = data.get("report", "") or ""
audio_bytes = generate_anchor_audio(raw_report) 

with top_c2:
    st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True) 
    if audio_bytes:
        b64_audio = base64.b64encode(audio_bytes).decode()
        components.html(f"""
        <style>body {{ margin: 0; padding: 0; overflow: hidden; }}</style>
        <div style="display: flex; align-items: center; justify-content: center; width: 100%;">
            <audio id="anchor-audio" src="data:audio/mp3;base64,{b64_audio}"></audio>
            <button onclick="var a = document.getElementById('anchor-audio'); a.playbackRate = 1.00; if(a.paused){{a.play(); this.innerHTML='⏸️ 暫停快報';}}else{{a.pause(); this.innerHTML='▶️ 收聽快報';}}" 
                    style="background: linear-gradient(135deg, #2563eb, #1e40af); color: white; border: none; border-radius: 50px; height: 44px; width: 100%; font-size: 15px; font-weight: 800; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.15); outline: none; transition: 0.2s; font-family: system-ui, -apple-system, sans-serif; display: flex; align-items: center; justify-content: center; padding: 0;">
                ▶️ 收聽快報
            </button>
        </div>
        """, height=46)

with top_c3:
    st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True) 
    if st.button("🔄 重新整理", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown('<div class="hr" style="margin-top: 0px; margin-bottom: 20px;"></div>', unsafe_allow_html=True)

# =====================================================================
# 【區塊 6】頁面主標題與倒數計時卡片
# =====================================================================
header_col1, header_col2 = st.columns([1.5, 1], gap="large") 

with header_col1:
    st.markdown(
        f"""
        <div class="header" style="flex-direction: column; align-items: flex-start; padding-bottom: 0;">
          <div>
            <div class="brand">財經AI快報</div>
            <div class="sub">每日市場重點整理（重大事件｜台股影響｜投資觀察）</div>
          </div>
          <div class="badge" style="margin-top: 10px;">最後更新（UTC）：{data.get("updated_at_utc", "")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with header_col2:
    st.markdown(generate_countdown_html(), unsafe_allow_html=True)

st.markdown('<div class="hr" style="margin-top: 24px;"></div>', unsafe_allow_html=True) 

# =====================================================================
# 【區塊 7】全球市場快照 (日夜動態切換)
# =====================================================================
tw_tz_snapshot = pytz.timezone('Asia/Taipei')
current_tw_time_snapshot = datetime.now(tw_tz_snapshot).time()

time_2130_snapshot = time(21, 30)
time_0900_snapshot = time(9, 0)
is_us_market_snapshot = (current_tw_time_snapshot >= time_2130_snapshot or current_tw_time_snapshot < time_0900_snapshot)

def render_market_section_dynamic(title, targets_list):
    st.markdown(f'<div class="section-title">🌍 {title}</div>', unsafe_allow_html=True)
    st.markdown('<div class="cards">', unsafe_allow_html=True)
    
    cols = st.columns(6)
    for i, (sym, name) in enumerate(targets_list):
        q = fetch_yf_data(sym, name)
        html = render_tile(name, q)
        with cols[i % 6]:
            st.markdown(html, unsafe_allow_html=True)
            
    st.markdown("</div>", unsafe_allow_html=True)

if is_us_market_snapshot:
    us_targets = [("TSM", "台積電-adr"), ("^DJI", "道瓊工業"), ("^IXIC", "納斯達克"), ("NVDA", "NVIDIA"), ("^SOX", "費半"), ("EWT", "MSCI 台灣")]
    render_market_section_dynamic("全球市場快照 (美股時段)", us_targets)
else:
    top6_targets = [("^TWII", "加權指數"), ("2330.TW", "台積電"), ("2454.TW", "聯發科"), ("^N225", "日經225"), ("^KS11", "韓國綜合"), ("0050.TW", "元大台灣50")]
    render_market_section_dynamic("護國神山與亞洲指數", top6_targets)
    
    try:
        with open("hot_stocks.json", "r", encoding="utf-8") as f:
            vol_pool = json.load(f).get("top_volume_pool", {})
            vol_targets = [(k, v) for k, v in vol_pool.items()][:6]
    except:
        vol_targets = [("3231.TW", "緯創"), ("2603.TW", "長榮"), ("2317.TW", "鴻海"), ("2356.TW", "英業達"), ("2409.TW", "友達"), ("3481.TW", "群創")]
    
    render_market_section_dynamic("盤中實戰：市場人氣爆量", vol_targets)

st.markdown('<div class="hr"></div>', unsafe_allow_html=True) 

# =====================================================================
# 【區塊 8】三大法人與期貨籌碼表格
# =====================================================================
df_inst, df_fut = fetch_histock_tables()
if df_inst is not None or df_fut is not None:
    ratio_left_inst = len(df_inst.columns) if df_inst is not None else 7
    ratio_right_fut = len(df_fut.columns) if df_fut is not None else 5
    t1_df, t2_df = st.columns([ratio_left_inst, ratio_right_fut], gap="small")
    
    with t1_df:
        if df_inst is not None:
            st.markdown(render_table_html(df_inst, "近五日上市三大法人買賣超 (億)", "🏦"), unsafe_allow_html=True)
    with t2_df:
        if df_fut is not None:
            st.markdown(render_table_html(df_fut, "近五日台股期貨未平倉 (口)", "📈"), unsafe_allow_html=True)
            
st.markdown('<div class="hr"></div>', unsafe_allow_html=True) 

# =====================================================================
# 【區塊 9】頁面主體：AI 盤勢快評與即時新聞分頁
# =====================================================================
left_ai, right_news = st.columns([1.35, 0.65], gap="large")

with left_ai:
    
# --- 🌟 市場關鍵指標橫幅 ---
    risk = data.get("risk_indicators", {})
    vix_val = risk.get("vix", "-")
    vix_trend = risk.get("vix_trend", "")
    usd_val = risk.get("usd_twd", "-") 
    
    # 🚨 帶有月份標示的 6 顆霸氣燈號 (9月至2月)
    light_val = """
    <div style="display: flex; gap: 12px; align-items: flex-start; margin-top: 5px; flex-wrap: wrap;">
        <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
            <div style="width: 40px; height: 40px; background: radial-gradient(circle at 12px 12px, #ffb347, #ff8c00); border-radius: 50%; display: flex; justify-content: center; align-items: center; color: white; font-weight: bold; font-size: 16px; box-shadow: 0 4px 8px rgba(255, 140, 0, 0.4);">32</div>
            <div style="font-size: 13px; font-weight: 700; color: #64748b;">9月</div>
        </div>
        <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
            <div style="width: 40px; height: 40px; background: radial-gradient(circle at 12px 12px, #ffb347, #ff8c00); border-radius: 50%; display: flex; justify-content: center; align-items: center; color: white; font-weight: bold; font-size: 16px; box-shadow: 0 4px 8px rgba(255, 140, 0, 0.4);">35</div>
            <div style="font-size: 13px; font-weight: 700; color: #64748b;">10月</div>
        </div>
        <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
            <div style="width: 40px; height: 40px; background: radial-gradient(circle at 12px 12px, #ffb347, #ff8c00); border-radius: 50%; display: flex; justify-content: center; align-items: center; color: white; font-weight: bold; font-size: 16px; box-shadow: 0 4px 8px rgba(255, 140, 0, 0.4);">37</div>
            <div style="font-size: 13px; font-weight: 700; color: #64748b;">11月</div>
        </div>
        <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
            <div style="width: 40px; height: 40px; background: radial-gradient(circle at 12px 12px, #ff4d4d, #cc0000); border-radius: 50%; display: flex; justify-content: center; align-items: center; color: white; font-weight: bold; font-size: 16px; box-shadow: 0 4px 8px rgba(204, 0, 0, 0.4);">38</div>
            <div style="font-size: 13px; font-weight: 700; color: #64748b;">12月</div>
        </div>
        <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
            <div style="width: 40px; height: 40px; background: radial-gradient(circle at 12px 12px, #ff4d4d, #cc0000); border-radius: 50%; display: flex; justify-content: center; align-items: center; color: white; font-weight: bold; font-size: 16px; box-shadow: 0 4px 8px rgba(204, 0, 0, 0.4);">39</div>
            <div style="font-size: 13px; font-weight: 700; color: #64748b;">1月</div>
        </div>
        <div style="display: flex; flex-direction: column; align-items: center; gap: 6px;">
            <div style="width: 40px; height: 40px; background: radial-gradient(circle at 12px 12px, #ff4d4d, #cc0000); border-radius: 50%; display: flex; justify-content: center; align-items: center; color: white; font-weight: bold; font-size: 16px; box-shadow: 0 4px 8px rgba(204, 0, 0, 0.4);">40</div>
            <div style="font-size: 13px; font-weight: 700; color: #64748b;">2月</div>
        </div>
    </div>
    """

    # 🚨 解決換行問題：左側加上 nowrap 屬性，並將整體對齊改為 flex-start 防止跑版
    market_banner_html = f'''
    <div style="background-color: #f8fafc; border-left: 6px solid #1e40af; padding: 20px; border-radius: 12px; margin-bottom: 25px; box-shadow: var(--shadow2);">
        <div style="font-size: 15px; font-weight: 850; color: #1e40af; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 18px;">📍</span> 市場核心戰略參數
        </div>
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 20px;">
            <div style="flex: 1; min-width: 220px; border-right: 1px solid #e2e8f0; padding-right: 10px;">
                <div style="font-size: 12px; color: #64748b; margin-bottom: 4px;">恐慌指標 / 匯率</div>
                <div style="font-size: 18px; font-weight: 700; color: #0f172a; white-space: nowrap;">
                    VIX {vix_val} <span style="font-size:13px; font-weight:normal; color:#64748b;">({vix_trend})</span> 
                    <span style="color: #cbd5e1; margin: 0 10px;">|</span> 
                    TWD {usd_val}
                </div>
            </div>
            <div style="flex: 1.3; min-width: 300px;">
                <div style="font-size: 12px; color: #64748b; margin-bottom: 4px;">台灣景氣對策信號 (近半年)</div>
                <div style="font-size: 18px; font-weight: 700; color: #0f172a;">{light_val}</div>
            </div>
        </div>
    </div>
    '''
    st.markdown(market_banner_html, unsafe_allow_html=True)
    # --- 🌟 🤖 AI 盤勢快評 ---
    st.markdown('<div class="section-title">🤖 AI 盤勢快評</div>', unsafe_allow_html=True)
    
    gold_star_html = '<span style="color: #FFD700; font-weight: bold;">★</span>'
    processed_report = raw_report.replace("★", gold_star_html)
    
    tw_tz = pytz.timezone('Asia/Taipei')
    current_hour = datetime.now(tw_tz).hour

    if current_hour >= 14 or current_hour < 5:
        processed_report = processed_report.replace("一分鐘晨報速讀", "盤後戰略精華包")
        processed_report = processed_report.replace("一分鐘戰略速讀", "盤後戰略精華包")
        processed_report = processed_report.replace("一分鐘晨報", "盤後戰略精華包")
        processed_report = processed_report.replace("晨報速讀", "盤後戰略精華")
    else:
        processed_report = processed_report.replace("一分鐘晨報速讀", "一分鐘速讀懶人包")
        processed_report = processed_report.replace("一分鐘戰略速讀", "一分鐘速讀懶人包")
        processed_report = processed_report.replace("一分鐘晨報", "一分鐘速讀懶人包")
    
    final_html = f'<div class="panel-blue">\n\n{processed_report}\n\n</div>'
    st.markdown(final_html, unsafe_allow_html=True)

with right_news:
    st.markdown('<div class="section-title">📰 即時新聞</div>', unsafe_allow_html=True)
    news_list = data.get("news", []) or []
    
    page_size = 30
    total_news = len(news_list)
    total_pages_news = max(1, math.ceil(total_news / page_size))
    if "news_page" not in st.session_state: st.session_state.news_page = 1
    st.session_state.news_page = max(1, min(st.session_state.news_page, total_pages_news))

    st.markdown(f"<div class='pagerline'><div class='small'>第 {st.session_state.news_page} / {total_pages_news} 頁（共 {total_news} 則）</div></div>", unsafe_allow_html=True)

    if total_pages_news <= 2:
        try:
            sel_page = st.segmented_control("分頁", options=[1, 2], format_func=lambda x: f"第 {x} 頁", selection_mode="single", default=st.session_state.news_page, label_visibility="collapsed")
        except:
            sel_page = st.radio("分頁", options=[1, 2], format_func=lambda x: f"第 {x} 頁", horizontal=True, index=st.session_state.news_page - 1, label_visibility="collapsed")
        if sel_page and sel_page != st.session_state.news_page:
            st.session_state.news_page = int(sel_page); st.rerun()
    else:
        pager1, pager2 = st.columns([1, 1])
        with pager1: 
            if st.button("← 上一頁", use_container_width=True, key="pager_prev", disabled=(st.session_state.news_page <= 1)):
                st.session_state.news_page -= 1; st.rerun()
        with pager2:
            if st.button("下一頁 →", use_container_width=True, key="pager_next", disabled=(st.session_state.news_page >= total_pages_news)):
                st.session_state.news_page += 1; st.rerun()

    st.markdown('<div class="hr" style="margin: 10px 0;"></div>', unsafe_allow_html=True) 
    
    start_news = (st.session_state.news_page - 1) * page_size
    
    for n in news_list[start_news:start_news+page_size]:
        news_title = (n.get("title") or "").strip()
        news_link = (n.get("link") or "").strip()
        news_source = urlparse(news_link).netloc.replace("www.", "") if news_link else ""
        
        dt_str = n.get("dt_utc", "")
        try:
            dt_utc = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            dt_tw = dt_utc.astimezone(pytz.timezone('Asia/Taipei'))
            time_display = dt_tw.strftime("%m/%d %H:%M") 
        except:
            time_display = ""
            
        parts_row = []
        if time_display: parts_row.append(f"<span style='color:#64748b; font-family:monospace; font-weight:bold;'>{time_display}</span>")
        if news_source: parts_row.append(f"<span>{news_source}</span>")
        if news_link: parts_row.append(f"<a href='{news_link}' target='_blank'>閱讀原文</a>")
        news_parts_row = " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(parts_row)
        
        card_html = f'''
        <div class="news-card">
            <a href="{news_link}" target="_blank" style="font-size:15px; font-weight:850; color:#0f172a; text-decoration:none; display:block; margin-bottom:6px; line-height:1.4;">{news_title}</a>
            <div class="inline-row">{news_parts_row}</div>
        </div>
        '''
        st.markdown(card_html, unsafe_allow_html=True)
