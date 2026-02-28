import json
import os
from datetime import datetime, timezone
import streamlit as st
import streamlit.components.v1 as components

LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

st.title("📈 財經AI快報")
st.caption("每日 06:00（台北）自動更新｜Telegram 推播同步｜重大事件排序｜台股影響判讀｜投資觀察")

# -------- TradingView widget helper --------
def tv_symbol_widget(symbol: str, height: int = 260, interval: str = "D"):
    # interval: "1", "5", "15", "60", "D", "W", "M"
    html = f"""
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
    """
    components.html(html, height=height + 40)

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
    files = []
    for fn in os.listdir(HISTORY_DIR):
        if fn.endswith(".json"):
            files.append(fn)
    # 檔名通常是 YYYY-MM-DD.json，倒序 = 最新在前
    files.sort(reverse=True)
    return files

# -------- 1) Top market charts --------
st.subheader("🌍 全球重要股市/個股走勢")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**台指期**")
    tv_symbol_widget("TVC:TW1!")
with c2:
    st.markdown("**費半（SOX）**")
    tv_symbol_widget("NASDAQ:SOX")
with c3:
    st.markdown("**道瓊期**")
    tv_symbol_widget("CBOT_MINI:YM1!")

c4, c5, c6 = st.columns(3)
with c4:
    st.markdown("**納指（NDX）**")
    tv_symbol_widget("NASDAQ:NDX")
with c5:
    st.markdown("**台積電 ADR（TSM）**")
    tv_symbol_widget("NYSE:TSM")
with c6:
    st.markdown("**NVIDIA（NVDA）**")
    tv_symbol_widget("NASDAQ:NVDA")

st.divider()

# -------- 2) Choose report: latest or history --------
history_files = list_history_files()
mode = st.radio("顯示內容", ["最新（今日）", "歷史回顧"], horizontal=True)

data = None
selected_label = "今日"

if mode == "最新（今日）":
    data = load_json(LATEST_FILE)
    selected_label = "今日"
else:
    if not history_files:
        st.warning("目前沒有歷史報告（你需要在 agent 端開啟歷史存檔）。")
        st.stop()
    pick = st.selectbox("選擇日期", history_files, index=0)
    data = load_json(os.path.join(HISTORY_DIR, pick))
    selected_label = pick.replace(".json", "")

if not data:
    st.warning("尚未產生報告（或檔案讀取失敗）。請確認 GitHub Actions 是否成功執行。")
    st.stop()

# -------- 3) Show report --------
updated_at_utc = data.get("updated_at_utc", "")
try:
    dt_utc = datetime.fromisoformat(updated_at_utc.replace("Z", "")).replace(tzinfo=timezone.utc)
    st.info(f"顯示：{selected_label}｜最後更新（UTC）：{dt_utc.strftime('%Y-%m-%d %H:%M')}")
except Exception:
    st.info(f"顯示：{selected_label}｜最後更新：{updated_at_utc}")

left, right = st.columns([1.25, 0.75], gap="large")

with left:
    st.subheader("🧠 AI 快報")
    st.markdown(data.get("report", ""))

with right:
    st.subheader("🗞️ 新聞來源")
    q = st.text_input("搜尋（標題/摘要）", placeholder="例如：Fed、CPI、台積電、AI、油價…")
    news = data.get("news", [])
    if q:
        ql = q.lower()
        news = [n for n in news if ql in (n.get("title","") + " " + n.get("summary","")).lower()]

    st.write(f"共 {len(news)} 則（近 24 小時）")

    for n in news:
        with st.container(border=True):
            st.markdown(f"**{n.get('title','')}**")
            if n.get("dt_utc"):
                st.caption(f"時間（UTC）：{n.get('dt_utc')}")
            if n.get("link"):
                st.markdown(f"[閱讀原文]({n.get('link')})")
            with st.expander("摘要"):
                st.write(n.get("summary",""))
