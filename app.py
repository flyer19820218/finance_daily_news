import json
import os
import math
import re
import requests
from urllib.parse import urlparse
from datetime import datetime

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
  font-size: 15px;
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
}
.tile{
  background:#fff;
  border:1px solid var(--border);
  border-radius: 16px;
  padding: 12px 12px;
  height: 100%;
  box-shadow: var(--shadow2);
  transition: transform .12s ease, box-shadow .12s ease;
}
.tile:hover{
  transform: translateY(-1px);
  box-shadow: 0 12px 28px rgba(2,6,23,0.08);
}
.name{ color:var(--muted); font-size: 12px; margin-bottom: 2px; }
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

@st.cache_data(ttl=60)
def fetch_ftx_wantgoo():
    """從玩股網抓取富台指即時報價，若失敗則自動切換為 MSCI 台灣 (EWT) 備援"""
    url = "https://www.wantgoo.com/global/indices/ftx"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.wantgoo.com/"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        p = re.search(r'"price":\s*"?([0-9,.]+)"?', res.text)
        c = re.search(r'"change":\s*"?([0-9,.-]+)"?', res.text)
        cp = re.search(r'"changePercent":\s*"?([0-9,.-]+)"?', res.text)
        if p:
            price = float(p.group(1).replace(',', ''))
            change = float(c.group(1)) if c else 0.0
            pct = float(cp.group(1).replace('%', '')) if cp else 0.0
            return {"ok": True, "price": price, "change": change, "pct": pct, "is_fallback": False}
    except:
        pass

    try:
        t = yf.Ticker("EWT")
        fi = getattr(t, "fast_info", None)
        if fi:
            last = _safe_float(fi.get("last_price") or fi.get("lastPrice"))
            prev = _safe_float(fi.get("previous_close") or fi.get("previousClose"))
            if last is not None and prev is not None:
                change = last - prev
                pct = (change / prev * 100) if prev != 0 else 0.0
                return {"ok": True, "price": last, "change": change, "pct": pct, "is_fallback": True}
    except:
        pass

    return {"ok": False}

SYMBOLS_OTHERS = [
    ("費半（SOX）", ["^SOX"]),
    ("道瓊期（YM）", ["YM=F"]),
    ("納指期（NQ）", ["NQ=F"]),
    ("台積電 ADR（TSM）", ["TSM"]),
    ("NVIDIA（NVDA）", ["NVDA"]),
]

def _safe_float(x):
    try:
        if x is None: return None
        return float(x)
    except: return None

@st.cache_data(ttl=60)
def yf_quote_any(tickers):
    for tk in tickers:
        try:
            t = yf.Ticker(tk)
            fi = getattr(t, "fast_info", None)
            last = None
            prev = None
            if fi:
                last = _safe_float(fi.get("last_price") or fi.get("lastPrice"))
                prev = _safe_float(fi.get("previous_close") or fi.get("previousClose"))
            if last is None:
                hist = t.history(period="2d", interval="1d")
                if hist is not None and len(hist) >= 1:
                    last = _safe_float(hist["Close"].iloc[-1])
                    if len(hist) >= 2: prev = _safe_float(hist["Close"].iloc[-2])
            if last is not None:
                ch = (last - prev) if prev is not None else None
                pct = (ch / prev * 100) if (ch is not None and prev not in (None, 0)) else None
                return {"ok": True, "price": last, "change": ch, "pct": pct}
        except: continue
    return {"ok": False}

def render_tile(name, q):
    render_ok = q and q.get("ok") and q.get("price") is not None
    if not render_ok:
        return f'<div class="tile"><div class="name">{name}</div><div class="price">-</div><div class="delta flat">-</div></div>'

    ch, pct, price = q.get("change") or 0.0, q.get("pct") or 0.0, q.get("price")
    cls = "up" if ch > 0 else "down" if ch < 0 else "flat"
    arrow = "▲" if ch > 0 else "▼" if ch < 0 else "—"

    display_name = "MSCI 台灣 (EWT 備援)" if q.get("is_fallback") else name

    return f"""
    <div class="tile">
      <div class="name">{display_name}</div>
      <div class="price">{round(float(price), 2)}</div>
      <div class="delta {cls}">{arrow} {round(float(ch), 2)}（{round(float(pct), 2)}%）</div>
    </div>
    """

def generate_countdown_html(start_year=2026, target_year=2035):
    """生成動態倒數卡片的 HTML 字串"""
    start_date = datetime(start_year, 1, 1)
    target_date = datetime(target_year, 12, 31)
    today = datetime.now()
    
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

# === 頁面邏輯 ===
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

# 頂部佈局：左側標題與更新時間，右側財務自由倒數卡片
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

st.markdown('<div class="section-title">全球市場快照</div>', unsafe_allow_html=True)

filled = {}
filled["富台指（FTX）"] = fetch_ftx_wantgoo()
for name, tickers in SYMBOLS_OTHERS:
    filled[name] = yf_quote_any(tuple(tickers))

st.markdown('<div class="cards">', unsafe_allow_html=True)
is_mobile = st.toggle("手機版排版（兩欄）", value=False)

DISPLAY_ORDER = [("富台指（FTX）", None)] + SYMBOLS_OTHERS

if is_mobile:
    col1, col2 = st.columns(2)
    for i, (name, _) in enumerate(DISPLAY_ORDER):
        html = render_tile(name, filled.get(name))
        with (col1 if i % 2 == 0 else col2):
            st.markdown(html, unsafe_allow_html=True)
else:
    cols = st.columns(6)
    for i, (name, _) in enumerate(DISPLAY_ORDER):
        html = render_tile(name, filled.get(name))
        with cols[i]:
            st.markdown(html, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

left, right = st.columns([1.35, 0.65], gap="large")
with left:
    st.markdown('<div class="section-title">AI 分析摘要</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(data.get("report", ""))
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-title">新聞清單</div>', unsafe_allow_html=True)
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
