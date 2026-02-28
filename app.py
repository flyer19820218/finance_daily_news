import json
import os
import math
from urllib.parse import urlparse

import streamlit as st

LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

# =============================
# 企業白底 UI
# =============================
st.markdown(
    """
<style>
:root{
  --bg:#ffffff;
  --panel:#f6f8fa;
  --border:#e5e7eb;
  --text:#111827;
  --muted:#6b7280;
  --up:#0a7d38;
  --down:#c1121f;
  --link:#2563eb;
}
.stApp{ background:var(--bg); color:var(--text); }
a{ color:var(--link) !important; text-decoration: none; }
a:hover{ text-decoration: underline; }
.block-container{ padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1200px; }
.header{
  display:flex;
  justify-content:space-between;
  align-items:flex-end;
  gap:12px;
  padding: 4px 0 12px 0;
}
.brand{
  font-size: 34px;
  font-weight: 800;
  letter-spacing: .2px;
}
.sub{
  color:var(--muted);
  font-size: 13px;
  margin-top: 6px;
}
.badge{
  display:inline-flex;
  align-items:center;
  padding: 8px 10px;
  border:1px solid var(--border);
  border-radius: 999px;
  background: #fff;
  color: var(--muted);
  font-size: 12px;
  white-space: nowrap;
}
.hr{ height:1px; background:var(--border); margin: 18px 0; }

.cards{
  border:1px solid var(--border);
  background: var(--panel);
  border-radius: 16px;
  padding: 14px;
}
.tile{
  background:#fff;
  border:1px solid var(--border);
  border-radius: 14px;
  padding: 12px 12px;
  height: 100%;
}
.name{ color:var(--muted); font-size: 12px; margin-bottom: 2px; }
.price{ font-size: 22px; font-weight: 800; margin: 2px 0 6px 0; }
.delta{ font-size: 13px; font-weight: 700; }
.up{ color:var(--up); }
.down{ color:var(--down); }
.flat{ color:var(--muted); }

.section-title{
  font-size: 16px;
  font-weight: 800;
  margin: 10px 0 8px 0;
}
.panel{
  border:1px solid var(--border);
  background: #fff;
  border-radius: 16px;
  padding: 14px;
}
.news-card{
  border:1px solid var(--border);
  background:#fff;
  border-radius: 14px;
  padding: 10px 12px;
  margin-bottom: 10px;
}
.small{ color:var(--muted); font-size: 12px; }
.inline-row{
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.35;
  word-break: break-word;
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


# =============================
# 選擇：最新 / 歷史
# =============================
mode = st.radio("檢視模式", ["最新（今日）", "歷史回顧"], horizontal=True)

data = None
label = "今日"
if mode == "最新（今日）":
    data = load_json(LATEST_FILE)
else:
    hist = list_history()
    if not hist:
        st.warning("尚無歷史資料，請先讓排程成功跑一次。")
        st.stop()
    pick = st.selectbox("選擇日期", hist, index=0)
    data = load_json(os.path.join(HISTORY_DIR, pick))
    label = pick.replace(".json", "")

if not data:
    st.warning("尚未產生報告（請先手動執行一次排程）。")
    st.stop()

updated = data.get("updated_at_utc", "")

# =============================
# Header（中文）
# =============================
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

# =============================
# 市場快照
# =============================
st.markdown('<div class="section-title">全球市場快照</div>', unsafe_allow_html=True)

market = data.get("market", {})
if market:
    st.markdown('<div class="cards">', unsafe_allow_html=True)

    is_mobile = st.toggle("手機版排版（兩欄）", value=True)

    items = list(market.items())
    if is_mobile:
        col1, col2 = st.columns(2)
        for i, (name, q) in enumerate(items):
            with (col1 if i % 2 == 0 else col2):
                render_ok = q and q.get("ok") and q.get("price") is not None
                if not render_ok:
                    st.markdown(
                        f"""
                        <div class="tile">
                          <div class="name">{name}</div>
                          <div class="price">-</div>
                          <div class="delta flat">-</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    ch = q.get("change") or 0
                    pct = q.get("pct") or 0
                    cls = "up" if ch > 0 else "down" if ch < 0 else "flat"
                    arrow = "▲" if ch > 0 else "▼" if ch < 0 else "—"
                    price = q.get("price")
                    st.markdown(
                        f"""
                        <div class="tile">
                          <div class="name">{name}</div>
                          <div class="price">{round(float(price), 2)}</div>
                          <div class="delta {cls}">{arrow} {round(float(ch), 2)}（{round(float(pct), 2)}%）</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
    else:
        cols = st.columns(len(items))
        for col, (name, q) in zip(cols, items):
            with col:
                render_ok = q and q.get("ok") and q.get("price") is not None
                if not render_ok:
                    st.markdown(
                        f"""
                        <div class="tile">
                          <div class="name">{name}</div>
                          <div class="price">-</div>
                          <div class="delta flat">-</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    ch = q.get("change") or 0
                    pct = q.get("pct") or 0
                    cls = "up" if ch > 0 else "down" if ch < 0 else "flat"
                    arrow = "▲" if ch > 0 else "▼" if ch < 0 else "—"
                    price = q.get("price")
                    st.markdown(
                        f"""
                        <div class="tile">
                          <div class="name">{name}</div>
                          <div class="price">{round(float(price), 2)}</div>
                          <div class="delta {cls}">{arrow} {round(float(ch), 2)}（{round(float(pct), 2)}%）</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("目前沒有市場快照資料。")

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# =============================
# AI 快報 + 新聞
# =============================
left, right = st.columns([1.35, 0.65], gap="large")

with left:
    st.markdown('<div class="section-title">AI 分析摘要</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(data.get("report", ""))
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-title">新聞清單</div>', unsafe_allow_html=True)
    news = data.get("news", []) or []

    # 每頁顯示 10 則
    page_size = 10
    total = len(news)
    total_pages = max(1, math.ceil(total / page_size))

    # 初始化頁碼
    if "news_page" not in st.session_state:
        st.session_state.news_page = 1  # 1-based

    st.session_state.news_page = max(1, min(st.session_state.news_page, total_pages))

    # 分頁按鈕
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if st.button("⬅ 上一頁", use_container_width=True, disabled=(st.session_state.news_page <= 1)):
            st.session_state.news_page -= 1
            st.rerun()
    with c2:
        if st.button("下一頁 ➡", use_container_width=True, disabled=(st.session_state.news_page >= total_pages)):
            st.session_state.news_page += 1
            st.rerun()
    with c3:
        st.markdown(
            f"<div class='small' style='text-align:right;'>第 {st.session_state.news_page} / {total_pages} 頁（共 {total} 則）</div>",
            unsafe_allow_html=True,
        )

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    # 取出當頁
    start = (st.session_state.news_page - 1) * page_size
    end = start + page_size
    page_items = news[start:end]

    # 列表：只顯示「標題 + 來源 + 閱讀原文」
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
