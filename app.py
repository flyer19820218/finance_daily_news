import json
import os
import math
import re
import requests
from urllib.parse import urlparse

import streamlit as st
import yfinance as yf

LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

# === 視覺規範補丁 (含手機版 2x3 強制排版) ===
st.markdown(
    """
<style>
:root{
  --bg:#ffffff; --panel:#f7f9fc; --border:#e7ebf3; --text:#0f172a;
  --muted:#64748b; --muted2:#94a3b8; --up:#16a34a; --down:#ef4444;
  --link:#2563eb; --pill:#eef2ff; --shadow: 0 10px 30px rgba(2,6,23,0.06);
  --shadow2: 0 8px 22px rgba(2,6,23,0.05);
  color-scheme: light;
}

.stApp{
  background:var(--bg); color:var(--text);
  font-family: "翩翩體", "HanziPen SC", "PingFang TC", sans-serif;
}

/* 專業級手機 2x3 網格隔離 CSS */
@media (max-width: 768px) {
    .cards-grid {
        display: grid !important;
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 10px !important;
    }
    /* 修正手機版欄位溢出 */
    [data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; }
}

.block-container{ padding-top: 1.2rem; padding-bottom: 2.2rem; max-width: 1180px; }
.header{ display:flex; justify-content:space-between; align-items:flex-end; gap:14px; padding: 6px 0 12px 0; }
.brand{ font-size: 34px; font-weight: 900; letter-spacing: -0.4px; }
.sub{ color:var(--muted); font-size: 13px; margin-top: 6px; }
.badge{ display:inline-flex; align-items:center; gap:8px; padding: 8px 12px; border:1px solid var(--border); border-radius: 999px; background: #fff; color: var(--muted); font-size: 12px; }
.hr{ height:1px; background:var(--border); margin: 18px 0; }
.section-title{ font-size: 15px; font-weight: 850; margin: 10px 0; }
.cards{ border:1px solid var(--border); background: var(--panel); border-radius: 18px; padding: 14px; box-shadow: var(--shadow); }
.tile{ background:#fff; border:1px solid var(--border); border-radius: 16px; padding: 12px; height: 100%; box-shadow: var(--shadow2); }
.price{ font-size: 22px; font-weight: 950; margin: 2px 0 6px 0; }
.delta{ font-size: 13px; font-weight: 800; }
.up{ color:var(--up); } .down{ color:var(--down); } .flat{ color:var(--muted2); }
.panel{ border:1px solid var(--border); background: #fff; border-radius: 18px; padding: 16px; }
.news-card{ border:1px solid var(--border); background:#fff; border-radius: 16px; padding: 10px 12px; margin-bottom: 10px; }
.inline-row{ margin-top: 4px; font-size: 12px; color: var(--muted); }
.pagerline{ display:flex; align-items:center; justify-content:space-between; margin: 6px 0 10px 0; }
</style>
""",
    unsafe_allow_html=True,
)

# === 核心抓取邏輯：三道保險 (不崩潰方案) ===

@st.cache_data(ttl=60)
def fetch_ftx_combined():
    # 1. 嘗試玩股網
    try:
        url = "https://www.wantgoo.com/global/indices/ftx"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        p = re.search(r'"price":\s*"?([0-9,.]+)"?', res.text)
        if p:
            price = float(p.group(1).replace(',', ''))
            c = re.search(r'"change":\s*"?([0-9,.-]+)"?', res.text)
            cp = re.search(r'"changePercent":\s*"?([0-9,.-]+)"?', res.text)
            return {"ok": True, "price": price, "change": float(c.group(1)) if c else 0.0, "pct": float(cp.group(1)) if cp else 0.0}
    except: pass
    
    # 2. 失敗則嘗試 Yahoo 富台 (FTX=F) 或 摩台 (STW=F)
    for tk in ["FTX=F", "STW=F"]:
        try:
            t = yf.Ticker(tk)
            h = t.history(period="2d")
            if not h.empty:
                l, p = h["Close"].iloc[-1], h["Close"].iloc[-2] if len(h)>1 else h["Close"].iloc[-1]
                return {"ok": True, "price": l, "change": l-p, "pct": (l-p)/p*100 if p!=0 else 0}
        except: continue
    return {"ok": False}

