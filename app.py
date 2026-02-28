import json
import os
from datetime import datetime, timezone

import streamlit as st

LATEST_FILE = "data/latest_report.json"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

# =============================
# 🎨 全站黑底金融終端風格
# =============================

st.markdown("""
<style>
body {
    background-color: #0e1117;
}
.stApp {
    background-color: #0e1117;
    color: #e6edf3;
}
.market-bar {
    background-color: #161b22;
    padding: 18px;
    border-radius: 12px;
    margin-bottom: 25px;
}
.market-item {
    text-align: center;
}
.market-name {
    font-size: 14px;
    opacity: 0.7;
}
.market-price {
    font-size: 22px;
    font-weight: 600;
}
.market-change-up {
    color: #00ff87;
    font-weight: 500;
}
.market-change-down {
    color: #ff4d4f;
    font-weight: 500;
}
.divider {
    height:1px;
    background:#30363d;
    margin:30px 0;
}
</style>
""", unsafe_allow_html=True)

st.title("📈 財經AI快報")
st.caption("每日 05:30（美股收盤）自動更新")

# =============================
# 讀資料
# =============================

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

# =============================
# 🔥 專業盤面條
# =============================

st.subheader("🌍 全球市場收盤快照")

market = data.get("market", {})

if market:
    st.markdown('<div class="market-bar">', unsafe_allow_html=True)

    cols = st.columns(len(market))

    for col, (name, q) in zip(cols, market.items()):
        with col:
            if not q or q["price"] is None:
                st.markdown(f"<div class='market-item'>{name}<br>-</div>", unsafe_allow_html=True)
            else:
                arrow = "▲" if q["change"] > 0 else "▼"
                change_class = "market-change-up" if q["change"] > 0 else "market-change-down"

                st.markdown(
                    f"""
                    <div class="market-item">
                        <div class="market-name">{name}</div>
                        <div class="market-price">{round(q["price"],2)}</div>
                        <div class="{change_class}">
                            {arrow} {round(q["change"],2)} ({round(q["pct"],2)}%)
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# =============================
# 🧠 AI 快報
# =============================

st.subheader("🧠 AI 市場分析")
st.markdown(data.get("report", ""))

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# =============================
# 🗞️ 新聞列表
# =============================

st.subheader("🗞️ 今日重要新聞")

news = data.get("news", [])
st.write(f"共 {len(news)} 則")

for n in news:
    with st.container(border=True):
        st.markdown(f"**{n.get('title','')}**")
        if n.get("link"):
            st.markdown(f"[閱讀原文]({n.get('link')})")
        with st.expander("摘要"):
            st.write(n.get("summary",""))

updated = data.get("updated_at_utc", "")
st.caption(f"最後更新：{updated}")
