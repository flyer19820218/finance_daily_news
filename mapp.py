import streamlit as st
import yfinance as yf
import json
import os
from urllib.parse import urlparse

# 1. 頁面配置
st.set_page_config(page_title="財經AI快報-手機版", page_icon="📱", layout="wide")

# 2. 核心 CSS
st.markdown("""
<style>
:root{
  --up:#16a34a; --down:#ef4444; --text:#0f172a; --muted:#64748b; --border:#e7ebf3;
}
.block-container { padding: 0.8rem 0.6rem !important; }
.stApp { background:#ffffff; font-family: "翩翩體", "PingFang TC", sans-serif; }

/* 標題區：補回完整副標題樣式 */
.brand { font-size: 28px; font-weight: 900; color: var(--text); letter-spacing: -0.5px; margin-bottom: 2px;}
.sub { color: var(--muted); font-size: 13px; margin-bottom: 8px; }
.update-time { font-size: 11px; color: #94a3b8; margin-bottom: 12px; }

/* 2x3 市場網格 */
.m-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
    background: #f8fafc; border: 1px solid var(--border);
    border-radius: 16px; padding: 10px; margin-bottom: 20px;
}
.m-tile {
    background: #ffffff; border: 1px solid var(--border);
    border-radius: 12px; padding: 8px; text-align: center;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}
.m-name { color: var(--muted); font-size: 10px; }
.m-price { font-size: 18px; font-weight: 900; margin: 2px 0; color: #0f172a; }
.m-pct { font-size: 11px; font-weight: 800; }
.up { color: var(--up); } .down { color: var(--down); }

/* 雙欄新聞區域 */
.news-container { display: flex; gap: 8px; align-items: flex-start; }
.news-column { flex: 1; }

.news-card {
    border: 1px solid var(--border); background: #fff;
    border-radius: 10px; padding: 10px; margin-bottom: 8px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    text-decoration: none; display: block;
}
.news-title { font-weight: 700; font-size: 12px; color: #1e293b; line-height: 1.4; margin-bottom: 4px; }
.source-tag { font-size: 9px; color: #64748b; background: #f1f5f9; padding: 1px 4px; border-radius: 3px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# 3. 數據抓取
@st.cache_data(ttl=60)
def fetch_yf_data(symbol, name):
    try:
        t = yf.Ticker(symbol)
        info = t.fast_info
        last, prev = info.last_price, info.previous_close
        if last and prev:
            return {"name": name, "ok": True, "price": last, "pct": ((last-prev)/prev)*100}
    except: pass
    return {"name": name, "ok": False}

# 4. 【功能回歸】最新與歷史資料切換
LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

mode = st.radio("檢視模式", ["最新（今日）", "歷史回顧"], horizontal=True)
data = None

if mode == "最新（今日）":
    if os.path.exists(LATEST_FILE):
        with open(LATEST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
else:
    if os.path.exists(HISTORY_DIR):
        hist_files = sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")], reverse=True)
        if hist_files:
            # 💡 只有這裡加了 format_func 幫你把 .json 變不見
            pick = st.selectbox("選擇日期", hist_files, index=0, format_func=lambda x: x.replace(".json", ""))
            with open(os.path.join(HISTORY_DIR, pick), "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            st.warning("尚無歷史資料")
            st.stop()
    else:
        st.warning("歷史資料夾不存在")
        st.stop()

if not data:
    st.warning("找不到資料檔案，請確認 data 目錄。")
    st.stop()

# 5. 【功能回歸】大標題與副標題
st.markdown(f'''
<div class="brand">財經AI快報</div>
<div class="sub">每日市場重點整理（重大事件｜台股影響｜投資觀察）</div>
<div class="update-time">最後更新（UTC）：{data.get("updated_at_utc", "")}</div>
''', unsafe_allow_html=True)

# 6. 市場網格
targets = [("EWT", "MSCI 台灣"), ("^SOX", "費半"), ("YM=F", "道瓊期"), ("NQ=F", "納指期"), ("TSM", "台積電"), ("NVDA", "NVIDIA")]
grid_html = '<div class="m-grid">'
for sym, name in targets:
    q = fetch_yf_data(sym, name)
    if q and q.get("ok"):
        cls = "up" if q["pct"] > 0 else "down" if q["pct"] < 0 else ""
        sign = "+" if q["pct"] > 0 else ""
        grid_html += f'<div class="m-tile"><div class="m-name">{q["name"]}</div><div class="m-price">{round(q["price"], 1)}</div><div class="m-pct {cls}">{sign}{round(q["pct"], 2)}%</div></div>'
    else:
        grid_html += f'<div class="m-tile"><div class="m-name">{name}</div><div class="m-price">-</div></div>'
grid_html += '</div>'
st.markdown(grid_html, unsafe_allow_html=True)

# 7. AI 摘要
st.markdown('<div style="font-size:15px; font-weight:800; margin-bottom:8px; color:#1e293b;">AI 分析摘要</div>', unsafe_allow_html=True)
st.info(data.get("report", ""))

# 8. 雙欄並列新聞
st.markdown('<div style="font-size:15px; font-weight:800; margin:15px 0 10px 0; color:#1e293b;">即時新聞快報</div>', unsafe_allow_html=True)
news = data.get("news", [])

if news:
    col_left = news[0:10]
    col_right = news[10:20]
    
    news_html = '<div class="news-container">'
    
    # 左欄
    news_html += '<div class="news-column">'
    for n in col_left:
        link = n.get("link", "")
        title = n.get("title", "")
        src = urlparse(link).netloc.replace("www.", "")
        news_html += f'<a class="news-card" href="{link}" target="_blank"><div class="news-title">{title}</div><span class="source-tag">{src}</span></a>'
    news_html += '</div>'
    
    # 右欄
    news_html += '<div class="news-column">'
    for n in col_right:
        link = n.get("link", "")
        title = n.get("title", "")
        src = urlparse(link).netloc.replace("www.", "")
        news_html += f'<a class="news-card" href="{link}" target="_blank"><div class="news-title">{title}</div><span class="source-tag">{src}</span></a>'
    news_html += '</div>'
    
    news_html += '</div>'
    st.markdown(news_html, unsafe_allow_html=True)
