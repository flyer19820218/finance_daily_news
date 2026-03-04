import json
import os
import math
import re
import requests
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta, time
import pytz
import pandas as pd
import streamlit as st
import yfinance as yf

LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

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

/* 動態變色方塊 */
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

/* === 新增：AI快評專屬淡藍色面板 === */
.panel-blue {
  border: 1px solid #bfdbfe;
  background: #eff6ff; /* 舒適的科技淡藍色 */
  border-radius: 18px;
  padding: 18px 20px;
  box-shadow: 0 4px 15px rgba(37, 99, 235, 0.05); /* 微微的藍色陰影 */
  line-height: 1.6;
}

.news-card{
  border:1px solid var(--border);
  background:#fff;
  border-radius: 16px;
  padding: 10px 12px;
  margin-bottom: 10px;
  box-shadow: var(--shadow2);
  transition: transform .12s ease, box-shadow .12s ease;
}
.news-card:hover{
  transform: translateY(-1px);
  box-shadow: 0 12px 28px rgba(2,6,23,0.08);
}
.small{ color:var(--muted); font-size: 12px; }
.inline-row{
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.35;
  word-break: break-word;
}
.pagerline{
  display:flex;
  align-items:center;
  justify-content:space-between;
  margin: 6px 0 10px 0;
}

