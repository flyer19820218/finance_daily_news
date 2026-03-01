st.markdown('<div class="section-title">全球市場快照</div>', unsafe_allow_html=True)

# ==========================
# ✅ 數據抓取更新：將富台指換成 MSCI 台灣 (EWT) 以確保有漲跌 %
# ==========================
@st.cache_data(ttl=60)
def fetch_msci_taiwan():
    """使用 EWT 作為 MSCI 台灣代理，確保 100% 抓到正負幾 % 的漲跌幅"""
    try:
        t = yf.Ticker("EWT")
        info = t.fast_info
        last = info.last_price
        prev = info.previous_close
        if last and prev:
            diff = last - prev
            pct = (diff / prev) * 100
            return {"ok": True, "price": last, "change": diff, "pct": pct}
    except: pass
    return {"ok": False}

# 抓取數據
filled = {}
filled["MSCI 台灣（EWT）"] = fetch_msci_taiwan()
for name, tickers in SYMBOLS_OTHERS:
    filled[name] = yf_quote_any(tuple(tickers))

# ==========================
# ✅ 2x3 強力排版：不使用 st.columns，直接用純 HTML Grid 解決手機一整排問題
# ==========================
DISPLAY_ORDER_NEW = [("MSCI 台灣（EWT）", None)] + SYMBOLS_OTHERS

# 這裡我們用一段自定義 CSS 來強制 Grid 佈局
st.markdown("""
<style>
.custom-market-grid {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(6, 1fr); /* 電腦版預設 6 欄 */
    background: #f7f9fc;
    border: 1px solid #e7ebf3;
    border-radius: 18px;
    padding: 16px;
    margin-bottom: 20px;
}
@media (max-width: 768px) {
    .custom-market-grid {
        grid-template-columns: repeat(2, 1fr) !important; /* 手機版強制 2 欄，達成 2x3 */
    }
}
</style>
""", unsafe_allow_html=True)

# 渲染 HTML 網格
grid_html = '<div class="custom-market-grid">'
for name, _ in DISPLAY_ORDER_NEW:
    grid_html += render_tile(name, filled.get(name))
grid_html += '</div>'

st.markdown(grid_html, unsafe_allow_html=True)
