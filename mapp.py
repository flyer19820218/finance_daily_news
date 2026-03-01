import streamlit as st
import yfinance as yf
import json
import os
import math
from urllib.parse import urlparse

# 1. 頁面配置
st.set_page_config(page_title="財經AI快報-手機版", page_icon="📱", layout="wide")

# 2. 核心 CSS 優化
st.markdown("""
<style>
:root{
  --up:#16a34a; --down:#ef4444; --text:#0f172a; --muted:#64748b; --border:#e7ebf3;
}
/* 移除手機版多餘邊距 */
.block-container { padding: 1rem 0.8rem !important; }

.stApp { background:#ffffff; font-family: "翩翩體", "PingFang TC", sans-serif; }

/* 標題區 */
.brand { font-size: 28px; font-weight: 900; color: var(--text); letter-spacing: -0.5px; }
.sub { color: var(--muted); font-size: 12px; margin-bottom: 4px; line-height: 1.4; }
.update-time { font-size: 10px; color: #94a3b8; margin-bottom: 15px; }

/* 2x3 網格系統 */
.m-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
    background: #f8fafc; border: 1px solid var(--border);
    border-radius: 16px; padding: 10px;
}
.m-tile {
    background: #ffffff; border: 1px solid var(--border);
    border-radius: 12px; padding: 10px; text-align: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}
.m-name { color: var(--muted); font-size: 11px; font-weight: 500; }
.m-price { font-size: 19px; font-weight: 900; margin: 2px 0; color: #0f172a; }
.m-pct { font-size: 12px; font-weight: 800; }
.up { color: var(--up); } .down { color: var(--down); }

/* AI 摘要區 */
.stInfo { border-radius: 14px !important; border: none !important; background-color: #f1f5f9 !important; color: #334155 !important; }

/* 專業分頁控制列 */
.pager-container {
    display: flex; align-items: center; justify-content: space-between;
    margin: 10px 0; padding: 0 5px;
}
.page-indicator { font-size: 12px; font-weight: 700; color: var(--muted); }

/* 新聞卡片優化 */
.news-card {
    border: 1px solid var(--border); background: #fff;
    border-radius: 14px; padding: 12px; margin-bottom: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.news-title { font-weight: 700; font-size: 14px; color: #1e293b; line-height: 1.5; margin-bottom: 6px; }
.news-meta { display: flex; align-items: center; gap: 8px; font-size: 11px; }
.source-tag { background: #f1f5f9; color: #475569; padding: 2px 6px; border-radius: 4px; font-weight: 600; }
.read-link { color: #2563eb; text-decoration: none; font-weight: 600; }

/* 隱藏預設按鈕樣式調整 */
div.stButton > button {
    border-radius: 20px !important; padding: 0px 15px !important;
    height: 32px !important; line-height: 32px !important;
    border: 1px solid var(--border) !important;
}
</style>
""", unsafe_allow_html=True)

# 3. 數據抓取
@st.cache_data(ttl=60)
def fetch_yf_data(symbol, display_name):
    try:
        t = yf.Ticker(symbol)
        info = t.fast_info
        last, prev = info.last_price, info.previous_close
        if last and prev:
            pct = ((last - prev) / prev) * 100
            return {"name": display_name, "ok": True, "price": last, "pct": pct}
    except: pass
    return {"name": display_name, "ok": False}

# 4. 載入資料
LATEST_FILE = "data/latest_report.json"
if os.path.exists(LATEST_FILE):
    with open(LATEST_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
else:
    st.error("Missing data")
    st.stop()

# 5. 大標題渲染
st.markdown(f'''
<div class="brand">財經AI快報</div>
<div class="sub">每日市場重點整理：重大事件｜台股影響</div>
<div class="update-time">最後更新：{data.get("updated_at_utc", "")}</div>
''', unsafe_allow_html=True)

# 6. 市場網格
st.markdown('<div style="font-size:15px; font-weight:800; margin-left:5px; margin-bottom:8px;">全球市場快照</div>', unsafe_allow_html=True)
targets = [
    ("EWT", "MSCI 台灣"), ("^SOX", "費半"), ("YM=F", "道瓊期"),
    ("NQ=F", "納指期"), ("TSM", "台積電"), ("NVDA", "NVIDIA")
]

grid_html = '<div class="m-grid">'
for sym, name in targets:
    q = fetch_ft = fetch_yf_data(sym, name)
    if q["ok"]:
        cls = "up" if q["pct"] > 0 else "down" if q["pct"] < 0 else ""
        sign = "+" if q["pct"] > 0 else ""
        grid_html += f'''
        <div class="m-tile">
            <div class="m-name">{q["name"]}</div>
            <div class="m-price">{round(q["price"], 1)}</div>
            <div class="m-pct {cls}">{sign}{round(q["pct"], 2)}%</div>
        </div>'''
    else:
        grid_html += f'<div class="m-tile"><div class="m-name">{name}</div><div class="m-price">-</div></div>'
grid_html += '</div>'
st.markdown(grid_html, unsafe_allow_html=True)

# 7. AI 摘要
st.markdown('<div style="font-size:15px; font-weight:800; margin:18px 0 8px 5px;">AI 分析摘要</div>', unsafe_allow_html=True)
st.info(data.get("report", ""))

# 8. 新聞清單優化
st.markdown('<div style="font-size:15px; font-weight:800; margin:18px 0 5px 5px;">即時新聞清單</div>', unsafe_allow_html=True)
news = data.get("news", [])
if news:
    page_size = 10
    total_pages = math.ceil(len(news) / page_size)
    if "m_news_page" not in st.session_state: st.session_state.m_news_page = 1
    
    # 精緻分頁列
    pc1, pc2, pc3 = st.columns([1,2,1])
    with pc1:
        if st.button("上頁", key="p", use_container_width=True, disabled=st.session_state.m_news_page==1):
            st.session_state.m_news_page -= 1; st.rerun()
    with pc2:
        st.markdown(f"<div style='text-align:center; padding-top:5px;'><span class='page-indicator'>{st.session_state.m_news_page} / {total_pages}</span></div>", unsafe_allow_html=True)
    with pc3:
        if st.button("下頁", key="n", use_container_width=True, disabled=st.session_state.m_news_page==total_pages):
            st.session_state.m_news_page += 1; st.rerun()

    start_idx = (st.session_state.m_news_page - 1) * page_size
    for n in news[start_idx : start_idx + page_size]:
        source = urlparse(n.get("link", "")).netloc.replace("www.", "")
        st.markdown(f'''
        <div class="news-card">
            <div class="news-title">{n.get("title")}</div>
            <div class="news-meta">
                <span class="source-tag">{source}</span>
                <a class="read-link" href="{n.get("link")}" target="_blank">閱讀全文 ↗</a>
            </div>
        </div>
        ''', unsafe_allow_html=True)
