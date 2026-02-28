import json
import os
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timezone

LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

# ---- Small CSS polish ----
st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
      h1, h2, h3 { letter-spacing: 0.2px; }
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

# ---- Detect mobile / desktop (simple client-width probe) ----
components.html(
    """
    <script>
      const w = window.innerWidth;
      const msg = {type: "streamlit:setComponentValue", value: w};
      window.parent.postMessage(msg, "*");
    </script>
    """,
    height=0,
)

# Streamlit doesn't directly capture that postMessage reliably in all setups,
# so we also give user a manual toggle as fallback.
is_mobile = st.toggle("📱 手機版顯示模式（窄螢幕用）", value=False)

# ---- TradingView widgets ----
def tv_mini(symbol: str, height: int = 260, interval: str = "D"):
    """Mini Symbol Overview (較漂亮但部分商品會被限制)"""
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
    components.html(html, height=height + 60)

def tv_advanced(symbol: str, height: int = 380, interval: str = "D"):
    """Advanced Chart (支援度高，適合期貨/指數)"""
    safe_id = "tv_" + symbol.replace(":", "_").replace("!", "_F").replace("/", "_")
    html = f"""
    <div class="tv-card">
      <div class="tradingview-widget-container">
        <div id="{safe_id}"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
          new TradingView.widget({{
            "autosize": true,
            "symbol": "{symbol}",
            "interval": "{interval}",
            "timezone": "Asia/Taipei",
            "theme": "light",
            "style": "1",
            "locale": "zh_TW",
            "enable_publishing": false,
            "hide_top_toolbar": true,
            "hide_legend": false,
            "save_image": false,
            "container_id": "{safe_id}"
          }});
        </script>
      </div>
    </div>
    """
    components.html(html, height=height + 40)

def chart_block(title: str, symbol: str, widget: str):
    st.markdown(f"**{title}**")
    if widget == "advanced":
        tv_advanced(symbol, height=360)
    else:
        tv_mini(symbol, height=260)

# ---- Top charts ----
st.subheader("🌍 全球重要股市 / 個股走勢（Top 6）")

# 你原本四個不行：改用 advanced（支援度高）
symbols = [
    ("台指期", "TVC:TW1!", "advanced"),
    ("費半（SOX）", "NASDAQ:SOX", "advanced"),
    ("道瓊期", "CBOT_MINI:YM1!", "advanced"),
    ("納指（NDX）", "NASDAQ:NDX", "advanced"),
    ("台積電 ADR（TSM）", "NYSE:TSM", "mini"),
    ("NVIDIA（NVDA）", "NASDAQ:NVDA", "mini"),
]

if is_mobile:
    # Mobile: 1 column
    for title, sym, w in symbols:
        chart_block(title, sym, w)
else:
    # Desktop: 3 columns grid (2 rows)
    row1 = symbols[:3]
    row2 = symbols[3:]

    c1, c2, c3 = st.columns(3)
    with c1: chart_block(*row1[0])
    with c2: chart_block(*row1[1])
    with c3: chart_block(*row1[2])

    c4, c5, c6 = st.columns(3)
    with c4: chart_block(*row2[0])
    with c5: chart_block(*row2[1])
    with c6: chart_block(*row2[2])

st.divider()

# ---- Data loading ----
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
    files.sort(reverse=True)  # latest first
    return files

# ---- Report mode ----
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

left, right = st.columns([1.35, 0.65], gap="large") if not is_mobile else (st.container(), st.container())

# ---- AI report ----
with left:
    st.subheader("🧠 AI 快報")
    st.markdown(data.get("report", ""))

# ---- News list ----
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
            if n.get("dt_utc"):
                st.caption(f"時間（UTC）：{n.get('dt_utc')}")
            if n.get("link"):
                st.markdown(f"[閱讀原文]({n.get('link')})")
            with st.expander("摘要"):
                st.write(n.get("summary", ""))
