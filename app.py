import json
import os
import math
import streamlit as st
import yfinance as yf
from urllib.parse import urlparse

LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

# 保持你原始的 CSS 樣式
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
.block-container{ padding-top: 1.2rem; padding-bottom: 2.2rem; max-width: 1180px; }
.header{ display:flex; justify-content:space-between; align-items:flex-end; gap:14px; padding: 6px 0 12px 0; }
.brand{ font-size: 34px; font-weight: 900; }
.badge{ padding: 8px 12px; border:1px solid var(--border); border-radius: 999px; background: #fff; font-size: 12px; }
.section-title{ font-size: 15px; font-weight: 850; margin: 10px 0; }
.cards{ border:1px solid var(--border); background: var(--panel); border-radius: 18px; padding: 14px; box-shadow: var(--shadow); }
.tile{ background:#fff; border:1px solid var(--border); border-radius: 16px; padding: 12px; height: 100%; box-shadow: var(--shadow2); }
.price{ font-size: 22px; font-weight: 950; margin: 2px 0 6px 0; }
.delta{ font-size: 13px; font-weight: 800; }
.up{ color:var(--up); } .down{ color:var(--down); } .flat{ color:var(--muted2); }
.panel{ border:1px solid var(--border); background: #fff; border-radius: 18px; padding: 16px; }
.news-card{ border:1px solid var(--border); background:#fff; border-radius: 16px; padding: 10px 12px; margin-bottom: 10px; }
</style>
""",
    unsafe_allow_html=True,
)

@st.cache_data(ttl=60)
def get_quote(symbol):
    """最穩定的 API 抓取方式，不解析網頁標籤"""
    try:
        ticker = yf.Ticker(symbol)
        # 使用 fast_info 獲取即時快取數字
        info = ticker.fast_info
        price = info.last_price
        prev = info.previous_close
        if price:
            change = price - prev
            pct = (change / prev) * 100 if prev else 0
            return {"ok": True, "price": price, "change": change, "pct": pct}
    except:
        pass
    return {"ok": False}

# 定義要抓取的代碼 (富台指使用 FTX=F)
SYMBOLS = [
    ("富台指", "FTX=F"),
    ("費半 (SOX)", "^SOX"),
    ("道瓊期 (YM)", "YM=F"),
    ("納指期 (NQ)", "NQ=F"),
    ("台積電 ADR", "TSM"),
    ("NVIDIA", "NVDA")
]

def render_tile(name, q):
    if not q or not q.get("ok"):
        return f'<div class="tile"><div class="name">{name}</div><div class="price">-</div></div>'
    p, ch, pct = q["price"], q["change"], q["pct"]
    cls = "up" if ch > 0 else "down" if ch < 0 else "flat"
    arrow = "▲" if ch > 0 else "▼" if ch < 0 else "—"
    return f'<div class="tile"><div class="name">{name}</div><div class="price">{round(p, 2)}</div><div class="delta {cls}">{arrow} {round(ch, 2)} ({round(pct, 2)}%)</div></div>'

# --- 頁面邏輯 ---
data = json.load(open(LATEST_FILE, "r", encoding="utf-8")) if os.path.exists(LATEST_FILE) else {}

st.markdown(f'<div class="header"><div><div class="brand">財經AI快報</div><div class="sub">即時數據監控</div></div><div class="badge">更新：{data.get("updated_at_utc","")}</div></div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">全球市場快照</div>', unsafe_allow_html=True)

# 執行抓取
filled = {name: get_quote(sym) for name, sym in SYMBOLS}

# 渲染卡片
st.markdown('<div class="cards">', unsafe_allow_html=True)
cols = st.columns(6)
for i, (name, _) in enumerate(SYMBOLS):
    with cols[i]:
        st.markdown(render_tile(name, filled[name]), unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# 保留原本的 AI 分析與新聞清單區塊...
st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
l, r = st.columns([1.35, 0.65], gap="large")
with l:
    st.markdown('<div class="section-title">AI 分析摘要</div><div class="panel">' + data.get("report","") + '</div>', unsafe_allow_html=True)
with r:
    st.markdown('<div class="section-title">新聞清單</div>', unsafe_allow_html=True)
    # 此處銜接你原本的分頁邏輯代碼...
