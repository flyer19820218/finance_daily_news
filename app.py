import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
import yfinance as yf


# =========================
# 基本設定
# =========================
st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

LATEST_FILE = Path("data/latest_report.json")
HISTORY_DIR = Path("data/history")

# 你要的 6 個（台指期改富台指）
SYMBOLS = [
    ("富台指期（FTX）", "FTX=F"),
    ("費半（SOX）", "^SOX"),
    ("道瓊期（YM）", "YM=F"),
    ("納指期（NQ）", "NQ=F"),
    ("台積電 ADR（TSM）", "TSM"),
    ("NVIDIA（NVDA）", "NVDA"),
]


# =========================
# 工具：讀 JSON
# =========================
@st.cache_data(ttl=10)
def load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def list_history_files():
    if not HISTORY_DIR.exists():
        return []
    files = sorted([p.name for p in HISTORY_DIR.glob("*.json")], reverse=True)
    return files


# =========================
# 工具：抓市場報價（yfinance）
# =========================
@st.cache_data(ttl=60)
def get_quote(symbol: str):
    """
    回傳:
      dict(price, change, pct) 或 None
    """
    try:
        t = yf.Ticker(symbol)

        # 先試 fast_info（比較快、比較穩）
        fi = getattr(t, "fast_info", None)
        if fi:
            last = fi.get("last_price") or fi.get("lastPrice")
            prev = fi.get("previous_close") or fi.get("previousClose")
            if last is not None and prev not in (None, 0):
                last = float(last)
                prev = float(prev)
                ch = last - prev
                pct = (ch / prev) * 100
                return {"price": last, "change": ch, "pct": pct}

        # fallback：用 intraday
        hist = t.history(period="1d", interval="5m")
        if hist is None or hist.empty:
            return None

        last = float(hist["Close"].iloc[-1])
        first = float(hist["Close"].iloc[0])
        if first == 0:
            return None

        ch = last - first
        pct = (ch / first) * 100
        return {"price": last, "change": ch, "pct": pct}
    except Exception:
        return None


# =========================
# Header
# =========================
st.title("📈 財經AI快報")
st.caption("每日市場重點整理（重大事件｜台股影響｜投資觀察）")

mode = st.radio("檢視模式", ["最新（今日）", "歷史回顧"], horizontal=True)

# =========================
# 讀資料（最新 or 歷史）
# =========================
data = None

if mode == "最新（今日）":
    data = load_json(str(LATEST_FILE))
else:
    files = list_history_files()
    if not files:
        st.warning("找不到歷史資料（data/history/）。請先跑一次 agent 產生資料。")
        st.stop()
    pick = st.selectbox("選擇日期", files, index=0)
    data = load_json(str(HISTORY_DIR / pick))

if not data:
    st.warning("找不到資料檔。請確認 data/latest_report.json 是否存在，或先跑一次 agent。")
    st.stop()

updated = data.get("updated_at_utc", "")
if updated:
    st.info(f"最後更新（UTC）：{updated}")

# =========================
# 市場快照（你要：一橫排 6 個）
# =========================
st.subheader("全球市場快照（文字）")

cols = st.columns(6)  # ✅ 強制一排 6 個（桌機）
for i, (name, symbol) in enumerate(SYMBOLS):
    q = get_quote(symbol)
    with cols[i]:
        st.caption(name)
        if not q:
            st.markdown("### -")
            st.caption("資料讀取失敗")
        else:
            price = q["price"]
            ch = q["change"]
            pct = q["pct"]
            st.markdown(f"### {price:,.2f}")
            if ch > 0:
                st.success(f"▲ {ch:,.2f}（{pct:.2f}%）")
            elif ch < 0:
                st.error(f"▼ {ch:,.2f}（{pct:.2f}%）")
            else:
                st.write(f"— {ch:,.2f}（{pct:.2f}%）")

st.divider()

# =========================
# 主體：左 AI / 右 新聞
# =========================
left, right = st.columns([1.35, 0.65], gap="large")

with left:
    st.subheader("AI 分析摘要")
    report = data.get("report", "")
    if report:
        st.markdown(report)
    else:
        st.info("目前沒有 AI 報告內容。")

with right:
    st.subheader("新聞清單")

    news = data.get("news", []) or []
    total = len(news)

    # 分頁：每頁 10 則
    page_size = 10
    total_pages = max(1, math.ceil(total / page_size))

    if "news_page" not in st.session_state:
        st.session_state.news_page = 1

    # 如果總頁數變少，避免超出
    st.session_state.news_page = max(1, min(st.session_state.news_page, total_pages))

    st.caption(f"第 {st.session_state.news_page} / {total_pages} 頁（共 {total} 則）")

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("← 上一頁", use_container_width=True, disabled=(st.session_state.news_page <= 1)):
            st.session_state.news_page -= 1
            st.rerun()
    with c2:
        if st.button("下一頁 →", use_container_width=True, disabled=(st.session_state.news_page >= total_pages)):
            st.session_state.news_page += 1
            st.rerun()

    st.write("")  # spacing

    start = (st.session_state.news_page - 1) * page_size
    end = start + page_size
    page_items = news[start:end]

    for n in page_items:
        title = (n.get("title") or "").strip()
        link = (n.get("link") or "").strip()

        source = ""
        if link:
            try:
                source = urlparse(link).netloc.replace("www.", "")
            except Exception:
                source = ""

        # 一張卡：標題 + 同一行「來源｜閱讀原文」
        with st.container(border=True):
            st.markdown(f"**{title}**")

            row_parts = []
            if source:
                row_parts.append(source)
            if link:
                row_parts.append(f"[閱讀原文]({link})")

            if row_parts:
                st.caption(" ｜ ".join(row_parts))
