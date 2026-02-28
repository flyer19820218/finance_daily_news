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

# === 視覺規範補丁 (含原本 CSS) ===
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
  font-family: "翩翩體", "PianPian", "PingFang TC", sans-serif;
}

/* 這裡保留你原本所有的 CSS 樣式 */
.block-container{ padding-top: 1.2rem; padding-bottom: 2.2rem; max-width: 1180px; }
.header{ display:flex; justify-content:space-between; align-items:flex-end; gap:14px; padding: 6px 0 12px 0; }
.brand{ font-size: 34px; font-weight: 900; letter-spacing: -0.4px; }
.sub{ color:var(--muted); font-size: 13px; margin-top: 6px; }
.badge{ display:inline-flex; align-items:center; gap:8px; padding: 8px 12px; border:1px solid var(--border); border-radius: 999px; background: #fff; color: var(--muted); font-size: 12px; }
.section-title{ font-size: 15px; font-weight: 850; margin: 10px 0; }
.cards{ border:1px solid var(--border); background: var(--panel); border-radius: 18px; padding: 14px; box-shadow: var(--shadow); }
.tile{ background:#fff; border:1px solid var(--border); border-radius: 16px; padding: 12px; height: 100%; box-shadow: var(--shadow2); }
.price{ font-size: 22px; font-weight: 950; margin: 2px 0 6px 0; }
.delta{ font-size: 13px; font-weight: 800; }
.up{ color:var(--up); }
.down{ color:var(--down); }
.flat{ color:var(--muted2); }
.panel{ border:1px solid var(--border); background: #fff; border-radius: 18px; padding: 16px; box-shadow: var(--shadow); }
.news-card{ border:1px solid var(--border); background:#fff; border-radius: 16px; padding: 10px 12px; margin-bottom: 10px; }
</style>
""",
    unsafe_allow_html=True,
)

# === 數據抓取邏輯 ===

@st.cache_data(ttl=60)
def fetch_wantgoo_ftx():
    """專門抓取玩股網富台指 (FTX)"""
    url = "https://www.wantgoo.com/global/indices/ftx" # 玩股網富台指頁面
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.wantgoo.com/"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        # 抓取目前價格與漲跌幅
        price_match = re.search(r'"price":\s*"?([0-9,.]+)"?', res.text)
        change_match = re.search(r'"change":\s*"?([0-9,.-]+)"?', res.text)
        pct_match = re.search(r'"changePercent":\s*"?([0-9,.-]+)"?', res.text)
        
        if price_match:
            p = float(price_match.group(1).replace(',', ''))
            c = float(change_match.group(1)) if change_match else 0.0
            pct = float(pct_match.group(1)) if pct_match else 0.0
            return {"ok": True, "ticker": "Wantgoo", "price": p, "change": c, "pct": pct}
    except:
        pass
    return {"ok": False}

@st.cache_data(ttl=60)
def yf_quote_any(tickers):
    for tk in tickers:
        try:
            t = yf.Ticker(tk)
            fi = getattr(t, "fast_info", None)
            last = None
            prev = None
            if fi:
                last = fi.get("last_price") or fi.get("lastPrice")
                prev = fi.get("previous_close") or fi.get("previousClose")
            if last is None:
                hist = t.history(period="2d")
                if len(hist) >= 1:
                    last = hist["Close"].iloc[-1]
                    prev = hist["Close"].iloc[-2] if len(hist) >= 2 else last
            if last is not None:
                ch = (last - prev) if prev else 0
                pct = (ch / prev * 100) if prev else 0
                return {"ok": True, "ticker": tk, "price": last, "change": ch, "pct": pct}
        except:
            continue
    return {"ok": False}

# === 初始化資料 ===

SYMBOLS = [
    ("費半（SOX）", ["^SOX"]),
    ("道瓊期（YM）", ["YM=F"]),
    ("納指期（NQ）", ["NQ=F"]),
    ("台積電 ADR（TSM）", ["TSM"]),
    ("NVIDIA（NVDA）", ["NVDA"]),
]

def load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return None

def render_tile(name, q):
    if not q or not q.get("ok"):
        return f'<div class="tile"><div class="name">{name}</div><div class="price">-</div></div>'
    
    p, ch, pct = q["price"], q["change"], q["pct"]
    cls = "up" if ch > 0 else "down" if ch < 0 else "flat"
    arrow = "▲" if ch > 0 else "▼" if ch < 0 else "—"
    
    return f"""
    <div class="tile">
      <div class="name">{name}</div>
      <div class="price">{round(p, 2)}</div>
      <div class="delta {cls}">{arrow} {round(ch, 2)} ({round(pct, 2)}%)</div>
    </div>
    """

# === 主介面邏輯 ===

mode = st.radio("檢視模式", ["最新（今日）", "歷史回顧"], horizontal=True)
data = load_json(LATEST_FILE) if mode == "最新（今日）" else None # 簡化邏輯供參考

if not data:
    st.warning("請確保 data/latest_report.json 存在")
    st.stop()

st.markdown(f'<div class="header"><div><div class="brand">財經AI快報</div><div class="sub">富台指專線：玩股網即時擷取</div></div><div class="badge">更新：{data.get("updated_at_utc","")}</div></div>', unsafe_allow_html=True)

# 抓取數據
filled = {}
filled["富台指（FTX）"] = fetch_wantgoo_ftx() # 優先嘗試玩股網
for name, tickers in SYMBOLS:
    filled[name] = yf_quote_any(tuple(tickers))

# 渲染卡片
st.markdown('<div class="section-title">全球市場快照</div><div class="cards">', unsafe_allow_html=True)
cols = st.columns(6)

# 第一個固定放富台指
with cols[0]:
    st.markdown(render_tile("富台指 (FTX)", filled["富台指（FTX）"]), unsafe_allow_html=True)

# 剩下的放 Yahoo 資料
for i, (name, _) in enumerate(SYMBOLS):
    with cols[i+1]:
        st.markdown(render_tile(name, filled[name]), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# 下方保留你原本的 AI 分析與新聞列表 (left, right 欄位)...
# [此處省略你原本的分析摘要與新聞分頁代碼，請直接保留你原本檔案末端的邏輯]