@st.cache_data(ttl=60)
def yf_quote_any(tickers):
    for tk in tickers:
        try:
            t = yf.Ticker(tk)
            h = t.history(period="2d")
            if not h.empty:
                l, p = h["Close"].iloc[-1], h["Close"].iloc[-2] if len(h)>1 else h["Close"].iloc[-1]
                return {"ok": True, "price": l, "change": l-p, "pct": (l-p)/p*100 if p!=0 else 0}
        except: continue
    return {"ok": False}

def load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return None

def list_history():
    if not os.path.exists(HISTORY_DIR): return []
    return sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")], reverse=True)

def render_tile(name, q):
    if not q or not q.get("ok"):
        return f'<div class="tile"><div class="name">{name}</div><div class="price">-</div><div class="delta flat">-</div></div>'
    p, ch, pct = q["price"], q.get("change", 0), q.get("pct", 0)
    cls = "up" if ch > 0 else "down" if ch < 0 else "flat"
    arrow = "▲" if ch > 0 else "▼" if ch < 0 else "—"
    return f'<div class="tile"><div class="name">{name}</div><div class="price">{round(float(p), 2)}</div><div class="delta {cls}">{arrow} {round(float(ch), 2)}（{round(float(pct), 2)}%）</div></div>'

# === 頁面邏輯 ===
mode = st.radio("檢視模式", ["最新（今日）", "歷史回顧"], horizontal=True)
data = load_json(LATEST_FILE) if mode == "最新（今日）" else None
if mode == "歷史回顧":
    hist = list_history()
    if hist:
        pick = st.selectbox("選擇日期", hist, index=0)
        data = load_json(os.path.join(HISTORY_DIR, pick))
    else: st.warning("尚無歷史資料"); st.stop()

if not data: st.warning("尚未產生報告"); st.stop()

st.markdown(f'<div class="header"><div><div class="brand">財經AI快報</div><div class="sub">每日市場重點整理</div></div><div class="badge">最後更新（UTC）：{data.get("updated_at_utc", "")}</div></div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">全球市場快照</div>', unsafe_allow_html=True)

# 抓取數據
SYMBOLS_OTHERS = [("費半（SOX）", ["^SOX"]), ("道瓊期（YM）", ["YM=F"]), ("納指期（NQ）", ["NQ=F"]), ("台積電 ADR", ["TSM"]), ("NVIDIA", ["NVDA"])]
filled = {"富台指": fetch_ftx_combined()}
for name, tks in SYMBOLS_OTHERS: filled[name] = yf_quote_any(tks)

# 市場快照渲染
st.markdown('<div class="cards">', unsafe_allow_html=True)
is_mobile = st.toggle("手機版排版（兩欄）", value=False)
disp_list = [("富台指", None)] + SYMBOLS_OTHERS

if is_mobile:
    st.markdown('<div class="cards-grid">', unsafe_allow_html=True)
    for i, (name, _) in enumerate(disp_list):
        st.markdown(render_tile(name, filled.get(name)), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    cols = st.columns(6)
    for i, (name, _) in enumerate(disp_list):
        with cols[i]: st.markdown(render_tile(name, filled.get(name)), unsafe_allow_html=True)
st.markdown("</div><div class='hr'></div>", unsafe_allow_html=True)

# 下方 AI 分析與新聞
left, right = st.columns([1.35, 0.65], gap="large")
with left:
    st.markdown('<div class="section-title">AI 分析摘要</div><div class="panel">'+data.get("report", "")+'</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-title">新聞清單</div>', unsafe_allow_html=True)
    news = data.get("news", [])
    page_size = 10
    total_pages = max(1, math.ceil(len(news) / page_size))
    if "news_page" not in st.session_state: st.session_state.news_page = 1
    st.session_state.news_page = max(1, min(st.session_state.news_page, total_pages))

    st.markdown(f"<div class='pagerline'><div class='small'>第 {st.session_state.news_page} / {total_pages} 頁</div></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: 
        if st.button("← 上一頁", disabled=(st.session_state.news_page <= 1)):
            st.session_state.news_page -= 1; st.rerun()
    with c2:
        if st.button("下一頁 →", disabled=(st.session_state.news_page >= total_pages)):
            st.session_state.news_page += 1; st.rerun()

    start = (st.session_state.news_page - 1) * page_size
    for n in news[start:start+page_size]:
        title, link = (n.get("title") or "").strip(), (n.get("link") or "").strip()
        source = urlparse(link).netloc.replace("www.", "") if link else ""
        st.markdown(f'<div class="news-card">**{title}**<div class="inline-row">{source} &nbsp;|&nbsp; <a href="{link}" target="_blank">閱讀原文</a></div></div>', unsafe_allow_html=True)
