import json
import os
from datetime import datetime, timezone

import streamlit as st
import yfinance as yf
import pandas as pd

LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

st.title("📈 財經AI快報")
st.caption("每日 06:00（台北）自動更新｜Telegram 推播同步｜重大事件排序｜台股影響判讀｜投資觀察")

# --------------------------------------------------
# 市場數據（純文字版）
# --------------------------------------------------

@st.cache_data(ttl=300)  # 5分鐘更新一次
def get_quote(ticker):
    try:
        df = yf.download(ticker, period="2d", interval="1d", progress=False)
        if df.empty:
            return None

        latest = df.iloc[-1]["Close"]
        prev = df.iloc[-2]["Close"] if len(df) > 1 else latest

        change = latest - prev
        pct = (change / prev) * 100 if prev != 0 else 0

        return {
            "price": round(latest, 2),
            "change": round(change, 2),
            "pct": round(pct, 2)
        }
    except:
        return None


def show_quote(name, ticker):
    q = get_quote(ticker)

    if not q:
        st.write(f"{name}：資料讀取失敗")
        return

    arrow = "▲" if q["change"] > 0 else "▼" if q["change"] < 0 else "-"
    color = "green" if q["change"] > 0 else "red" if q["change"] < 0 else "gray"

    st.markdown(
        f"""
        <div style="padding:6px 0;">
            <strong>{name}</strong><br>
            <span style="font-size:20px;">{q["price"]}</span>
            <span style="color:{color};">
                {arrow} {q["change"]} ({q["pct"]}%)
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )


st.subheader("🌍 全球重要市場（即時文字）")

mobile = st.toggle("📱 手機模式", value=False)

markets = [
    ("台指期（TX）", "TX=F"),   # Yahoo 可能抓不到完整連續近月，但先試
    ("納指期（NQ）", "NQ=F"),
    ("費半（SOX）", "^SOX"),
    ("道瓊（DJI）", "^DJI"),
    ("台積電 ADR", "TSM"),
    ("NVIDIA", "NVDA"),
]

if mobile:
    col1, col2 = st.columns(2)
    for i, m in enumerate(markets):
        with (col1 if i % 2 == 0 else col2):
            show_quote(*m)
else:
    cols = st.columns(6)
    for col, m in zip(cols, markets):
        with col:
            show_quote(*m)

st.divider()

# --------------------------------------------------
# 報告區
# --------------------------------------------------

@st.cache_data(ttl=60)
def load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

def list_history_files():
    if not os.path.exists(HISTORY_DIR):
        return []
    files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")]
    files.sort(reverse=True)
    return files

st.subheader("📰 快報內容")

history_files = list_history_files()
mode = st.radio("顯示內容", ["最新（今日）", "歷史回顧"], horizontal=True)

data = None
label = "今日"

if mode == "最新（今日）":
    data = load_json(LATEST_FILE)
else:
    if history_files:
        pick = st.selectbox("選擇日期", history_files)
        data = load_json(os.path.join(HISTORY_DIR, pick))
        label = pick.replace(".json", "")

if not data:
    st.warning("尚未產生報告")
    st.stop()

updated = data.get("updated_at_utc", "")
st.info(f"顯示：{label}｜更新時間：{updated}")

left, right = st.columns([1.4, 0.6])

with left:
    st.subheader("🧠 AI 快報")
    st.markdown(data.get("report", ""))

with right:
    st.subheader("🗞️ 新聞列表")
    news = data.get("news", [])
    st.write(f"共 {len(news)} 則")
    for n in news:
        with st.container(border=True):
            st.markdown(f"**{n.get('title','')}**")
            if n.get("link"):
                st.markdown(f"[閱讀原文]({n.get('link')})")
