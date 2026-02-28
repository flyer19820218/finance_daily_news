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

# === 視覺規範補丁 (完全保留你原本的 CSS) ===
st.markdown(
    """
<style>
:root{
  --bg:#ffffff; --panel:#f7f9fc; --border:#e7ebf3; --text:#0f172a;
  --muted:#64748b; --muted2:#94a3b8; --up:#16a34a; --down:#ef4444;
  --link:#2563eb; --pill:#eef2ff; --shadow: 0 10px 30px rgba(2,6,23,0.06);
  --shadow2: 0 8px 22px rgba(2,6,23,0.05);
}
.stApp{
  background:var(--bg); color:var(--text);
  font-family: "翩翩體", "HanziPen SC", "PingFang TC", sans-serif;
}
.block-container{ padding-top: 1.2rem; padding-bottom: 2.2rem; max-width: 1180px; }
.header{ display:flex; justify-content:space-between; align-items:flex-end; gap:14px; padding: 6px 0 12px 0; }
.brand{ font-size: 34px; font-weight: 900; letter-spacing: -0.4px; }
.sub{ color:var(--muted); font-size: 13px; margin-top: 6px; }
.badge{ display:inline-flex; align-items:center; gap:8px; padding: 8px 12px; border:1px solid var(--border); border-radius: 999px; background: #fff; color: var(--muted); font-size: 12px; }
.hr{ height:1px; background:var(--border); margin: 18px 0; }
.section-title{ font-size: 15px; font-weight: 850; margin: 10px 0 10px 0; }
.cards{ border:1px solid var(--border); background: var(--panel); border-radius: 18px; padding: 14px; box-shadow: var(--shadow); }
.tile{ background:#fff; border:1px solid var(--border); border-radius: 16px; padding: 12px; height: 100%; box-shadow: var(--shadow2); }
.price{ font-size: 22px; font-weight: 950; margin: 2px 0 6px 0; }
.delta{ font-size: 13px; font-weight: 800; }
.up{ color:var(--up); } .down{ color:var(--down); } .flat{ color:var(--muted2); }
.panel{ border:1px solid var(--border); background: #fff; border-radius: 18px; padding: 16px; box-shadow: var(--shadow); }
.news-card{ border:1px solid var(--border); background:#fff; border-radius: 16px; padding: 10px 12px; margin-bottom: 10px; }
.inline-row{ margin-top: 4px; font-size: 12px; color: var(--muted); }
.pagerline{ display:flex; align-items:center; justify-content:space-between; margin: 6px 0 10px 0; }
</style>
""",
    unsafe_allow_html=True,
)

# === 抓取函數：富台指 (玩股網) ===
@st.cache_data(ttl=60)
def fetch_ftx_wantgoo():
    url = "https://www.wantgoo.com/global/indices/ftx"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.wantgoo.com/"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        p = re.search(r'"price":\s*"?([0-9,.]+)"?', res.text)
        c = re.search(r'"change":\s*"?([0-9,.-]+)"?', res.text)
        cp = re.search(r'"changePercent":\s*"?([0-9,.-]+)"?', res.text)
        if p:
            return {"ok": True, "price": float(p.group(1).replace(',', '')), 
                    "change": float(c.group(1)) if c else 0.0, "pct": float(cp.group(1)) if cp else 0.0}
    except: pass
    return {"ok": False}

# === 抓取函數：其他指數 (Yahoo) ===
@st.cache_data(ttl=60)
def yf_quote_any(tickers):
    for tk in tickers:
        try:
            t = yf.Ticker(tk)
            h = t.history(period="2d")
            if not h.empty:
                last, prev = h["Close"].iloc[-1], h["Close"].iloc[-2] if len(h)>1 else h["Close"].iloc[-1]
                return {"ok": True, "price": last, "change": last-prev, "pct": (last-prev)/prev*100 if prev!=0 else 0}
        except: continue
    return {"ok": False}

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return None

