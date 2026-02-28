import os
import re
import json
import calendar
from datetime import datetime, timedelta, timezone

import feedparser
import requests
import google.generativeai as genai

RSS_LIST = [
    "https://news.google.com/rss/search?q=finance+OR+stock&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    "https://news.google.com/rss/search?q=台股+OR+美股&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
]

CACHE_FILE = "data/news_cache.json"
OUT_FILE = "data/latest_report.json"


# -------------------------------------------------
# 工具
# -------------------------------------------------
def clean_html(text: str) -> str:
    return re.sub(r"<.*?>", "", text or "")


def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except:
            return []
    return []


def save_cache(cache_list):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_list, f, ensure_ascii=False, indent=2)


# -------------------------------------------------
# 抓新聞
# -------------------------------------------------
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

            news.append(
                {
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "dt_utc": dt.isoformat(),
                }
            )

            cache_set.add(link)
            cache_list.append(link)

    save_cache(cache_list)
    news.sort(key=lambda x: x["dt_utc"], reverse=True)
    return news[:limit]


# -------------------------------------------------
# 抓市場快照（Yahoo 官方 JSON API）
# -------------------------------------------------
def fetch_market_snapshot():
    tickers = {
        "台指期": "TX=F",
        "納指期": "NQ=F",
        "費半": "^SOX",
        "道瓊": "^DJI",
        "TSM": "TSM",
        "NVDA": "NVDA",
    }

    snapshot = {}

    for name, ticker in tickers.items():
        try:
            url = "https://query1.finance.yahoo.com/v7/finance/quote"
            r = requests.get(url, params={"symbols": ticker}, timeout=10)
            data = r.json()

            result = data.get("quoteResponse", {}).get("result", [])
            if not result:
                continue

            q = result[0]

            snapshot[name] = {
                "price": q.get("regularMarketPrice"),
                "change": q.get("regularMarketChange"),
                "pct": q.get("regularMarketChangePercent"),
            }

        except:
            continue

    return snapshot


# -------------------------------------------------
# AI 分析
# -------------------------------------------------
def ai_analyze(news):
    if not news:
        return "📰 今日無新重大財經事件"

    text = "\n".join([f"{n['title']} | {n['summary']}" for n in news])

    prompt = f"""
你是總體經濟分析師與台股策略研究員。
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
        return "⚠️ 未設定 GEMINI_API_KEY"

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    r = model.generate_content(prompt)
    return r.text if hasattr(r, "text") else "AI分析失敗"


# -------------------------------------------------
# 主流程
# -------------------------------------------------
def run_daily():
    news = fetch_news()
    report_text = ai_analyze(news)
    market_snapshot = fetch_market_snapshot()

    payload = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "title": f"財經AI快報 {datetime.now().strftime('%Y-%m-%d')}",
        "report": report_text,
        "news": news,
        "market": market_snapshot,
    }

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    run_daily()
