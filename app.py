import json
import os
import math
import requests
from urllib.parse import urlparse

import streamlit as st
import yfinance as yf

LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

st.markdown(
    """
<style>
:root{
  --bg:#ffffff;
  --panel:#f7f9fc;
  --border:#e7ebf3;
  --text:#0f172a;
  --muted:#64748b;
  --muted2:#94a3b8;
  --up:#16a34a;
  --down:#ef4444;
  --link:#2563eb;
  --pill:#eef2ff;
  --shadow: 0 10px 30px rgba(2,6,23,0.06);
  --shadow2: 0 8px 22px rgba(2,6,23,0.05);
}

.stApp{
  background:var(--bg);
  color:var(--text);
  font-family:
    "翩翩體",
    "PianPian",
    "PingFang TC",
    "PingFang SC",
    "Noto Sans TC",
    "Noto Sans CJK TC",
    "Microsoft JhengHei",
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;
}

html, body, [class*="css"]{
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

a{ color:var(--link) !important; text-decoration:none; }
a:hover{ text-decoration:underline; }

.block-container{
  padding-top: 1.2rem;
  padding-bottom: 2.2rem;
  max-width: 1180px;
}

.header{
  display:flex;
  justify-content:space-between;
  align-items:flex-end;
  gap:14px;
  padding: 6px 0 12px 0;
}

.brand{
  font-size: 34px;
  font-weight: 900;
  letter-spacing: -0.4px;
  line-height: 1.15;
  word-break: keep-all;
  overflow-wrap: normal;
  white-space: normal;
  max-width: 100%;
}

.sub{
  color:var(--muted);
  font-size: 13px;
  margin-top: 6px;
}

.badge{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding: 8px 12px;
  border:1px solid var(--border);
  border-radius: 999px;
  background: #fff;
  color: var(--muted);
  font-size: 12px;
  white-space: nowrap;
  box-shadow: 0 6px 18px rgba(2,6,23,0.06);
}

.hr{ height:1px; background:var(--border); margin: 18px 0; }

.section-title{
  font-size: 15px;
  font-weight: 850;
  letter-spacing: -0.1px;
  margin: 10px 0 10px 0;
}

.cards{
  border:1px solid var(--border);
  background: var(--panel);
  border-radius: 18px;
  padding: 14px;
  box-shadow: var(--shadow);
}
.tile{
  background:#fff;
  border:1px solid var(--border);
  border-radius: 16px;
  padding: 12px 12px;
  height: 100%;
  box-shadow: var(--shadow2);
  transition: transform .12s ease, box-shadow .12s ease;
}
.tile:hover{
  transform: translateY(-1px);
  box-shadow: 0 12px 28px rgba(2,6,23,0.08);
}
.name{ color:var(--muted); font-size: 12px; margin-bottom: 2px; }
.price{
  font-size: 22px;
  font-weight: 950;
  margin: 2px 0 6px 0;
  letter-spacing: -0.2px;
}
.delta{ font-size: 13px; font-weight: 800; }
.up{ color:var(--up); }
.down{ color:var(--down); }
.flat{ color:var(--muted2); }

.panel{
  border:1px solid var(--border);
  background: #fff;
  border-radius: 18px;
  padding: 16px 16px;
  box-shadow: var(--shadow);
}

.news-card{
  border:1px solid var(--border);
  background:#fff;
  border-radius: 16px;
  padding: 10px 12px;
  margin-bottom: 10px;
  box-shadow: var(--shadow2);
  transition: transform .12s ease, box-shadow .12s ease;
}
.news-card:hover{
  transform: translateY(-1px);
  box-shadow: 0 12px 28px rgba(2,6,23,0.08);
}
.small{ color:var(--muted); font-size: 12px; }
.inline-row{
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.35;
  word-break: break-word;
}
.pagerline{
  display:flex;
  align-items:center;
  justify-content:space-between;
  margin: 6px 0 10px 0;
}

@media (max-width: 768px){
  .block-container{ padding-left: 0.9rem; padding-right: 0.9rem; }
  .header{
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  .brand{
    font-size: 28px;
    letter-spacing: -0.2px;
  }
  .sub{ font-size: 12px; }
  .badge{
    font-size: 11px;
    padding: 7px 10px;
    white-space: normal;
  }
  .section-title{ font-size: 14px; }
  .price{ font-size: 20px; }
  .delta{ font-size: 12px; }
  .inline-row{ font-size: 12px; }
}
</style>
""",
    unsafe_allow_html=True,
)

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


