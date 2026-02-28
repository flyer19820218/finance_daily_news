import os
import json
from datetime import datetime, timedelta, timezone, date

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup

import yfinance as yf

LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

st.title("📈 財經AI快報")
st.caption("每日 06:00（台北）自動更新｜Telegram 推播同步｜重大事件排序｜台股影響判讀｜投資觀察")

# -------------------------
# Data helpers (report)
# -------------------------
@st.cache_data(ttl=60)
def load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def list_history_files():
    if not os.path.exists(HISTORY_DIR):
        return []
    files = [fn for fn in os.listdir(HISTORY_DIR) if fn.endswith(".json")]
    files.sort(reverse=True)
    return files

def fmt_updated(updated_at_utc: str) -> str:
    try:
        dt_utc = datetime.fromisoformat(updated_at_utc.replace("Z", "")).replace(tzinfo=timezone.utc)
        return dt_utc.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return updated_at_utc or "-"

# -------------------------
# Market data helpers
# -------------------------
@st.cache_data(ttl=60 * 30)  # 30 mins cache
def yf_series(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.Series:
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
    if df is None or df.empty:
        return pd.Series(dtype=float)
    s = df["Close"].dropna()
    s.name = ticker
    return s

@st.cache_data(ttl=60 * 60)  # 1 hour cache
def taifex_txf_close(days: int = 90) -> pd.Series:
    """
    嘗試抓期交所(taifex) TX(台指期) 近 N 天收盤/結算資料。
    由於期交所頁面格式可能變動，若抓不到會回傳空 Series。
    """
    # 期交所日報通常需要逐日查；這裡做「近幾天」逐日抓取（有 cache，避免重複打）
    end = date.today()
    start = end - timedelta(days=days)

    rows = []
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0"
    })

    # 逐日抓（只取有資料的交易日）
    d = start
    while d <= end:
        # 避免太頻繁：在 Streamlit Cloud 其實還好，且有 cache
        query_date = d.strftime("%Y/%m/%d")

        # 期交所「期貨每日行情」(HTML)
        # commodity_id=TX 是台指期 (TX)；不同站點可能參數名略不同
        url = "https://www.taifex.com.tw/cht/3/futDailyMarketReport"
        params = {
            "queryType": "2",
            "marketCode": "0",
            "commodity_id": "TX",
            "queryDate": query_date,
            "MarketCode": "0",
            "commodityId": "TX",
        }

        try:
            r = session.get(url, params=params, timeout=15)
            if r.status_code != 200 or not r.text:
                d += timedelta(days=1)
                continue

            # 用 pandas read_html 抓表格比較穩（lxml 已在 requirements）
            tables = pd.read_html(r.text)
            if not tables:
                d += timedelta(days=1)
                continue

            # 通常第一個大表就是行情表；我們找「收盤價」或「結算價」欄位
            found = None
            for t in tables:
                cols = [str(c) for c in t.columns]
                if any("收盤" in c for c in cols) or any("結算" in c for c in cols):
                    found = t
                    break

            if found is None or found.empty:
                d += timedelta(days=1)
                continue

            # 有些表會包含多個到期月份；取第一列（近月）或「到期月份」最小者
            # 欄位名稱可能是：到期月份(週別)、收盤價、結算價
            t = found.copy()

            # 嘗試找「到期月份」欄
            month_col = None
            for c in t.columns:
                if "到期" in str(c) and ("月" in str(c) or "週" in str(c)):
                    month_col = c
                    break

            if month_col is not None:
                # 取排序後第一筆（近月）
                t = t.sort_values(by=month_col, ascending=True)

            # 收盤價優先，沒有就用結算價
            close_col = None
            for c in t.columns:
                if "收盤" in str(c):
                    close_col = c
                    break
            if close_col is None:
                for c in t.columns:
                    if "結算" in str(c):
                        close_col = c
                        break

            if close_col is None:
                d += timedelta(days=1)
                continue

            val = t.iloc[0][close_col]
            try:
                val = float(str(val).replace(",", "").strip())
            except Exception:
                d += timedelta(days=1)
                continue

            rows.append((pd.to_datetime(d), val))

        except Exception:
            # 當天抓不到就跳過
            pass

        d += timedelta(days=1)

    if not rows:
        return pd.Series(dtype=float)

    s = pd.Series({dt: v for dt, v in rows}).sort_index()
    s.name = "TAIFEX:TXF (TX)"
    return s

