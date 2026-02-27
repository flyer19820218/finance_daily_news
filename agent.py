import json
from datetime import datetime, timezone
import streamlit as st

DATA_FILE = "data/latest_report.json"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

st.title("📈 財經AI快報")
st.caption("每日 06:00（台北）自動更新｜Telegram 推播同步｜重大事件排序｜台股影響判讀｜投資觀察")

@st.cache_data(ttl=60)
def load_report():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None

data = load_report()

if not data:
    st.warning("尚未產生今日報告（或檔案讀取失敗）。請確認 GitHub Actions 排程是否已執行。")
    st.stop()

updated_at_utc = data.get("updated_at_utc", "")
title = data.get("title", "財經AI快報")
report = data.get("report", "")
news = data.get("news", [])

# 顯示更新時間
try:
    dt_utc = datetime.fromisoformat(updated_at_utc.replace("Z", "")).replace(tzinfo=timezone.utc)
    st.info(f"最後更新（UTC）：{dt_utc.strftime('%Y-%m-%d %H:%M')}｜（台北）約 {dt_utc.astimezone().strftime('%Y-%m-%d %H:%M')}")
except Exception:
    st.info(f"最後更新：{updated_at_utc}")

left, right = st.columns([1.25, 0.75], gap="large")

with left:
    st.subheader("🧠 AI 快報")
    st.markdown(report)

with right:
    st.subheader("🗞️ 新聞來源")
    q = st.text_input("搜尋（標題/摘要）", placeholder="例如：Fed、CPI、台積電、AI、油價…")
    if q:
        ql = q.lower()
        filtered = []
        for n in news:
            text = (n.get("title", "") + " " + n.get("summary", "")).lower()
            if ql in text:
                filtered.append(n)
        news_show = filtered
    else:
        news_show = news

    st.write(f"共 {len(news_show)} 則（近 24 小時）")

    for n in news_show:
        with st.container(border=True):
            st.markdown(f"**{n.get('title','')}**")
            dt = n.get("dt_utc", "")
            if dt:
                st.caption(f"時間（UTC）：{dt}")
            link = n.get("link", "")
            if link:
                st.markdown(f"[閱讀原文]({link})")
            with st.expander("摘要"):
                st.write(n.get("summary", ""))