/* 倒數卡片專屬 CSS */
.countdown-card {
    max-width: 300px;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 14px;
    background-color: #ffffff;
    box-shadow: var(--shadow2);
}
.card-date {
    font-size: 11px;
    font-weight: bold;
    color: var(--muted);
    margin-bottom: 6px;
}
.card-main {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 6px;
    white-space: nowrap;
}
.card-title {
    font-size: 13px;
    font-weight: bold;
}
.card-days {
    font-size: 17px;
    font-weight: bold;
    margin-left: 8px;
}
.card-progress-bar {
    height: 5px;
    background-color: var(--border);
    border-radius: 3px;
    overflow: hidden;
    margin: 8px 0 6px 0;
}
.card-progress-fill {
    height: 100%;
    background-color: var(--text);
    transition: width 0.5s ease-in-out;
}
.card-progress-details {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
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
  .countdown-card { max-width: 100%; width: 100%; margin-top: 10px; }
}
</style>
""",
    unsafe_allow_html=True,
)

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

def _safe_float(x):
    try:
        if x is None: return None
        return float(x)
    except: return None

@st.cache_data(ttl=60)
def fetch_yf_data(symbol, name):
    try:
        t = yf.Ticker(symbol)
        info = getattr(t, "fast_info", None)
        if info:
            last = getattr(info, "last_price", getattr(info, "lastPrice", None))
            prev = getattr(info, "previous_close", getattr(info, "previousClose", None))
            if last and prev:
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

# === 頁面邏輯 ===
# --- JSON 讀取防呆 ---
mode = st.radio("檢視模式", ["最新（今日）", "歷史回顧"], horizontal=True)

data = None
if mode == "最新（今日）":
    data = load_json(LATEST_FILE)
else:
    hist = list_history()
    if not hist:
        st.warning("尚無歷史資料")
        st.stop()
    pick = st.selectbox("選擇日期", hist, index=0, format_func=lambda x: x.replace(".json", ""))
    data = load_json(os.path.join(HISTORY_DIR, pick))

if not data:
    st.warning("尚未產生報告")
    st.stop()

# --- 頂部區域 ---
header_col1, header_col2 = st.columns([1.5, 0.8], gap="large")

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

# ==================================================
# 🌟 日夜自動切換市場快照 (套用網頁版超美卡片)
# ==================================================
tw_tz = pytz.timezone('Asia/Taipei')
current_tw_time = datetime.now(tw_tz).time()

# 判定時間：21:30 ~ 09:00 為美股時間
time_2130 = time(21, 30)
time_0900 = time(9, 0)
is_us_market = (current_tw_time >= time_2130 or current_tw_time < time_0900)

def render_market_section(title, targets_list):
    st.markdown(f'<div class="section-title">🌍 {title}</div>', unsafe_allow_html=True)
    st.markdown('<div class="cards">', unsafe_allow_html=True)
    
    # 電腦版網頁通常排版較寬，這裡設定一行排 6 個
    cols = st.columns(6)
    for i, (sym, name) in enumerate(targets_list):
        q = fetch_yf_data(sym, name)
        html = render_tile(name, q)
        with cols[i % 6]:
            st.markdown(html, unsafe_allow_html=True)
            
    st.markdown("</div>", unsafe_allow_html=True)

# 依據時間動態渲染 (無縫接軌您的設計)
if is_us_market:
    us_targets = [("TSM", "台積電-adr"), ("YM=F", "道瓊期"), ("NQ=F", "納指期"), ("NVDA", "NVIDIA"), ("^SOX", "費半"), ("EWT", "MSCI 台灣")]
    render_market_section("全球市場快照 (美股時段)", us_targets)
else:
    top6_targets = [("2330.TW", "台積電"), ("2317.TW", "鴻海"), ("2454.TW", "聯發科"), ("2382.TW", "廣達"), ("2308.TW", "台達電"), ("0050.TW", "元大台灣50")]
    render_market_section("護國神山：核心權值 (含0050)", top6_targets)
    
    # 嘗試讀取爆量熱門股
    try:
        with open("hot_stocks.json", "r", encoding="utf-8") as f:
            vol_pool = json.load(f).get("top_volume_pool", {})
            vol_targets = [(k, v) for k, v in vol_pool.items()][:6]
    except:
        vol_targets = [("3231.TW", "緯創"), ("2603.TW", "長榮"), ("2317.TW", "鴻海"), ("2356.TW", "英業達"), ("2409.TW", "友達"), ("3481.TW", "群創")]
    
    render_market_section("盤中實戰：市場人氣爆量", vol_targets)

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# ====== 三大法人與期貨未平倉區塊 ======
df_inst, df_fut = fetch_histock_tables()
if df_inst is not None or df_fut is not None:
    
    ratio_left = len(df_inst.columns) if df_inst is not None else 7
    ratio_right = len(df_fut.columns) if df_fut is not None else 5
    t1, t2 = st.columns([ratio_left, ratio_right], gap="small")
    
    with t1:
        if df_inst is not None:
            st.markdown(render_table_html(df_inst, "近五日上市三大法人買賣超 (億)", "🏦"), unsafe_allow_html=True)
    with t2:
        if df_fut is not None:
            st.markdown(render_table_html(df_fut, "近五日台股期貨未平倉 (口)", "📈"), unsafe_allow_html=True)
            
st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
# ==========================================

left, right = st.columns([1.35, 0.65], gap="large")
with left:
    st.markdown('<div class="section-title">🤖 AI 盤勢快評</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel-blue">', unsafe_allow_html=True)
    st.markdown(data.get("report", ""))
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-title">📰 新聞清單</div>', unsafe_allow_html=True)
    news = data.get("news", []) or []
    page_size = 10
    total = len(news)
    total_pages = max(1, math.ceil(total / page_size))
    if "news_page" not in st.session_state: st.session_state.news_page = 1
    st.session_state.news_page = max(1, min(st.session_state.news_page, total_pages))

    st.markdown(f"<div class='pagerline'><div class='small'>第 {st.session_state.news_page} / {total_pages} 頁（共 {total} 則）</div></div>", unsafe_allow_html=True)

    if total_pages <= 2:
        try:
            sel = st.segmented_control("分頁", options=[1, 2], format_func=lambda x: f"第 {x} 頁", selection_mode="single", default=st.session_state.news_page, label_visibility="collapsed")
        except:
            sel = st.radio("分頁", options=[1, 2], format_func=lambda x: f"第 {x} 頁", horizontal=True, index=st.session_state.news_page - 1, label_visibility="collapsed")
        if sel and sel != st.session_state.news_page:
            st.session_state.news_page = int(sel); st.rerun()
    else:
        c1, c2 = st.columns([1, 1])
        with c1: 
            if st.button("← 上一頁", use_container_width=True, disabled=(st.session_state.news_page <= 1)):
                st.session_state.news_page -= 1; st.rerun()
        with c2:
            if st.button("下一頁 →", use_container_width=True, disabled=(st.session_state.news_page >= total_pages)):
                st.session_state.news_page += 1; st.rerun()

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    start = (st.session_state.news_page - 1) * page_size
    for n in news[start:start+page_size]:
        title = (n.get("title") or "").strip()
        link = (n.get("link") or "").strip()
        source = urlparse(link).netloc.replace("www.", "") if link else ""
        st.markdown('<div class="news-card">', unsafe_allow_html=True)
        st.markdown(f"**{title}**")
        parts = []
        if source: parts.append(f"<span>{source}</span>")
        if link: parts.append(f"<a href='{link}' target='_blank'>閱讀原文</a>")
        if parts:
            row = " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(parts)
            st.markdown(f"<div class='inline-row'>{row}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
