import json
import os
import streamlit as st

LATEST_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

st.set_page_config(page_title="Market Briefing", page_icon="📊", layout="wide")

# =============================
# Enterprise UI (V2)
# =============================
st.markdown(
    """
<style>
:root{
  --bg:#0b0f17;
  --panel:#111827;
  --panel2:#0f172a;
  --border:#263042;
  --text:#e5e7eb;
  --muted:#9aa4b2;
  --up:#00ff87;
  --down:#ff4d4f;
  --flat:#a3a9b5;
  --link:#60a5fa;
}

.stApp { background: var(--bg); color: var(--text); }
a { color: var(--link) !important; }

.block-container{ padding-top: 1.2rem; padding-bottom: 2rem; }

.header{
  display:flex;
  align-items:flex-end;
  justify-content:space-between;
  gap:12px;
  padding: 2px 0 10px 0;
}
.brand{
  font-size: 38px;
  font-weight: 800;
  letter-spacing: 0.5px;
}
.sub{
  color: var(--muted);
  font-size: 13px;
  margin-top: 6px;
}

.pill{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding: 8px 10px;
  border:1px solid var(--border);
  border-radius: 999px;
  background: rgba(17,24,39,0.7);
  color: var(--muted);
  font-size: 12px;
  white-space: nowrap;
}

.hr{ height:1px; background: var(--border); margin: 18px 0; }

.ticker{
  border:1px solid var(--border);
  background: linear-gradient(180deg, rgba(17,24,39,0.90), rgba(15,23,42,0.90));
  border-radius: 16px;
  padding: 14px 14px;
}

.tile{
  text-align:left;
  padding: 10px 10px;
  border-radius: 14px;
  background: rgba(15,23,42,0.55);
  border:1px solid rgba(38,48,66,0.65);
  height: 100%;
}

.name{
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.4px;
  margin-bottom: 2px;
}
.price{
  font-size: 22px;
  font-weight: 800;
  margin: 2px 0 4px 0;
}
.delta{
  font-size: 13px;
  font-weight: 700;
}
.up{ color: var(--up); }
.down{ color: var(--down); }
.flat{ color: var(--flat); }

.section-title{
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 0.25px;
  margin: 10px 0 8px 0;
}

.panel{
  border:1px solid var(--border);
  background: rgba(17,24,39,0.65);
  border-radius: 16px;
  padding: 14px 14px;
}

.news-card{
  border:1px solid rgba(38,48,66,0.75);
  background: rgba(15,23,42,0.55);
  border-radius: 14px;
  padding: 12px 12px;
  margin-bottom: 10px;
}

.small{
  color: var(--muted);
  font-size: 12px;
}
</style>
""",
    unsafe_allow_html=True,
)

# =============================
# Data loading
# =============================
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


mode = st.radio("View", ["Latest", "History"], horizontal=True)

data = None
label = "Latest"
if mode == "Latest":
    data = load_json(LATEST_FILE)
else:
    hist = list_history()
    if not hist:
        st.warning("No history yet. Run workflow once to generate the first report.")
        st.stop()
    pick = st.selectbox("Date", hist, index=0)
    data = load_json(os.path.join(HISTORY_DIR, pick))
    label = pick.replace(".json", "")

if not data:
    st.warning("Report not found yet. Please run the scheduled job once.")
    st.stop()

updated = data.get("updated_at_utc", "")

# =============================
# Header
# =============================
st.markdown(
    f"""
<div class="header">
  <div>
    <div class="brand">Market Briefing</div>
    <div class="sub">Daily macro + equities highlights</div>
  </div>
  <div class="pill">Last updated (UTC): {updated}</div>
</div>
""",
    unsafe_allow_html=True,
)

# =============================
# Market snapshot
# =============================
st.markdown('<div class="section-title">Market snapshot</div>', unsafe_allow_html=True)

market = data.get("market", {})

if market:
    st.markdown('<div class="ticker">', unsafe_allow_html=True)

    cols = st.columns(len(market))
    for col, (name, q) in zip(cols, market.items()):
        with col:
            if not q or not q.get("ok") or q.get("price") is None:
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
                      <div class="delta {cls}">{arrow} {round(float(ch), 2)} ({round(float(pct), 2)}%)</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Market snapshot is empty.")

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# =============================
# Content: Analysis + News
# =============================
left, right = st.columns([1.35, 0.65], gap="large")

with left:
    st.markdown('<div class="section-title">AI Summary</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(data.get("report", ""))
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-title">Top news</div>', unsafe_allow_html=True)

    news = data.get("news", [])
    st.markdown(f'<div class="small">Items: {len(news)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    for n in news:
        title = n.get("title", "")
        link = n.get("link", "")
        summary = n.get("summary", "")

        st.markdown('<div class="news-card">', unsafe_allow_html=True)
        st.markdown(f"**{title}**")
        if link:
            st.markdown(f"[Open source]({link})")
        if summary:
            with st.expander("Summary"):
                st.write(summary)
        st.markdown("</div>", unsafe_allow_html=True)
