import streamlit as st
import yfinance as yf
import json
import os
from urllib.parse import urlparse

# 1. 頁面配置
st.set_page_config(page_title="財經AI快報-手機版", page_icon="📱", layout="wide")

# 2. 核心 CSS：移除分頁，改用對稱雙欄
st.markdown("""
<style>
:root{
  --up:#16a34a; --down:#ef4444; --text:#0f172a; --muted:#64748b; --border:#e7ebf3;
}
.block-container { padding: 1rem 0.6rem !important; }
.stApp { background:#ffffff; font-family: "翩翩體", sans-serif; }

/* 標題與更新時間 */
.brand { font-size: 26px; font-weight: 900; color: var(--text); }
.update-time { font-size: 10px; color: #94a3b8; margin-bottom: 12px; }

/* 2x3 市場網格 */
.m-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
    background: #f8fafc; border: 1px solid var(--border);
    border-radius: 16px; padding: 10px; margin-bottom: 20px;
}
.m-tile {
    background: #ffffff; border: 1px solid var(--border);
    border-radius: 12px; padding: 8px; text-align: center;
}
.m-name { color: var(--muted); font-size: 10px; }
.m-price { font-size: 18px; font-weight: 900; margin: 2px 0; }
.m-pct { font-size: 11px; font-weight: 800; }
.up { color: var(--up); } .down { color: var(--down); }

/* 新聞雙欄佈局：左 1-10, 右 11-20 */
.news-container {
    display: flex; gap: 10px; align-items: flex-start;
}
.news-column { flex: 1; }

.news-card {
    border: 1px solid var(--border); background: #fff;
    border-radius: 12px; padding: 10px; margin-bottom: 8px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.03);
}
.news-title { font-weight: 700; font-size: 13px; color: #1e293b; line-height: 1.4; margin-bottom: 5px; }
.source-tag { font-size: 10px; color: #64748b; background: #f1f5f9; padding: 1px 5px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# 3. 數據抓取
@st.cache_data(ttl=60)
def fetch_yf_data(symbol, name):
    try:
        t = yf.Ticker(symbol); info = t.fast_info
        last, prev = info.last_price, info.previous_close
        if last and prev:
            return {"name": name, "ok": True, "price": last, "pct": ((last-prev)/prev)*100}
    except: pass
    return {"name": name, "ok": False}

# 4. 載入資料
LATEST_FILE = "data/latest_report.json"
if os.path.exists(LATEST_FILE):
    with open(LATEST_FILE, "r", encoding="utf-8") as f: data = json.load(f)
else: st.stop()

# 5. 頁面渲染
st.markdown(f'<div class="brand">財經AI快報</div><div class="update-time">最後更新：{data.get("updated_at_utc", "")}</div>', unsafe_allow_html=True)

# 市場網格
targets = [("EWT", "MSCI 台灣"), ("^SOX", "費半"), ("YM=F", "道瓊期"), ("NQ=F", "納指期"), ("TSM", "台積電"), ("NVDA", "NVIDIA")]
grid_html = '<div class="m-grid">'
for sym, name in targets:
    q = fetch_yf_data(sym, name)
    if q["ok"]:
        cls = "up" if q["pct"] > 0 else "down" if q["pct"] < 0 else ""
        grid_html += f'<div class="m-tile"><div class="m-name">{q["name"]}</div><div class="m-price">{round(q["price"], 1)}</div><div class="m-pct {cls}">{round(q["pct"], 2)}%</div></div>'
    else: grid_html += f'<div class="m-tile"><div class="m-name">{name}</div><div class="m-price">-</div></div>'
grid_html += '</div>'
st.markdown(grid_html, unsafe_allow_html=True)

# AI 摘要
st.markdown('<div style="font-size:15px; font-weight:800; margin-bottom:8px;">AI 分析摘要</div>', unsafe_allow_html=True)
st.info(data.get("report", ""))

# 新聞雙欄並列 (左 1-10, 右 11-20)
st.markdown('<div style="font-size:15px; font-weight:800; margin:15px 0 10px 0;">即時新聞 (左1-10 | 右11-20)</div>', unsafe_allow_html=True)
news = data.get("news", [])

if news:
    # 拆分新聞
    col_left_data = news[0:10]
    col_right_data = news[10:20]
    
    # 構建 HTML
    news_html = '<div class="news-container">'
    
    # 左欄
    news_html += '<div class="news-column">'
    for n in col_left_data:
        src = urlparse(n.get("link", "")).netloc.replace("www.", "")
        news_html += f'<div class="news-card"><div class="news-title">{n.get("title")}</div><span class="source-tag">{src}</span></div>'
    news_html += '</div>'
    
    # 右欄
    news_html += '<div class="news-column">'
    for n in col_right_data:
        src = urlparse(n.get("link", "")).netloc.replace("www.", "")
        news_html += f'<div class="news-card"><div class="news-title">{n.get("title")}</div><span class="source-tag">{src}</span></div>'
    news_html += '</div>'
    
    news_html += '</div>'
    st.markdown(news_html, unsafe_allow_html=True)
