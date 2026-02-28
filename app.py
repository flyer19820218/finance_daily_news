import streamlit as st
import yfinance as yf
import json
from datetime import datetime
from pathlib import Path

# =========================
# 基本設定
# =========================
st.set_page_config(
    page_title="財經AI快報",
    layout="wide"
)

st.title("📈 財經AI快報")

# =========================
# 讀取最新報告（如果存在）
# =========================
DATA_PATH = Path("data/latest_report.json")

if DATA_PATH.exists():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    updated = data.get("updated_at_utc", "")
    if updated:
        st.caption(f"最後更新 (UTC)：{updated}")

    st.divider()
    st.subheader("今日市場重點")
    st.markdown(data.get("report", ""))
else:
    st.info("尚未產生每日報告資料。")

st.divider()

# =========================
# 全球市場快照（文字版）
# =========================
st.subheader("全球市場快照")

SYMBOLS = {
    "富台指期 (FTX)": "FTX=F",
    "費半 (SOX)": "^SOX",
    "道瓊期 (YM)": "YM=F",
    "納指期 (NQ)": "NQ=F",
    "台積電 ADR (TSM)": "TSM",
    "NVIDIA (NVDA)": "NVDA",
}

def get_quote(symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d", interval="5m")

        if hist.empty:
            return None

        last = hist["Close"].iloc[-1]
        first = hist["Close"].iloc[0]

        change = last - first
        pct = (change / first) * 100

        return {
            "price": float(last),
            "change": float(change),
            "pct": float(pct)
        }
    except:
        return None

cols = st.columns(6)

for i, (name, symbol) in enumerate(SYMBOLS.items()):
    with cols[i]:
        st.caption(name)
        quote = get_quote(symbol)

        if not quote:
            st.markdown("### -")
            st.caption("資料讀取失敗")
        else:
            price = quote["price"]
            change = quote["change"]
            pct = quote["pct"]

            st.markdown(f"### {price:,.2f}")

            if change > 0:
                st.success(f"▲ {change:,.2f} ({pct:.2f}%)")
            elif change < 0:
                st.error(f"▼ {change:,.2f} ({pct:.2f}%)")
            else:
                st.write(f"{change:,.2f} ({pct:.2f}%)")

st.divider()
