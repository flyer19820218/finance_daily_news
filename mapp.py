import streamlit as st
import yfinance as yf
import json
import os
import math
from urllib.parse import urlparse

# 1. 頁面配置：手機版一定要設為 wide 才能撐開網格
st.set_page_config(page_title="財經AI快報-手機版", page_icon="📱", layout="wide")

# 2. 路徑設定
LATEST_FILE = "data/latest_report.json"

# 3. 核心 CSS：保留大標題樣式，並強制 2x3 網格
st.markdown("""
<style>
:root{
  --up:#16a34a; --down:#ef4444; --text:#0f172a; --muted:#64748b;
}
.stApp { background:#ffffff; font-family: "翩翩體", sans-serif; }

/* 大標題樣式 */
.brand { font-size: 32px; font-weight: 900; color: var(--text); margin-bottom: 2px; }
.sub { color: var(--muted); font-size: 13px; margin-bottom: 15px; }

/* 2x3 網格系統 */
.m-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    background: #f7f9fc;
    border: 1px solid #e7ebf3;
    border-radius: 18px;
    padding: 12px;
}
.m-tile {
    background: #ffffff;
    border: 1px solid #e7ebf3;
    border-radius: 16px;
    padding: 12px;
    text-align: center;
}
.m-name { color: var(--muted); font-size: 12px; }
.m-price { font-size: 20px; font-weight: 900; margin: 4px 0; }
.m-pct { font-size: 13px; font-weight: 800; }
.up { color: var(--up); }
.down { color: var(--down); }

/* 新聞卡片 */
.news-card {
    border: 1px solid #e7ebf3;
    background: #fff;
    border-radius: 16px;
    padding: 12px;
    margin-bottom: 10px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}
</style>
""", unsafe_allow_html=True)

# 4. 數據抓取：MSCI 台灣代理與漲跌幅
@st.cache_data(ttl=60)
def fetch_yf_data(symbol, display_name):
    try:
        t = yf.Ticker(symbol)
        info = t.fast_info
        last = info.last_price
        prev = info.previous_close
        if last and prev:
            diff = last - prev
            pct = (diff / prev) * 100
            return {"name": display_name, "ok": True, "price": last, "pct": pct}
    except: pass
    return {"name": display_name, "ok": False}

# 5. 載入資料
if not os.path.exists(LATEST_FILE):
    st.error("找不到資料檔案，請確認 data 目錄。")
    st.stop()
with open(LATEST_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# 6. 【功能回歸】大標題與最後更新
st.markdown(f'''
<div class="brand">財經AI快報</div>
<div class="sub">每日市場重點整理：重大事件｜台股影響｜投資觀察</div>
<div style="font-size:11px; color:#94a3b8; margin-bottom:20px;">更新時間：{data.get("updated_at_utc", "")}</div>
''', unsafe_allow_html=True)

# 7. 2x3 市場快照
st.markdown('<div style="font-size:16px; font-weight:800; margin-bottom:10px;">全球市場快照</div>', unsafe_allow_html=True)
targets = [
    ("EWT", "MSCI 台灣"), ("^SOX", "費半"), ("YM=F", "道瓊期"),
    ("NQ=F", "納指期"), ("TSM", "台積電"), ("NVDA", "NVIDIA")
]

grid_html = '<div class="m-grid">'
for sym, name in targets:
    q = fetch_yf_data(sym, name)
    if q["ok"]:
        cls = "up" if q["pct"] > 0 else "down" if q["pct"] < 0 else ""
        sign = "+" if q["pct"] > 0 else ""
        grid_html += f'''
        <div class="m-tile">
            <div class="m-name">{q["name"]}</div>
            <div class="m-price">{round(q["price"], 2)}</div>
            <div class="m-pct {cls}">{sign}{round(q["pct"], 2)}%</div>
        </div>'''
    else:
        grid_html += f'<div class="m-tile"><div>{name}</div><div>-</div></div>'
grid_html += '</div>'
st.markdown(grid_html, unsafe_allow_html=True)

# 8. AI 分析摘要
st.markdown('<div style="font-size:16px; font-weight:800; margin:20px 0 10px 0;">AI 分析摘要</div>', unsafe_allow_html=True)
st.info(data.get("report", ""))

# 9. 【功能回歸】新聞清單與簡單分頁
st.markdown('<div style="font-size:16px; font-weight:800; margin:20px 0 10px 0;">新聞清單</div>', unsafe_allow_html=True)
news = data.get("news", [])
if news:
    page_size = 10
    total_pages = math.ceil(len(news) / page_size)
    if "m_news_page" not in st.session_state: st.session_state.m_news_page = 1
    
    # 簡易分頁切換
    c1, c2, c3 = st.columns([1,2,1])
    with c1:
        if st.button("⬅️", key="p", disabled=st.session_state.m_news_page==1):
            st.session_state.m_news_page -= 1; st.rerun()
    with c2:
        st.markdown(f"<center><small>{st.session_state.m_news_page} / {total_pages}</small></center>", unsafe_allow_html=True)
    with c3:
        if st.button("➡️", key="n", disabled=st.session_state.m_news_page==total_pages):
            st.session_state.m_news_page += 1; st.rerun()

    start_idx = (st.session_state.m_news_page - 1) * page_size
    for n in news[start_idx : start_idx + page_size]:
        source = urlparse(n.get("link", "")).netloc.replace("www.", "")
        st.markdown(f'''
        <div class="news-card">
            <div style="font-weight:700; font-size:14px; margin-bottom:5px;">{n.get("title")}</div>
            <div style="font-size:12px; color:#64748b;">{source} | <a href="{n.get("link")}" target="_blank">閱讀原文</a></div>
        </div>
        ''', unsafe_allow_html=True)