def plot_series(title: str, s: pd.Series):
    if s is None or s.empty:
        st.warning(f"{title}：資料抓不到（可能資料源限制或當前網路/格式變動）")
        return
    df = s.to_frame("Close")
    st.write(f"**{title}**")
    fig = plt.figure()
    plt.plot(df.index, df["Close"])
    plt.xticks(rotation=0)
    st.pyplot(fig, clear_figure=True)

# -------------------------
# TOP charts
# -------------------------
st.subheader("🌍 全球重要股市 / 期貨 / 個股（自己抓資料繪圖）")
mobile = st.toggle("📱 手機模式（窄螢幕用）", value=False)

# 1) 台指期：先抓 TAIFEX，抓不到 fallback ^TWII（加權）
txf = taifex_txf_close(days=120)
if txf.empty:
    txf = yf_series("^TWII", period="6mo")  # fallback
    txf_title = "台指期（抓不到 TXF 時以加權 ^TWII 代替）"
else:
    txf_title = "台指期（TAIFEX TX 近月）"

# 其餘：yfinance
sox = yf_series("^SOX", period="6mo")
ymf = yf_series("YM=F", period="6mo")   # 道瓊期
ndx = yf_series("^NDX", period="6mo")   # 納指（也可改 NQ=F）
tsm = yf_series("TSM", period="6mo")
nvda = yf_series("NVDA", period="6mo")

series_list = [
    (txf_title, txf),
    ("費半（^SOX）", sox),
    ("道瓊期（YM=F）", ymf),
    ("納指（^NDX）", ndx),
    ("台積電 ADR（TSM）", tsm),
    ("NVIDIA（NVDA）", nvda),
]

if mobile:
    for title, s in series_list:
        plot_series(title, s)
else:
    # 兩列三欄
    r1 = series_list[:3]
    r2 = series_list[3:]

    c1, c2, c3 = st.columns(3)
    with c1: plot_series(*r1[0])
    with c2: plot_series(*r1[1])
    with c3: plot_series(*r1[2])

    c4, c5, c6 = st.columns(3)
    with c4: plot_series(*r2[0])
    with c5: plot_series(*r2[1])
    with c6: plot_series(*r2[2])

st.divider()

# -------------------------
# Report section
# -------------------------
st.subheader("📰 快報內容")
history_files = list_history_files()
mode = st.radio("顯示內容", ["最新（今日）", "歷史回顧"], horizontal=True)

data = None
label = "今日"

if mode == "最新（今日）":
    data = load_json(LATEST_FILE)
else:
    if not history_files:
        st.warning("目前沒有歷史報告（請確認 agent 有存 data/history/YYYY-MM-DD.json 且 workflow 有 git add data/history）。")
        st.stop()
    pick = st.selectbox("選擇日期", history_files, index=0)
    data = load_json(os.path.join(HISTORY_DIR, pick))
    label = pick.replace(".json", "")

if not data:
    st.warning("尚未產生報告（或檔案讀取失敗）。請確認 GitHub Actions 是否成功執行。")
    st.stop()

st.info(f"顯示：{label}｜最後更新：{fmt_updated(data.get('updated_at_utc',''))}")

if mobile:
    st.subheader("🧠 AI 快報")
    st.markdown(data.get("report", ""))

    st.subheader("🗞️ 新聞列表")
    q = st.text_input("搜尋（標題/摘要）", placeholder="例如：Fed、CPI、台積電、AI、油價…")
    news = data.get("news", [])
    if q:
        ql = q.lower()
        news = [n for n in news if ql in (n.get("title","") + " " + n.get("summary","")).lower()]
    st.write(f"共 {len(news)} 則")
    for n in news:
        with st.container(border=True):
            st.markdown(f"**{n.get('title','')}**")
            if n.get("link"):
                st.markdown(f"[閱讀原文]({n.get('link')})")
            with st.expander("摘要"):
                st.write(n.get("summary",""))
else:
    left, right = st.columns([1.35, 0.65], gap="large")
    with left:
        st.subheader("🧠 AI 快報")
        st.markdown(data.get("report", ""))
    with right:
        st.subheader("🗞️ 新聞列表")
        q = st.text_input("搜尋（標題/摘要）", placeholder="例如：Fed、CPI、台積電、AI、油價…")
        news = data.get("news", [])
        if q:
            ql = q.lower()
            news = [n for n in news if ql in (n.get("title","") + " " + n.get("summary","")).lower()]
        st.write(f"共 {len(news)} 則")
        for n in news:
            with st.container(border=True):
                st.markdown(f"**{n.get('title','')}**")
                if n.get("link"):
                    st.markdown(f"[閱讀原文]({n.get('link')})")
                with st.expander("摘要"):
                    st.write(n.get("summary",""))
