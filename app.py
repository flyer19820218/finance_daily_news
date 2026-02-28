import json
import os
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timezone

LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
      .tv-card { border: 1px solid rgba(0,0,0,0.08); border-radius: 14px; padding: 10px 12px; }
      .muted { color: rgba(0,0,0,0.55); font-size: 0.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📈 財經AI快報")
st.markdown(
    '<div class="muted">每日 06:00（台北）自動更新｜Telegram 推播同步｜重大事件排序｜台股影響判讀｜投資觀察</div>',
    unsafe_allow_html=True,
)

is_mobile = st.toggle("📱 手機版顯示模式（窄螢幕用）", value=False)

def tv_mini(symbol: str, height: int = 260, interval: str = "D"):
    html = f"""
    <div class="tv-card">
      <div class="tradingview-widget-container">
        <div class="tradingview-widget-container__widget"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js" async>
        {{
          "symbol": "{symbol}",
          "width": "100%",
          "height": "{height}",
          "locale": "zh_TW",
          "dateRange": "12M",
          "colorTheme": "light",
          "isTransparent": false,
          "autosize": true,
          "largeChartUrl": "",
          "chartOnly": false,
          "noTimeScale": false,
          "interval": "{interval}"
        }}
        </script>
      </div>
    </div>
    """
    components.html(html, height=height + 70)

def chart_block(title: str, symbol: str, note: str = ""):
    st.markdown(f"**{title}**")
    if note:
        st.caption(note)
    tv_mini(symbol, height=260)

# ✅ 改成「可嵌入」替代標的（ETF/常見可用代號）
symbols = [
    ("台股大盤（0050 代表）", "TPEX:0050", "原台指期：改用 0050 代表台股大盤"),
    ("費半（SOXX ETF）", "AMEX:SOXX", "原 SOX：改用 SOXX ETF 追蹤費半"),
    ("道瓊（DIA ETF）", "AMEX:DIA", "原道瓊期：改用 DIA ETF"),
    ("納指（QQQ ETF）", "NASDAQ:QQQ", "原 NDX：改用 QQQ ETF"),
    ("台積電 ADR（TSM）", "NYSE:TSM", ""),
    ("NVIDIA（NVDA）", "NASDAQ:NVDA", ""),
]

st.subheader("🌍 全球重要股市 / 個股走勢（Top 6）")

if is_mobile:
    for t, s, n in symbols:
        chart_block(t, s, n)
else:
    row1, row2 = symbols[:3], symbols[3:]
    c1, c2, c3 = st.columns(3)
    with c1: chart_block(*row1[0])
    with c2: chart_block(*row1[1])
    with c3: chart_block(*row1[2])

    c4, c5, c6 = st.columns(3)
    with c4: chart_block(*row2[0])
    with c5: chart_block(*row2[1])
    with c6: chart_block(*row2[2])

st.divider()

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

st.subheader("📰 快報內容")

history_files = list_history_files()
mode = st.radio("顯示內容", ["最新（今日）", "歷史回顧"], horizontal=True)

data = None
selected_label = "今日"

if mode == "最新（今日）":
    data = load_json(LATEST_FILE)
    selected_label = "今日"
else:
    if not history_files:
        st.warning("目前沒有歷史報告（請確認 agent 有存 data/history/YYYY-MM-DD.json，且 workflow 有 git add data/history）。")
        st.stop()
    pick = st.selectbox("選擇日期", history_files, index=0)
    data = load_json(os.path.join(HISTORY_DIR, pick))
    selected_label = pick.replace(".json", "")

if not data:
    st.warning("尚未產生報告（或檔案讀取失敗）。請確認 GitHub Actions 是否成功執行。")
    st.stop()

updated_at_utc = data.get("updated_at_utc", "")
try:
    dt_utc = datetime.fromisoformat(updated_at_utc.replace("Z", "")).replace(tzinfo=timezone.utc)
    st.info(f"顯示：{selected_label}｜最後更新（UTC）：{dt_utc.strftime('%Y-%m-%d %H:%M')}")
except Exception:
    st.info(f"顯示：{selected_label}｜最後更新：{updated_at_utc}")

if is_mobile:
    st.subheader("🧠 AI 快報")
    st.markdown(data.get("report", ""))

    st.subheader("🗞️ 新聞列表")
    q = st.text_input("搜尋（標題/摘要）", placeholder="例如：Fed、CPI、台積電、AI、油價…")
    news = data.get("news", [])
    if q:
        ql = q.lower()
        news = [n for n in news if ql in (n.get("title", "") + " " + n.get("summary", "")).lower()]
    st.write(f"共 {len(news)} 則")
    for n in news:
        with st.container(border=True):
            st.markdown(f"**{n.get('title','')}**")
            if n.get("link"):
                st.markdown(f"[閱讀原文]({n.get('link')})")
            with st.expander("摘要"):
                st.write(n.get("summary", ""))
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
            news = [n for n in news if ql in (n.get("title", "") + " " + n.get("summary", "")).lower()]
        st.write(f"共 {len(news)} 則")
        for n in news:
            with st.container(border=True):
                st.markdown(f"**{n.get('title','')}**")
                if n.get("link"):
                    st.markdown(f"[閱讀原文]({n.get('link')})")
                with st.expander("摘要"):
                    st.write(n.get("summary", ""))
