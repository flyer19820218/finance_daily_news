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

# === 完整 CSS 樣式 (保留原本所有細節) ===
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

# === 數據抓取：富台指 (玩股網) + 其他 (Yahoo) ===
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
                    "change": float(c.group(1)) if c else 0, "pct": float(cp.group(1)) if cp else 0}
    except: pass
    return {"ok": False}

@st.cache_data(ttl=60)
def yf_quote(symbol):
    try:
        t = yf.Ticker(symbol)
        h = t.history(period="2d")
        if not h.empty:
            l, p = h["Close"].iloc[-1], h["Close"].iloc[-2] if len(h)>1 else h["Close"].iloc[-1]
            return {"ok": True, "price": l, "change": l-p, "pct": (l-p)/p*100 if p!=0 else 0}
    except: pass
    return {"ok": False}

def render_tile(name, q):
    if not q or not q.get("ok"):
        return f'<div class="tile"><div class="name">{name}</div><div class="price">-</div></div>'
    p, ch, pct = q["price"], q["change"], q["pct"]
    cls = "up" if ch > 0 else "down" if ch < 0 else "flat"
    arrow = "▲" if ch > 0 else "▼" if ch < 0 else "—"
    return f'<div class="tile"><div class="name">{name}</div><div class="price">{round(p, 2)}</div><div class="delta {cls}">{arrow} {round(ch, 2)} ({round(pct, 2)}%)</div></div>'

# === 頁面邏輯 ===
data = json.load(open(LATEST_FILE, "r", encoding="utf-8")) if os.path.exists(LATEST_FILE) else {}
if not data: st.error("資料缺失"); st.stop()

st.markdown(f'<div class="header"><div><div class="brand">財經AI快報</div><div class="sub">每日市場重點監測</div></div><div class="badge">更新：{data.get("updated_at_utc","")}</div></div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">全球市場快照</div>', unsafe_allow_html=True)

# 執行抓取
SYMBOLS = [("費半 (SOX)", "^SOX"), ("道瓊期 (YM)", "YM=F"), ("納指期 (NQ)", "NQ=F"), ("台積電 ADR", "TSM"), ("NVIDIA", "NVDA")]
filled = {"富台指": fetch_ftx_wantgoo()}
for name, sym in SYMBOLS: filled[name] = yf_quote(sym)

# 市場卡片區
st.markdown('<div class="cards">', unsafe_allow_html=True)
cols = st.columns(6)
with cols[0]: st.markdown(render_tile("富台指", filled["富台指"]), unsafe_allow_html=True)
for i, (name, _) in enumerate(SYMBOLS):
    with cols[i+1]: st.markdown(render_tile(name, filled[name]), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# 下方主內容區
left, right = st.columns([1.35, 0.65], gap="large")
with left:
    st.markdown('<div class="section-title">AI 分析摘要</div><div class="panel">' + data.get("report", "") + '</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-title">新聞清單</div>', unsafe_allow_html=True)
    news = data.get("news", [])
    page_size = 10
    total_pages = max(1, math.ceil(len(news) / page_size))
    if "news_page" not in st.session_state: st.session_state.news_page = 1
    
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
        st.markdown(f'''
        <div class="news-card">
            <div style="font-weight:bold;">{title}</div>
            <div class="inline-row">{source} &nbsp;|&nbsp; <a href="{link}" target="_blank">閱讀原文</a></div>
        </div>''', unsafe_allow_html=True)
