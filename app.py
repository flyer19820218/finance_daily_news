import json
import os
from datetime import datetime, timezone

import streamlit as st
import streamlit.components.v1 as components

LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
      .muted { color: rgba(0,0,0,0.55); font-size: 0.9rem; }
      .tv-wrap { border: 1px solid rgba(0,0,0,0.10); border-radius: 14px; padding: 10px 12px; }
      .tv-title { font-weight: 700; margin-bottom: 6px; }
      .tv-links a { font-size: 0.9rem; }
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

# -----------------------------
# TradingView embed helpers
# -----------------------------
def tv_mini(symbol: str, height: int = 260, interval: str = "D"):
    """TradingView Mini Symbol Overview (漂亮，但有些商品會受限制)"""
    html = f"""
    <div class="tv-wrap">
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

def chart_card(title: str, tv_symbol: str, wantgoo_url: str | None = None,
               fallback_title: str | None = None, fallback_symbol: str | None = None):
    """
    先嘗試顯示 tv_symbol。
    若 TradingView 這個商品不給嵌入（你之前遇到的情況），圖上會顯示提示字樣。
    我們無法在程式上「讀到」那個提示，因此做法是：一律附上 wantgoo 本尊連結 + 可用替代品。
    """
    st.markdown(f"**{title}**")
    link_html = ""
    if wantgoo_url:
        link_html += f'<div class="tv-links"><a href="{wantgoo_url}" target="_blank">🔗 WantGoo 本尊（點我開新分頁）</a></div>'
    if link_html:
        st.markdown(link_html, unsafe_allow_html=True)

    # 主要圖：用 try/except 確保不會整頁爆掉
    try:
        tv_mini(tv_symbol, height=260, interval="D")
    except Exception as e:
        st.warning(f"這個圖表載入失敗（不影響其他區塊）。原因：{e}")

    # 替代圖（ETF）— 當 TradingView 不給本尊時，你至少有圖可看
    if fallback_title and fallback_symbol:
        with st.expander("若本尊無法嵌入，改看替代追蹤標的（點開）", expanded=False):
            st.markdown(f"**{fallback_title}**")
            try:
                tv_mini(fallback_symbol, height=260, interval="D")
            except Exception as e:
                st.warning(f"替代圖也載入失敗：{e}")

# -----------------------------
# TOP 6 charts (revert mode)
# -----------------------------
st.subheader("🌍 全球重要股市 / 期貨 / 個股走勢（嵌入模式）")

# 你提供的 wantgoo 連結（本尊）
WG_TXF = "https://www.wantgoo.com/futures/wtxm"
WG_NQ  = "https://www.wantgoo.com/global/m1nq"
WG_SOX = "https://www.wantgoo.com/global/sox"
WG_DJI = "https://www.wantgoo.com/global/dji"

# TradingView 端「本尊」代號（可能被限制嵌入）
# 台指期：你之前用 TVC:TW1! 會被擋 => 這裡仍先放，並提供替代 0050
# 納指期：NQ1! 常被擋 => 先放 CME_MINI:NQ1!，替代 QQQ
# 費半：SOX 有時被擋 => 先放 NASDAQ:SOX，替代 SOXX
# 道瓊：DJI / YM1! 可能被擋 => 先放 DJ:DJI，替代 DIA
cards = [
    # title, tv_symbol, wantgoo_url, fallback_title, fallback_symbol
    ("台指期（近月）", "TVC:TW1!", WG_TXF, "台股大盤替代：0050", "TPEX:0050"),
    ("費半（SOX）", "NASDAQ:SOX", WG_SOX, "費半替代：SOXX（ETF）", "AMEX:SOXX"),
    ("道瓊（DJI）", "DJ:DJI", WG_DJI, "道瓊替代：DIA（ETF）", "AMEX:DIA"),
    ("納指期（NQ）", "CME_MINI:NQ1!", WG_NQ, "納指替代：QQQ（ETF）", "NASDAQ:QQQ"),
    ("台積電 ADR（TSM）", "NYSE:TSM", None, None, None),
    ("NVIDIA（NVDA）", "NASDAQ:NVDA", None, None, None),
]

if is_mobile:
    for c in cards:
        chart_card(*c)
else:
    r1, r2 = cards[:3], cards[3:]
    c1, c2, c3 = st.columns(3)
    with c1: chart_card(*r1[0])
    with c2: chart_card(*r1[1])
    with c3: chart_card(*r1[2])

    c4, c5, c6 = st.columns(3)
    with c4: chart_card(*r2[0])
    with c5: chart_card(*r2[1])
    with c6: chart_card(*r2[2])

st.divider()

# -----------------------------
# Report section (latest/history)
# -----------------------------
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
        news = [n for n in news if ql in (n.get("title","") + " " + n.get("summary","")).lower()]

    st.write(f"共 {len(news)} 則")
    for n in news:
        with st.container(border=True):
            st.markdown(f"**{n.get('title','')}**")
            if n.get("link"):
                st.markdown(f"[閱讀原文]({n.get('link')})")
            with st.expander("摘要"):
                st.write(n.get("summary",""))
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
            news = [n for n in news if ql in (n.get("title","") + " " + n.get("summary","")).lower()]

        st.write(f"共 {len(news)} 則")
        for n in news:
            with st.container(border=True):
                st.markdown(f"**{n.get('title','')}**")
                if n.get("link"):
                    st.markdown(f"[閱讀原文]({n.get('link')})")
                with st.expander("摘要"):
                    st.write(n.get("summary",""))
