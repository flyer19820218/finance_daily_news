import streamlit as st
import yfinance as yf
import json
import os

# 1. 頁面配置
st.set_page_config(page_title="財經快報-手機版", page_icon="📱", layout="wide")

# 2. 定義路徑
LATEST_FILE = "data/latest_report.json"

# 3. 核心 CSS：保證手機絕對 2x3
st.markdown("""
<style>
.stApp { background:#ffffff; font-family: sans-serif; }
.m-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    background: #f7f9fc;
    border: 1px solid #e7ebf3;
    border-radius: 18px;
    padding: 16px;
}
.m-tile {
    background: #ffffff;
    border: 1px solid #e7ebf3;
    border-radius: 16px;
    padding: 15px;
    text-align: center;
}
.m-name { color: #64748b; font-size: 13px; }
.m-price { font-size: 24px; font-weight: 900; margin: 5px 0; }
.up { color: #16a34a; font-weight: 800; }
.down { color: #ef4444; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# 4. 數據抓取函數
@st.cache_data(ttl=60)
def fetch_yf(symbol, display_name):
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
data = {"report": "資料讀取中..."}
if os.path.exists(LATEST_FILE):
    with open(LATEST_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

# 6. 渲染介面
st.markdown('<div style="font-size:20px; font-weight:800; margin-bottom:10px;">全球市場快照</div>', unsafe_allow_html=True)

# 抓取數據 (使用 MSCI 台灣代理)
targets = [
    ("EWT", "MSCI 台灣"), ("^SOX", "費半"), ("YM=F", "道瓊期"),
    ("NQ=F", "納指期"), ("TSM", "台積電"), ("NVDA", "NVIDIA")
]

grid_html = '<div class="m-grid">'
for sym, name in targets:
    q = fetch_yf(sym, name)
    if q["ok"]:
        cls = "up" if q["pct"] > 0 else "down" if q["pct"] < 0 else ""
        sign = "+" if q["pct"] > 0 else ""
        grid_html += f'''
        <div class="m-tile">
            <div class="m-name">{q["name"]}</div>
            <div class="m-price">{round(q["price"], 2)}</div>
            <div class="{cls}">{sign}{round(q["pct"], 2)}%</div>
        </div>'''
    else:
        grid_html += f'<div class="m-tile"><div>{name}</div><div>-</div></div>'
grid_html += '</div>'

st.markdown(grid_html, unsafe_allow_html=True)

st.markdown('<div style="font-size:18px; font-weight:800; margin-top:20px;">AI 分析摘要</div>', unsafe_allow_html=True)
st.info(data.get("report"))
