import streamlit as st
import yfinance as yf
import json
import os
import requests
import pandas as pd
from urllib.parse import urlparse
from datetime import datetime, time
import pytz

# 1. 頁面配置
st.set_page_config(page_title="財經AI快報-手機特務版", page_icon="📱", layout="wide")

# 2. 核心 CSS (動態方塊 + 籌碼高光 + 垂直時間軸)
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

/* 方案三：籌碼高光表格 CSS */
.combined-table { width: 100%; border-collapse: collapse; text-align: center; margin-bottom: 20px; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 6px rgba(0,0,0,0.08); }
.combined-table th { background: #1e293b; padding: 10px 4px; color: #ffffff; font-size: 12px; font-weight: 700; letter-spacing: 1px; }
.combined-table td { padding: 8px 4px; border-bottom: 1px solid #e2e8f0; }

/* 方案一：3x2 市場網格 (動態背景) */
.m-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px;
  margin-bottom: 20px;
}
.m-tile {
  background: #ffffff; border: 1px solid var(--border);
  border-radius: 10px; padding: 8px 2px; text-align: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
  transition: all 0.3s ease;
}
/* 漲跌動態背景色 */
.m-tile.up-bg { background: #f0fdf4; border-color: #bbf7d0; }
.m-tile.down-bg { background: #fef2f2; border-color: #fecaca; }

.m-name { color: var(--muted); font-size: 9px; white-space: nowrap; letter-spacing: -0.3px; font-weight: 700; }
.m-price { font-size: 16px; font-weight: 900; margin: 3px 0; color: #0f172a; letter-spacing: -0.5px; }
.m-pct { font-size: 11px; font-weight: 800; }
.up { color: var(--up); } .down { color: var(--down); }

/* 🌟 富途牛牛風格：垂直時間軸 CSS 🌟 */
.timeline-container {
    border-left: 2px solid #e2e8f0; 
    margin-left: 12px; 
    padding-left: 16px; 
    position: relative;
    margin-bottom: 30px;
}
.timeline-item {
    position: relative;
    margin-bottom: 24px; 
}
.timeline-item::before {
    content: '';
    position: absolute;
    left: -21px; /* 根據 padding 調整圓點位置貼齊直線 */
    top: 4px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #94a3b8; 
    border: 2px solid #ffffff; 
}
.timeline-time {
    font-size: 12px;
    color: #64748b;
    font-weight: 700;
    margin-bottom: 4px;
    font-family: monospace; 
}
.timeline-title {
    font-size: 15px;
    font-weight: 900;
    color: #0f172a;
    line-height: 1.4;
    margin-bottom: 6px;
    text-decoration: none;
    display: block;
}
.timeline-title:hover {
    color: #2563eb;
    text-decoration: underline;
}
.timeline-summary {
    font-size: 13px;
    color: #475569;
    line-height: 1.5;
}
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
    if df_inst is None or df_fut is None: return ""
    html = '<div style="font-size:16px; font-weight:900; margin:15px 0 8px 0; color:#1e293b;">🏦 外資籌碼動向 (近三日)</div>'
    html += '<table class="combined-table">'
    html += '<tr><th>日期</th><th>現貨買賣(億)</th><th>期貨未平倉(口)</th></tr>'
    max_rows = min(3, len(df_inst), len(df_fut))
    for i in range(max_rows):
        date_str = df_inst.iloc[i].get('日期', '')
        spot_val = df_inst.iloc[i].get('外資', '')
        fut_val = df_fut.iloc[i].get('外資', '')
        def get_color(val_str):
            try:
                num = float(str(val_str).replace(',', ''))
                return "#16a34a" if num < 0 else "#ef4444"
            except: return "#0f172a"
        spot_color = get_color(spot_val)
        fut_color = get_color(fut_val)
        if i == 0:
            row_style = "font-weight: 900; font-size: 15px; background: linear-gradient(90deg, #fffbeb 0%, #fef3c7 100%);"
            date_weight = "font-weight: 900; color: #b45309;"
        else:
            row_style = "font-size: 13px;"
            date_weight = "color: #64748b;"
        html += f'<tr style="{row_style}"><td style="{date_weight}">{date_str}</td><td style="color: {spot_color};">{spot_val}</td><td style="color: {fut_color};">{fut_val}</td></tr>'
    html += '</table>'
    return html

# ==========================================
# 4. JSON 讀取與三層式過濾 (手機版最佳化)
# ==========================================
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
            # 1. 抓取年份
            years = []
            for f in hist_files:
                y = f[:4]
                if y not in years: years.append(y)
            
            # 手機版佈局：年份與月份並排一行
            col_y, col_m = st.columns(2)
            with col_y:
                selected_year = st.selectbox("🗓️ 選擇年份", years, format_func=lambda x: f"{x} 年")
            
            # 2. 抓取月份
            months = []
            for f in hist_files:
                if f.startswith(selected_year):
                    m = f[5:7]
                    if m not in months: months.append(m)
            
            with col_m:
                selected_month = st.selectbox("📅 選擇月份", months, format_func=lambda x: f"{int(x)} 月")
            
            # 3. 獨立全寬選取特定報告，避免手指點不到
            prefix = f"{selected_year}-{selected_month}"
            filtered_hist = [f for f in hist_files if f.startswith(prefix)]
            
            if filtered_hist:
                pick = st.selectbox("📄 選擇報告", filtered_hist, index=0, format_func=lambda x: x.replace(".json", ""))
                with open(os.path.join(HISTORY_DIR, pick), "r", encoding="utf-8") as f: data = json.load(f)
            else:
                st.warning("該月份尚未產生報告。"); st.stop()
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

# ==================================================
# 6. 日夜自動切換市場快照
# ==================================================
tw_tz = pytz.timezone('Asia/Taipei')
current_tw_time = datetime.now(tw_tz).time()

# 判定時間：21:30 ~ 09:00 為美股時間
time_2130 = time(21, 30)
time_0900 = time(9, 0)
is_us_market = (current_tw_time >= time_2130 or current_tw_time < time_0900)

# 將您原本的網格產生邏輯包裝成函數，方便呼叫
def render_market_grid(title, targets_list):
    html = f'<div style="font-size:16px; font-weight:900; margin:15px 0 8px 0; color:#1e293b;">{title}</div>'
    html += '<div class="m-grid">'
    for sym, name in targets_list:
        q = fetch_yf_data(sym, name)
        if q and q.get("ok"):
            pct = q["pct"]
            bg_cls = "up-bg" if pct > 0 else "down-bg" if pct < 0 else ""
            cls = "up" if pct > 0 else "down" if pct < 0 else ""
            sign = "+" if pct > 0 else ""
            html += f'<div class="m-tile {bg_cls}"><div class="m-name">{q["name"]}</div><div class="m-price">{round(q["price"], 1)}</div><div class="m-pct {cls}">{sign}{round(pct, 2)}%</div></div>'
        else:
            html += f'<div class="m-tile"><div class="m-name">{name}</div><div class="m-price">-</div><div class="m-pct">-</div></div>'
    html += '</div>'
    return html

# 依據時間動態渲染
if is_us_market:
    us_targets = [("TSM", "台積電-adr"), ("^DJI", "道瓊工業"), ("^IXIC", "納斯達克"), ("NVDA", "NVIDIA"), ("^SOX", "費半"), ("EWT", "MSCI 台灣")]
    st.markdown(render_market_grid("🌍 全球市場快照 (美股時段)", us_targets), unsafe_allow_html=True)
else:
    # 權值股陣容
    top6_targets = [("^TWII", "加權指數"), ("2330.TW", "台積電"), ("2454.TW", "聯發科"), ("^N225", "日經225"), ("^KS11", "韓國綜合"), ("0050.TW", "元大台灣50")]
    st.markdown(render_market_grid("👑 護國神山與亞洲指數", top6_targets), unsafe_allow_html=True)
    
    # 爆量股陣容 (優先讀取 hot_stocks.json，若無則用備用)
    try:
        with open("hot_stocks.json", "r", encoding="utf-8") as f:
            vol_pool = json.load(f).get("top_volume_pool", {})
            vol_targets = [(k, v) for k, v in vol_pool.items()][:6]
    except:
        vol_targets = [("3231.TW", "緯創"), ("2603.TW", "長榮"), ("2317.TW", "鴻海"), ("2356.TW", "英業達"), ("2409.TW", "友達"), ("3481.TW", "群創")]
    
    st.markdown(render_market_grid("🔥 盤中實戰：市場人氣爆量", vol_targets), unsafe_allow_html=True)

# 7. 🏦 整合版外資籌碼表
df_inst, df_fut = fetch_histock_tables()
st.markdown(render_combined_foreign_table(df_inst, df_fut), unsafe_allow_html=True)

# 8. 🤖 AI 摘要
st.markdown('<div style="font-size:16px; font-weight:900; margin-bottom:8px; color:#1e293b;">🤖 AI 盤勢快評</div>', unsafe_allow_html=True)
st.info(data.get("report", ""))

# ==================================================
# 9. 📰 即時新聞快報 (富途牛牛垂直時間軸風格)
# ==================================================
st.markdown('<div style="font-size:16px; font-weight:900; margin:24px 0 16px 0; color:#1e293b;">📰 即時新聞快報</div>', unsafe_allow_html=True)
news = data.get("news", [])

if news:
    news_html = '<div class="timeline-container">'
    
    # 限制顯示前 15 則，避免手機滑動太長
    for n in news[:15]:
        link = n.get("link", "")
        title = n.get("title", "")
        summary = n.get("summary", "")
        
        # 處理時間：解析 UTC 時間並轉換為台灣時間的 HH:MM
        dt_str = n.get("dt_utc", "")
        try:
            dt_utc = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            dt_tw = dt_utc.astimezone(pytz.timezone('Asia/Taipei'))
            time_display = dt_tw.strftime("%H:%M")
        except:
            time_display = "今日" # 防呆機制
            
        # ⚠️ 關鍵修復：全部寫在同一行，絕對不留開頭空白，避免被 Streamlit 誤判為程式碼區塊！
        news_html += f'<div class="timeline-item"><div class="timeline-time">{time_display}</div><a href="{link}" target="_blank" class="timeline-title">{title}</a><div class="timeline-summary">{summary}</div></div>'
        
    news_html += '</div>'
    st.markdown(news_html, unsafe_allow_html=True)
else:
    st.info("目前無最新快訊資料。")
