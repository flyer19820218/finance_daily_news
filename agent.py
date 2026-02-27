import os
import re
import json
import calendar
from datetime import datetime, timedelta, timezone
import feedparser
import requests
import google.generativeai as genai

# ================= CONFIG =================
RSS_LIST = [
    "https://news.google.com/rss/search?q=finance+OR+stock&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    "https://news.google.com/rss/search?q=台股+OR+美股&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
]

CACHE_FILE = "data/news_cache.json"
OUT_FILE = "data/latest_report.json"

# ================= UTILS =================
def apply_streamlit_patch():
    """視覺規範補丁：解決 Apple iOS 設備反黑問題"""
    try:
        import streamlit as st
        st.markdown(
            """
            <style>
            html, body, [data-testid="stAppViewContainer"] {
                background-color: #FFFFFF !important;
                color: #000000 !important;
                font-family: 'HanziPen SC', sans-serif !important;
                color-scheme: light !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
    except ImportError:
        pass  # 於 GitHub Actions 純後端執行時自動略過

def clean_html(text: str) -> str:
    return re.sub(r"<.*?>", "", text or "")

def escape_md_v2(text: str) -> str:
    chars = r"\_*[]()~`>#+-=|{}.!"
    for c in chars:
        text = text.replace(c, "\\" + c)
    return text

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_cache(cache_list):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_list[-200:], f, ensure_ascii=False)

# ================= CORE LOGIC =================
def fetch_news(hours=24, limit=20):
    cache_list = load_cache()
    cache_set = set(cache_list)
    news = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    for rss in RSS_LIST:
        feed = feedparser.parse(rss)
        for e in feed.entries:
            if not hasattr(e, "published_parsed"):
                continue

            unix = calendar.timegm(e.published_parsed)
            dt = datetime.fromtimestamp(unix, tz=timezone.utc)
            if dt < cutoff:
                continue

            link = getattr(e, "link", None)
            if not link or link in cache_set:
                continue

            summary = clean_html(e.get("summary", ""))[:200]
            title = getattr(e, "title", "(no title)")

            news.append({
                "title": title,
                "link": link,
                "summary": summary,
                "dt_utc": dt.isoformat(),
            })
            cache_set.add(link)
            cache_list.append(link)

    save_cache(cache_list)
    news.sort(key=lambda x: x["dt_utc"], reverse=True)
    return news[:limit]

def ai_analyze(news):
    if not news:
        return "📰 今日無新重大財經事件"

    text = "\n".join([f"{n['title']} | {n['summary']}" for n in news])
    prompt = f"""你是總體經濟分析師與台股策略研究員。
請對以下新聞做：
1) 重要性排序（列出 3-6 則最重要）
2) 市場情緒（偏風險偏好/風險趨避/中性 + 原因）
3) 台股影響（利多/中性/利空；若可能點名產業）
4) 投資觀察（3-5 點可操作觀察，避免保證獲利語氣）

新聞：
{text}

輸出格式：
🌟財經AI快報 {datetime.now().strftime("%Y-%m-%d")}

📊重大事件
🔥市場情緒
💰台股影響
📈投資觀察
"""

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "❌ 錯誤：未設定 GEMINI_API_KEY 環境變數"

    genai.configure(api_key=api_key)
    # 鎖定 2.5 版本
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    try:
        # 設定 60 秒 timeout 防呆，避免 GitHub Actions 卡死
        r = model.generate_content(prompt, request_options={"timeout": 60})
        return r.text if r.text else "AI 分析回傳空值"
    except Exception as e:
        return f"❌ AI 處理失敗，遭遇 API 異常: {str(e)}"

def send_telegram(msg: str):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("⚠️ 警告：缺少 Telegram Token 或 Chat ID，略過發送。")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": escape_md_v2(msg),
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
    }
    r = requests.post(url, json=payload, timeout=20)
    if r.status_code != 200:
        print(f"Telegram API Error: {r.text}")

def run_daily():
    os.makedirs("data", exist_ok=True)
    news = fetch_news()
    report_text = ai_analyze(news)

    payload = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "title": f"財經AI快報 {datetime.now().strftime('%Y-%m-%d')}",
        "report": report_text,
        "news": news,
    }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    send_telegram(report_text)
    print("✅ 任務執行完畢。")

if __name__ == "__main__":
    apply_streamlit_patch()
    run_daily()
