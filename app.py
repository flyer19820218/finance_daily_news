import json
import os
from datetime import datetime

import streamlit as st

LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0e1117; color: #e6edf3; }
a { color: #58a6ff !important; }
.market-bar { background: #161b22; padding: 18px; border-radius: 14px; margin: 12px 0 22px 0; border: 1px solid #30363d; }
.market-name { font-size: 13px; opacity: 0.75; letter-spacing: 0.3px; }
.market-price { font-size: 22px; font-weight: 700; margin-top: 2px; }
.up { color: #00ff87; font-weight: 650; }
.down { color: #ff4d4f; font-weight: 650; }
.flat { color: #9da7b3; font-weight: 650; }
.hr { height:1px; background:#30363d; margin: 22px 0; }
.small { opacity: 0.7; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

st.title("📈 財經AI快報")
st.caption("每日 05:30（台北，美股收盤後）自動更新｜資料由 GitHub Actions 產生，前端只讀檔案（最穩）")

@st.cache_data(ttl=60)
def load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def list_history():
    if not os.path.exists(HISTORY_DIR):
        return []
    files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")]
    files.sort(reverse=True)
    return files

mode = st.radio("顯示", ["最新（今日）", "歷史回顧"], horizontal=True)

data = None
label = "今日"
if mode == "最新（今日）":
    data = load_json(LATEST_FILE)
else:
    hist = list_history()
    if not hist:
        st.warning("沒有歷史檔案，請先讓 workflow 成功跑一次。")
        st.stop()
    pick = st.selectbox("選擇日期", hist, index=0)
    data = load_json(os.path.join(HISTORY_DIR, pick))
    label = pick.replace(".json", "")

if not data:
    st.warning("尚未產生報告（或讀取失敗）。請先手動 Run workflow 一次。")
    st.stop()

updated = data.get("updated_at_utc", "")
st.markdown(f"<div class='small'>顯示：<b>{label}</b> ｜最後更新（UTC）：{updated}</div>", unsafe_allow_html=True)

# ------------------ Market Bar ------------------
st.subheader("🌍 全球市場收盤快照")

market = data.get("market", {})
if market:
    st.markdown("<div class='market-bar'>", unsafe_allow_html=True)

    cols = st.columns(len(market))
    for col, (name, q) in zip(cols, market.items()):
        with col:
            if not q or not q.get("ok") or q.get("price") is None:
                st.markdown(f"<div class='market-name'>{name}</div><div class='market-price'>-</div><div class='flat'>-</div>", unsafe_allow_html=True)
            else:
                ch = q.get("change") or 0
                pct = q.get("pct") or 0
                cls = "up" if ch > 0 else "down" if ch < 0 else "flat"
                arrow = "▲" if ch > 0 else "▼" if ch < 0 else "—"
                st.markdown(
                    f"""
                    <div class="market-name">{name}</div>
                    <div class="market-price">{round(float(q["price"]), 2)}</div>
                    <div class="{cls}">{arrow} {round(float(ch), 2)} ({round(float(pct), 2)}%)</div>
                    """,
                    unsafe_allow_html=True
                )

    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("目前沒有 market 快照（請確認 agent 有寫入 payload['market']）。")

st.markdown("<div class='hr'></div>", unsafe_allow_html=True)

# ------------------ Report + News ------------------
left, right = st.columns([1.35, 0.65], gap="large")

with left:
    st.subheader("🧠 AI 市場分析")
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
            with st.expander("摘要"):
                st.write(n.get("summary", ""))
