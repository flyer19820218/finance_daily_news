import os
import re
import json
import calendar
import requests
from datetime import datetime, timedelta, timezone

import feedparser
import google.generativeai as genai

RSS_LIST = [
    "https://news.google.com/rss/search?q=finance+OR+stock&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    "https://news.google.com/rss/search?q=台股+OR+美股&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
]

CACHE_FILE = "data/news_cache.json"
OUT_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"

# 🌟 設定台灣時區 (UTC+8)
TW_TZ = timezone(timedelta(hours=8))

def clean_html(text: str) -> str:
    return re.sub(r"<.*?>", "", text or "")

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def save_cache(cache_list):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    # 限制 Cache 大小，避免檔案無限膨脹 (只保留最近 200 筆)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_list[-200:], f, ensure_ascii=False, indent=2)

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
        return "📰 今日目前無更新之重大財經事件。"

    text = "\n".join([f"{n['title']} | {n['summary']}" for n in news])

    prompt = f"""
你是總體經濟分析師與台股策略研究員。
請對以下新聞做：
1) 重要性排序（列出 3-6 則最重要）
2) 市場情緒（偏風險偏好/風險趨避/中性 + 原因）
3) 台股影響（利多/中性/利空；若可能點名產業）
4) 投資觀察（3-5 點可操作觀察，避免保證獲利語氣，避免過度看多或看空）

新聞：
{text}

輸出格式：
🌟財經AI快報 {datetime.now(TW_TZ).strftime("%Y-%m-%d")}

📊重大事件
🔥市場情緒
💰台股影響
📈投資觀察
"""

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return "（本機測試模式：未設定 GEMINI_API_KEY，因此略過 AI 分析）"

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    try:
        r = model.generate_content(prompt)
        return r.text
    except Exception as e:
        # 🌟 防呆：避免 Gemini 安全過濾導致整個程式崩潰
        return f"AI分析生成失敗 (可能觸發安全過濾)，錯誤訊息：{e}"

def escape_md_v2(text: str) -> str:
    chars = r"\_*[]()~`>#+-=|{}.!"
    for c in chars:
        text = text.replace(c, "\\" + c)
    return text

def send_telegram(msg: str):
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": escape_md_v2(msg),
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
    }
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()

def run_daily():
    news = fetch_news()
    
    # 🌟 防呆：如果今天第二次執行，抓不到新新聞，就讀取舊資料，不要用空檔案覆蓋網頁！
    if not news and os.path.exists(OUT_FILE):
        print("沒有抓到新新聞，保留今日舊有報告不覆蓋。")
        return

    report_text = ai_analyze(news)

    # 統一使用台灣時間 (TW_TZ)
    now_tw = datetime.now(TW_TZ)

    payload = {
        "updated_at_utc": now_tw.strftime("%Y-%m-%d %H:%M:%S (TW)"),
        "title": f"財經AI快報 {now_tw.strftime('%Y-%m-%d')}",
        "report": report_text,
        "news": news,
        "market": {}, 
    }

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    os.makedirs(HISTORY_DIR, exist_ok=True)
    date_str = now_tw.strftime("%Y-%m-%d") # 🌟 保證存出來的檔名是正確的台灣日期
    history_path = os.path.join(HISTORY_DIR, f"{date_str}.json")
    
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    send_telegram(report_text)

if __name__ == "__main__":
    run_daily()