# ==========================
# ✅ 6 個指數設定（富果 + Yahoo）
# ==========================
SYMBOLS = [
    ("台指期（全）", ["TX00"]),  # 使用富果 API (TX00 為台指期近月代碼)
    ("費半（SOX）", ["^SOX"]),
    ("道瓊期（YM）", ["YM=F"]),
    ("納指期（NQ）", ["NQ=F"]),
    ("台積電 ADR（TSM）", ["TSM"]),
    ("NVIDIA（NVDA）", ["NVDA"]),
]

def _safe_float(x):
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None

# ==========================
# ✅ 富果 API 專用抓取函數
# ==========================
@st.cache_data(ttl=60)
def fugle_quote_tx(symbol):
    api_key = os.environ.get("FUGLE_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets["FUGLE_API_KEY"]
        except:
            pass
            
    if not api_key:
        return {"ok": False, "ticker": symbol, "price": None, "change": None, "pct": None}

    url = f"https://openapi.fugle.tw/marketdata/v1.0/stock/intraday/quote/{symbol}"
    headers = {"X-API-KEY": api_key}
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            last = data.get("lastPrice") or data.get("closePrice")
            prev = data.get("previousClose")
            
            if last is not None and prev is not None:
                ch = last - prev
                pct = (ch / prev) * 100 if prev != 0 else 0
                return {
                    "ok": True,
                    "ticker": symbol,
                    "price": float(last),
                    "prev_close": float(prev),
                    "change": float(ch),
                    "pct": float(pct),
                }
    except Exception:
        pass

    return {"ok": False, "ticker": symbol, "price": None, "change": None, "pct": None}

# ==========================
# ✅ YFinance 抓取函數
# ==========================
@st.cache_data(ttl=60)
def yf_quote_any(tickers):
    for tk in tickers:
        try:
            t = yf.Ticker(tk)
            fi = getattr(t, "fast_info", None)

            last = None
            prev = None
            if fi:
                last = _safe_float(fi.get("last_price") or fi.get("lastPrice"))
                prev = _safe_float(fi.get("previous_close") or fi.get("previousClose"))

            if last is None:
                hist = t.history(period="2d", interval="1d")
                if hist is not None and len(hist) >= 1:
                    last = _safe_float(hist["Close"].iloc[-1])
                    if len(hist) >= 2:
                        prev = _safe_float(hist["Close"].iloc[-2])

            if last is not None:
                ch = (last - prev) if prev is not None else None
                pct = (ch / prev * 100) if (ch is not None and prev not in (None, 0)) else None
                return {
                    "ok": True,
                    "ticker": tk,
                    "price": last,
                    "prev_close": prev,
                    "change": ch,
                    "pct": pct,
                }
        except Exception:
            continue

    return {"ok": False, "ticker": tickers[0] if tickers else "", "price": None, "prev_close": None, "change": None, "pct": None}


def render_tile(name, q):
    render_ok = q and q.get("ok") and q.get("price") is not None
    if not render_ok:
        return f"""
        <div class="tile">
          <div class="name">{name}</div>
          <div class="price">-</div>
          <div class="delta flat">-</div>
        </div>
        """

    ch = q.get("change")
    pct = q.get("pct")
    price = q.get("price")

    ch = float(ch) if ch is not None else 0.0
    pct = float(pct) if pct is not None else 0.0
    price = float(price)

    cls = "up" if ch > 0 else "down" if ch < 0 else "flat"
    arrow = "▲" if ch > 0 else "▼" if ch < 0 else "—"

    return f"""
    <div class="tile">
      <div class="name">{name}</div>
      <div class="price">{round(price, 2)}</div>
      <div class="delta {cls}">{arrow} {round(ch, 2)}（{round(pct, 2)}%）</div>
    </div>
    """


mode = st.radio("檢視模式", ["最新（今日）", "歷史回顧"], horizontal=True)

data = None
if mode == "最新（今日）":
    data = load_json(LATEST_FILE)
else:
    hist = list_history()
    if not hist:
        st.warning("尚無歷史資料，請先讓排程成功跑一次。")
        st.stop()
    pick = st.selectbox("選擇日期", hist, index=0)
    data = load_json(os.path.join(HISTORY_DIR, pick))

if not data:
    st.warning("尚未產生報告（請先手動執行一次排程）。")
    st.stop()

updated = data.get("updated_at_utc", "")

st.markdown(
    f"""
<div class="header">
  <div>
    <div class="brand">財經AI快報</div>
    <div class="sub">每日市場重點整理（重大事件｜台股影響｜投資觀察）</div>
  </div>
  <div class="badge">最後更新（UTC）：{updated}</div>
</div>
""",
    unsafe_allow_html=True,
)

# =======================
# ✅ 市場快照：分配不同 API
# =======================
st.markdown('<div class="section-title">全球市場快照</div>', unsafe_allow_html=True)

market = data.get("market", {}) or {}

filled = {}
for name, tickers in SYMBOLS:
    # 判斷 JSON 是否已有完整數據
    if name in market and market[name].get("price") is not None:
        filled[name] = market[name]
    else:
        # 分流抓取：台指期給富果，其他給 Yahoo
        if name == "台指期（全）":
            filled[name] = fugle_quote_tx(tickers[0])
        else:
            filled[name] = yf_quote_any(tuple(tickers))

st.markdown('<div class="cards">', unsafe_allow_html=True)

# ✅ 桌機預設：一排6個
is_mobile = st.toggle("手機版排版（兩欄）", value=False)

if is_mobile:
    col1, col2 = st.columns(2)
    for i, (name, _) in enumerate(SYMBOLS):
        html = render_tile(name, filled.get(name))
        with (col1 if i % 2 == 0 else col2):
            st.markdown(html, unsafe_allow_html=True)
else:
    cols = st.columns(6)
    for i, (name, _) in enumerate(SYMBOLS):
        html = render_tile(name, filled.get(name))
        with cols[i]:
            st.markdown(html, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

left, right = st.columns([1.35, 0.65], gap="large")

with left:
    st.markdown('<div class="section-title">AI 分析摘要</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(data.get("report", ""))
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-title">新聞清單</div>', unsafe_allow_html=True)
    news = data.get("news", []) or []

    page_size = 10
    total = len(news)
    total_pages = max(1, math.ceil(total / page_size))

    if "news_page" not in st.session_state:
        st.session_state.news_page = 1
    st.session_state.news_page = max(1, min(st.session_state.news_page, total_pages))

    st.markdown(
        f"<div class='pagerline'><div class='small'>第 {st.session_state.news_page} / {total_pages} 頁（共 {total} 則）</div></div>",
        unsafe_allow_html=True,
    )

    if total_pages <= 2:
        try:
            sel = st.segmented_control(
                "分頁",
                options=[1, 2],
                format_func=lambda x: f"第 {x} 頁",
                selection_mode="single",
                default=st.session_state.news_page,
                label_visibility="collapsed",
            )
        except Exception:
            sel = st.radio(
                "分頁",
                options=[1, 2],
                format_func=lambda x: f"第 {x} 頁",
                horizontal=True,
                index=st.session_state.news_page - 1,
                label_visibility="collapsed",
            )
        if sel and sel != st.session_state.news_page:
            st.session_state.news_page = int(sel)
            st.rerun()
    else:
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("← 上一頁", use_container_width=True, disabled=(st.session_state.news_page <= 1)):
                st.session_state.news_page -= 1
                st.rerun()
        with c2:
            if st.button("下一頁 →", use_container_width=True, disabled=(st.session_state.news_page >= total_pages)):
                st.session_state.news_page += 1
                st.rerun()

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

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

        st.markdown('<div class="news-card">', unsafe_allow_html=True)
        st.markdown(f"**{title}**")

        parts = []
        if source:
            parts.append(f"<span>{source}</span>")
        if link:
            parts.append(f"<a href='{link}' target='_blank'>閱讀原文</a>")

        if parts:
            row = " &nbsp;&nbsp;|&nbsp;&nbsp; ".join(parts)
            st.markdown(f"<div class='inline-row'>{row}</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
