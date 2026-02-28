import json
import os
import math
from urllib.parse import urlparse

import streamlit as st

LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

st.set_page_config(page_title="財經AI快報", page_icon="📈", layout="wide")

# =============================
# Tech Startup UI (白底新創感)
# =============================
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
  --pill:#f1f5ff;
  --shadow: 0 10px 30px rgba(2,6,23,0.06);
}

.stApp{ background:var(--bg); color:var(--text); }
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
  font-weight: 850;
  letter-spacing: -0.3px;
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
  font-weight: 800;
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
  box-shadow: 0 8px 24px rgba(2,6,23,0.05);
}

.name{
  color:var(--muted);
  font-size: 12px;
  margin-bottom: 2px;
}
.price{
  font-size: 22px;
  font-weight: 900;
  margin: 2px 0 6px 0;
  letter-spacing: -0.2px;
}
.delta{
  font-size: 13px;
  font-weight: 750;
}
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
  box-shadow: 0 8px 22px rgba(2,6,23,0.05);
}

.small{ color:var(--muted); font-size: 12px; }
.inline-row{
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.35;
  word-break: break-word;
}

/* Pagination: ← 1 2 3 → */
.pager{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:10px;
  margin: 6px 0 10px 0;
}
.pager-left{ color:var(--muted); font-size:12px; }

.pagebox{
  display:flex;
  align-items:center;
  gap:6px;
  flex-wrap:wrap;
  justify-content:flex-end;
}
.pagebtn{
  border:1px solid var(--border);
  background:#fff;
  padding:6px 10px;
  border-radius: 999px;
  font-size:12px;
  color:#0f172a;
}
.pagebtn:hover{ background: #f3f6ff; }

.pagebtn-active{
  border:1px solid rgba(37,99,235,0.35);
  background: var(--pill);
  color: #1d4ed8;
  font-weight: 800;
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

market = data.get("market", {}) or {}
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

    page_size = 10
    total = len(news)
    total_pages = max(1, math.ceil(total / page_size))

    if "news_page" not in st.session_state:
        st.session_state.news_page = 1
    st.session_state.news_page = max(1, min(st.session_state.news_page, total_pages))

    # ===== 分頁：← 1 2 3 →（數字頁碼）=====
    # 顯示的頁碼範圍（最多顯示 5 個）
    current = st.session_state.news_page
    window = 2
    start_page = max(1, current - window)
    end_page = min(total_pages, current + window)

    # 邊界補齊讓頁碼維持最多 5 個
    while (end_page - start_page + 1) < 5 and start_page > 1:
        start_page -= 1
    while (end_page - start_page + 1) < 5 and end_page < total_pages:
        end_page += 1

    st.markdown(
        f"""
<div class="pager">
  <div class="pager-left">第 {current} / {total_pages} 頁（共 {total} 則）</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # 用 Streamlit button 來做「← 1 2 3 →」
    cols = st.columns([1, 6, 1])
    with cols[0]:
        if st.button("←", use_container_width=True, disabled=(current <= 1)):
            st.session_state.news_page -= 1
            st.rerun()

    with cols[1]:
        # 中間區塊做成「一排數字」
        page_cols = st.columns(end_page - start_page + 1)
        for i, p in enumerate(range(start_page, end_page + 1)):
            with page_cols[i]:
                label = str(p)
                if p == current:
                    # active：用不同 key 並用 CSS 讓它更像 pill
                    st.markdown(
                        f"<div style='text-align:center;'><span class='pagebtn pagebtn-active'>{label}</span></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    if st.button(label, key=f"page_{p}", use_container_width=True):
                        st.session_state.news_page = p
                        st.rerun()

    with cols[2]:
        if st.button("→", use_container_width=True, disabled=(current >= total_pages)):
            st.session_state.news_page += 1
            st.rerun()

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
