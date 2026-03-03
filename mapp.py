import streamlit as st
import yfinance as yf
import json
import os
import requests
import pandas as pd
from urllib.parse import urlparse

# 1. 頁面配置
st.set_page_config(page_title="財經AI快報-手機特務版", page_icon="📱", layout="wide")

# 2. 核心 CSS (極致壓縮版 3x2 網格)
st.markdown("""
<style>
:root{
  --up:#16a34a; --down:#ef4444; --text:#0f172a; --muted:#64748b; --border:#e7ebf3;
}
.block-container { padding: 0.8rem 0.6rem !important; }
.stApp { background:#ffffff; font-family: "翩翩體", "PingFang TC", sans-serif; }

/* 標題區 */
.brand { font-size: 28px; font-weight: 900; color: var(--text); letter-spacing: -0.5px; margin-bottom: 2px;}
.sub { color: var(--muted); font-size: 13px; margin-bottom: 8px; }
.update-time { font-size: 11px; color: #94a3b8; margin-bottom: 12px; }

/* 整合版外資專用表格 CSS */
.combined-table { width: 100%; border-collapse: collapse; text-align: center; margin-bottom: 20px; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.combined-table th { background: #f1f5f9; padding: 8px 4px; border-bottom: 2px solid #cbd5e1; color: #475569; font-size: 12px; }
.combined-table td { padding: 8px 4px; border-bottom: 1px solid #e2e8f0; }

/* 3x2 市場網格 (極致壓縮) */
.m-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px;
  background: #f8fafc; border: 1px solid var(--border);
  border-radius: 12px; padding: 6px; margin-bottom: 20px;
}
.m-tile {
  background: #ffffff; border: 1px solid var(--border);
  border-radius: 8px; padding: 6px 2px; text-align: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
  overflow: hidden;
}
.m-name { color: var(--muted); font-size: 9px; white-space: nowrap; letter-spacing: -0.3px; }
.m-price { font-size: 15px; font-weight: 900; margin: 2px 0; color: #0f172a; letter-spacing: -0.5px; }
.m-pct { font-size: 10px; font-weight: 800; }
.up { color: var(--up); } .down { color: var(--down); }

/* 雙欄新聞區域 */
.news-container { display: flex; gap: 8px; align-items: flex-start; margin-bottom: 20px; }
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

# 3. 數據抓取 (YF 與 HiStock)
@st.cache_data(ttl=60)
def fetch_yf_data(symbol, name):
    try:
        t = yf.Ticker(symbol)
        info = getattr(t, "fast_info", None)
        if info:
            last = getattr(info, "last_price", getattr(info, "lastPrice", None))
            prev = getattr(info, "previous_close", getattr(info, "previousClose", None))
            if last and prev:
                return {"name": name, "ok": True, "price": last, "pct": ((last-prev)/prev)*100}
    except: pass
    return {"name": name, "ok": False}

@st.cache_data(ttl=600)
def fetch_histock_tables():
    url = "https://histock.tw/stock/three.aspx"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        tables = pd.read_html(res.text)
        df_inst, df_fut = None, None
        for tbl in tables:
            if isinstance(tbl.columns, pd.MultiIndex):
                tbl.columns = [col[-1] for col in tbl.columns]
            cols = list(tbl.columns)
            if '外資' in cols and '投信' in cols and '總計' in cols:
                if '自營(總)' in cols: df_inst = tbl.head(5)
                elif '自營' in cols and len(cols) == 5: df_fut = tbl.head(5)
        return df_inst, df_fut
    except:
        return None, None

def render_combined_foreign_table(df_inst, df_fut):
    """將現貨與期貨整合成單一外資專屬表格，只留三天，最新一天粗體加大"""
    if df_inst is None or df_fut is None: return ""
    
    html = '<div style="font-size:15px; font-weight:800; margin:10px 0 5px 0; color:#1e293b;">🏦 外資籌碼動向 (近三日)</div>'
    html += '<table class="combined-table">'
    html += '<tr><th>日期</th><th>現貨買賣(億)</th><th>期貨未平倉(口)</th></tr>'
    
    # 確保兩邊資料對齊，且最多只取 3 筆
    max_rows = min(3, len(df_inst), len(df_fut))
    for i in range(max_rows):
        date_str = df_inst.iloc[i].get('日期', '')
        spot_val = df_inst.iloc[i].get('外資', '')
        fut_val = df_fut.iloc[i].get('外資', '')
        
        # 決定顏色：台股慣例 負數(賣)=綠, 正數(買)=紅
        def get_color(val_str):
            try:
                num = float(str(val_str).replace(',', ''))
                return "#16a34a" if num < 0 else "#ef4444"
            except: return "#0f172a"
            
        spot_color = get_color(spot_val)
        fut_color = get_color(fut_val)
        
        # 第一天(最新一天) 樣式特別處理
        if i == 0:
            row_style = "font-weight: 900; font-size: 15px; background: #fffbeb;"
            date_weight = "font-weight: 900;"
        else:
            row_style = "font-size: 13px;"
            date_weight = "color: #64748b;"
            
        html += f'<tr style="{row_style}">'
        html += f'<td style="{date_weight}">{date_str}</td>'
        html += f'<td style="color: {spot_color};">{spot_val}</td>'
        html += f'<td style="color: {fut_color};">{fut_val}</td>'
        html += '</tr>'
        
    html += '</table>'
    return html

# 4. JSON 讀取
LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"
mode = st.radio("檢視模式", ["最新（今日）", "歷史回顧"], horizontal=True)
data = None

if mode == "最新（今日）":
    if os.path.exists(LATEST_FILE):
        with open(LATEST_FILE, "r", encoding="utf-8") as f: data = json.load(f)
else:
    if os.path.exists(HISTORY_DIR):
        hist_files = sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")], reverse=True)
        if hist_files:
            pick = st.selectbox("選擇日期", hist_files, index=0, format_func=lambda x: x.replace(".json", ""))
            with open(os.path.join(HISTORY_DIR, pick), "r", encoding="utf-8") as f: data = json.load(f)
        else:
            st.warning("尚無歷史資料"); st.stop()
    else:
        st.warning("歷史資料夾不存在"); st.stop()

if not data:
    st.warning("找不到資料檔案，請確認 data 目錄。"); st.stop()

# 5. 大標題
st.markdown(f'''
<div class="brand">財經AI快報</div>
<div class="sub">每日重點整理（重大事件｜台股影響｜投資觀察）</div>
<div class="update-time">最後更新（UTC）：{data.get("updated_at_utc", "")}</div>
''', unsafe_allow_html=True)

# 6. 🌍 全球市場快照 (3x2 壓縮版)
st.markdown('<div style="font-size:15px; font-weight:800; margin:5px 0 10px 0; color:#1e293b;">🌍 全球市場快照</div>', unsafe_allow_html=True)
targets = [("EWT", "MSCI 台灣"), ("^SOX", "費半"), ("YM=F", "道瓊期"), ("NQ=F", "納指期"), ("TSM", "台積電-adr"), ("NVDA", "NVIDIA")]
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

# 7. 🏦 整合版外資籌碼表
df_inst, df_fut = fetch_histock_tables()
st.markdown(render_combined_foreign_table(df_inst, df_fut), unsafe_allow_html=True)

# 8. 🤖 AI 摘要
st.markdown('<div style="font-size:15px; font-weight:800; margin-bottom:8px; color:#1e293b;">🤖 AI 盤勢快評</div>', unsafe_allow_html=True)
st.info(data.get("report", ""))

# 9. 📰 雙欄並列新聞
st.markdown('<div style="font-size:15px; font-weight:800; margin:20px 0 10px 0; color:#1e293b;">📰 即時新聞快報</div>', unsafe_allow_html=True)
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