def list_history():
    if not os.path.exists(HISTORY_DIR): return []
    files = sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")], reverse=True)
    return files

def render_tile(name, q):
    if not q or not q.get("ok"):
        return f'<div class="tile"><div class="name">{name}</div><div class="price">-</div></div>'
    p, ch, pct = q["price"], q["change"], q["pct"]
    cls = "up" if ch > 0 else "down" if ch < 0 else "flat"
    arrow = "▲" if ch > 0 else "▼" if ch < 0 else "—"
    return f'<div class="tile"><div class="name">{name}</div><div class="price">{round(p, 2)}</div><div class="delta {cls}">{arrow} {round(ch, 2)} ({round(pct, 2)}%)</div></div>'

# === 頁面核心邏輯 (完全保留你的歷史模式切換) ===
mode = st.radio("檢視模式", ["最新（今日）", "歷史回顧"], horizontal=True)
data = None
if mode == "最新（今日）":
    data = load_json(LATEST_FILE)
else:
    hist = list_history()
    if not hist:
        st.warning("尚無歷史資料"); st.stop()
    pick = st.selectbox("選擇日期", hist, index=0)
    data = load_json(os.path.join(HISTORY_DIR, pick))

if not data:
    st.warning("尚未產生報告"); st.stop()

updated = data.get("updated_at_utc", "")
st.markdown(f'<div class="header"><div><div class="brand">財經AI快報</div><div class="sub">每日市場重點整理</div></div><div class="badge">更新：{updated}</div></div>', unsafe_allow_html=True)

# 市場快照區 (富台指強制玩股網)
st.markdown('<div class="section-title">全球市場快照</div>', unsafe_allow_html=True)
SYMBOLS = [("費半 (SOX)", ["^SOX"]), ("道瓊期 (YM)", ["YM=F"]), ("納指期 (NQ)", ["NQ=F"]), ("台積電 ADR", ["TSM"]), ("NVIDIA", ["NVDA"])]
filled = {"富台指": fetch_ftx_wantgoo()}
for name, tks in SYMBOLS: filled[name] = yf_quote_any(tks)

st.markdown('<div class="cards">', unsafe_allow_html=True)
is_mobile = st.toggle("手機版排版（兩欄）", value=False)
disp_list = [("富台指", None)] + SYMBOLS
if is_mobile:
    c1, c2 = st.columns(2)
    for i, (name, _) in enumerate(disp_list):
        with (c1 if i % 2 == 0 else c2): st.markdown(render_tile(name, filled.get(name)), unsafe_allow_html=True)
else:
    cols = st.columns(6)
    for i, (name, _) in enumerate(disp_list):
        with cols[i]: st.markdown(render_tile(name, filled.get(name)), unsafe_allow_html=True)
st.markdown("</div><div class=\"hr\"></div>", unsafe_allow_html=True)

# 下方主內容 (完全保留你的 AI 分析與新聞分頁)
left, right = st.columns([1.35, 0.65], gap="large")
with left:
    st.markdown('<div class="section-title">AI 分析摘要</div><div class="panel">' + data.get("report", "") + '</div>', unsafe_allow_html=True)

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
        if st.button("← 上一頁", disabled=st.session_state.news_page <= 1):
            st.session_state.news_page -= 1; st.rerun()
    with c2:
        if st.button("下一頁 →", disabled=st.session_state.news_page >= total_pages):
            st.session_state.news_page += 1; st.rerun()

    start = (st.session_state.news_page - 1) * page_size
    for n in news[start : start + page_size]:
        title, link = n.get("title", ""), n.get("link", "")
        source = urlparse(link).netloc.replace("www.", "") if link else ""
        st.markdown(f'<div class="news-card">**{title}**<div class="inline-row">{source} &nbsp;|&nbsp; <a href="{link}" target="_blank">閱讀原文</a></div></div>', unsafe_allow_html=True)
