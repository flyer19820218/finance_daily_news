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

# === 視覺規範補丁 (含 iOS 反黑與翩翩體) ===
st.markdown(
    """
<style>
:root{
  --bg:#ffffff; --panel:#f7f9fc; --border:#e7ebf3; --text:#0f172a;
  --muted:#64748b; --muted2:#94a3b8; --up:#16a34a; --down:#ef4444;
  --link:#2563eb; --shadow: 0 10px 30px rgba(2,6,23,0.06);
  color-scheme: light;
}
.stApp{
  background:var(--bg); color:var(--text);
  font-family: "翩翩體", "HanziPen SC", "PingFang TC", sans-serif;
}
.block-container{ padding-top: 1.2rem; max-width: 1180px; }
.header{ display:flex; justify-content:space-between; align-items:flex-end; padding-bottom: 12px; }
.brand{ font-size: 34px; font-weight: 900; }
.badge{ padding: 8px 12px; border:1px solid var(--border); border-radius: 999px; background: #fff; font-size: 12px; }
.section-title{ font-size: 15px; font-weight: 850; margin: 10px 0; }
.cards{ border:1px solid var(--border); background: var(--panel); border-radius: 18px; padding: 14px; box-shadow: var(--shadow); }
.tile{ background:#fff; border:1px solid var(--border); border-radius: 16px; padding: 12px; height: 100%; }
.price{ font-size: 22px; font-weight: 950; margin: 2px 0 6px 0; }
.delta{ font-size: 13px; font-weight: 800; }
.up{ color:var(--up); } .down{ color:var(--down); } .flat{ color:var(--muted2); }
.panel{ border:1px solid var(--border); background: #fff; border-radius: 18px; padding: 16px; box-shadow: var(--shadow); }
.news-card{ border:1px solid var(--border); background:#fff; border-radius: 16px; padding: 10px 12px; margin-bottom: 10px; }
.inline-row{ margin-top: 4px; font-size: 12px; color: var(--muted); }
</style>
""",
    unsafe_allow_html=True,
)

# === 核心抓取函數 ===

@st.cache_data(ttl=60)
def fetch_wantgoo_ftx():
    """專門抓取玩股網富台指 (FTX)"""
    url = "https://www.wantgoo.com/global/indices/ftx"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": "https://www.wantgoo.com/"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        # 利用玩股網原始碼中的 JSON 結構
        p = re.search(r'"price":\s*"?([0-9,.]+)"?', res.text)
        c = re.search(r'"change":\s*"?([0-9,.-]+)"?', res.text)
        cp = re.search(r'"changePercent":\s*"?([0-9,.-]+)"?', res.text)
        if p:
            return {
                "ok": True, "ticker": "FTX", 
                "price": float(p.group(1).replace(',', '')),
                "change": float(c.group(1)) if c else 0.0,
                "pct": float(cp.group(1)) if cp else 0.0
            }
    except: pass
    return {"ok": False}

@st.cache_data(ttl=60)
def yf_quote_any(tickers):
    for tk in tickers:
        try:
            t = yf.Ticker(tk)
            hist = t.history(period="2d")
            if not hist.empty:
                last = hist["Close"].iloc[-1]
                prev = hist["Close"].iloc[-2] if len(hist) > 1 else last
                return {"ok": True, "ticker": tk, "price": last, "change": last-prev, "pct": (last-prev)/prev*100 if prev else 0}
        except: continue
    return {"ok": False}

# === 資料載入邏輯 ===

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return None

def list_history():
    if not os.path.exists(HISTORY_DIR): return []
    files = sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")], reverse=True)
    return files

# === UI 渲染函數 ===

def render_tile(name, q):
    if not q or not q.get("ok"):
        return f'<div class="tile"><div class="name">{name}</div><div class="price">連線中</div></div>'
    p, ch, pct = q["price"], q["change"], q["pct"]
    cls = "up" if ch > 0 else "down" if ch < 0 else "flat"
    arrow = "▲" if ch > 0 else "▼" if ch < 0 else "—"
    return f'<div class="tile"><div class="name">{name}</div><div class="price">{round(p, 2)}</div><div class="delta {cls}">{arrow} {round(ch, 2)} ({round(pct, 2)}%)</div></div>'

# === 主程式執行 ===

mode = st.radio("檢視模式", ["最新（今日）", "歷史回顧"], horizontal=True)
if mode == "最新（今日）":
    data = load_json(LATEST_FILE)
else:
    hist_files = list_history()
    if hist_files:
        pick = st.selectbox("選擇日期", hist_files)
        data = load_json(os.path.join(HISTORY_DIR, pick))
    else:
        st.warning("尚無歷史資料"); st.stop()

if not data:
    st.error("找不到報告檔案"); st.stop()

st.markdown(f'<div class="header"><div><div class="brand">財經AI快報</div><div class="sub">富台指(玩股網) | 美股指數(Yahoo)</div></div><div class="badge">更新：{data.get("updated_at_utc","")}</div></div>', unsafe_allow_html=True)

# 抓取即時數據
SYMBOLS = [
    ("費半（SOX）", ["^SOX"]), ("道瓊期（YM）", ["YM=F"]), ("納指期（NQ）", ["NQ=F"]),
    ("台積電 ADR", ["TSM"]), ("NVIDIA", ["NVDA"])
]
filled = {"富台指": fetch_wantgoo_ftx()}
for name, tks in SYMBOLS:
    filled[name] = yf_quote_any(tks)

# 市場快照區
st.markdown('<div class="section-title">全球市場快照</div><div class="cards">', unsafe_allow_html=True)
cols = st.columns(6)
with cols[0]: st.markdown(render_tile("富台指", filled["富台指"]), unsafe_allow_html=True)
for i, (name, _) in enumerate(SYMBOLS):
    with cols[i+1]: st.markdown(render_tile(name, filled[name]), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# 下方內容區
left, right = st.columns([1.35, 0.65], gap="large")
with left:
    st.markdown('<div class="section-title">AI 分析摘要</div><div class="panel">', unsafe_allow_html=True)
    st.markdown(data.get("report", "無分析內容"))
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-title">新聞清單</div>', unsafe_allow_html=True)
    news = data.get("news", [])
    page_size = 10
    total_pages = max(1, math.ceil(len(news) / page_size))
    if "news_page" not in st.session_state: st.session_state.news_page = 1
    
    # 分頁按鈕
    c1, c2 = st.columns(2)
    with c1: 
        if st.button("← 上一頁", disabled=st.session_state.news_page <= 1):
            st.session_state.news_page -= 1; st.rerun()
    with c2:
        if st.button("下一頁 →", disabled=st.session_state.news_page >= total_pages):
            st.session_state.news_page += 1; st.rerun()

    # 顯示新聞卡片
    start = (st.session_state.news_page - 1) * page_size
    for n in news[start : start + page_size]:
        st.markdown(f'''
        <div class="news-card">
            <div style="font-weight:bold;">{n.get("title","")}</div>
            <div class="inline-row"><a href="{n.get("link","#")}" target="_blank">閱讀原文</a></div>
        </div>''', unsafe_allow_html=True)
