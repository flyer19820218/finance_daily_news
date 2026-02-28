import json
import os
from datetime import datetime, timezone

import streamlit as st

LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

st.title("📈 財經AI快報")
st.caption("每日 05:30（美股收盤）自動更新")

# -------------------------------------------------
# 讀取資料
# -------------------------------------------------
@st.cache_data(ttl=60)
def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None


data = load_json(LATEST_FILE)

if not data:
    st.warning("尚未產生報告")
    st.stop()

# -------------------------------------------------
# 市場快照
# -------------------------------------------------
st.subheader("🌍 全球重要市場（收盤快照）")

market = data.get("market", {})

if market:
    cols = st.columns(len(market))

    for col, (name, q) in zip(cols, market.items()):
        with col:
            if not q or q["price"] is None:
                st.write(f"{name}：-")
            else:
                arrow = "▲" if q["change"] > 0 else "▼"
                color = "green" if q["change"] > 0 else "red"
                st.markdown(
                    f"""
                    <strong>{name}</strong><br>
                    <span style="font-size:20px;">{round(q["price"],2)}</span>
                    <span style="color:{color};">
                    {arrow} {round(q["change"],2)} ({round(q["pct"],2)}%)
                    </span>
                    """,
                    unsafe_allow_html=True
                )

st.divider()

# -------------------------------------------------
# AI 快報
# -------------------------------------------------
st.subheader("🧠 AI 快報")
st.markdown(data.get("report", ""))

st.divider()

# -------------------------------------------------
# 新聞列表
# -------------------------------------------------
st.subheader("🗞️ 新聞列表")

news = data.get("news", [])
st.write(f"共 {len(news)} 則")

for n in news:
    with st.container(border=True):
        st.markdown(f"**{n.get('title','')}**")
        if n.get("link"):
            st.markdown(f"[閱讀原文]({n.get('link')})")
        with st.expander("摘要"):
            st.write(n.get("summary",""))
