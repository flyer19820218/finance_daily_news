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
HISTORY_DIR = "data/history"


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
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_list, f, ensure_ascii=False, indent=2)


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


def fetch_market_snapshot():
    """
    用 Yahoo quote JSON API 抓快照（在 GitHub Actions 通常比 Streamlit Cloud 穩）
    """
    tickers = {
        "台指期": "TX=F",
        "納指期": "NQ=F",
        "費半": "^SOX",
        "道瓊": "^DJI",
        "TSM": "TSM",
        "NVDA": "NVDA",
    }

    snapshot = {}
    url = "https://query1.finance.yahoo.com/v7/finance/quote"

    for name, ticker in tickers.items():
        try:
            r = requests.get(url, params={"symbols": ticker}, timeout=15)
            data = r.json()
            result = data.get("quoteResponse", {}).get("result", [])
            if not result:
                snapshot[name] = {"ticker": ticker, "ok": False}
                continue

            q = result[0]
            snapshot[name] = {
                "ticker": ticker,
                "ok": True,
                "price": q.get("regularMarketPrice"),
                "change": q.get("regularMarketChange"),
                "pct": q.get("regularMarketChangePercent"),
                "time": q.get("regularMarketTime"),
            }
        except Exception:
            snapshot[name] = {"ticker": ticker, "ok": False}

    return snapshot


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
        return "⚠️ 未設定 GEMINI_API_KEY（請到 GitHub Secrets 設定）"

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    r = model.generate_content(prompt)

    return r.text if hasattr(r, "text") else "AI分析失敗"


def write_json(path: str, payload: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def run_daily():
    news = fetch_news(hours=24, limit=20)
    report_text = ai_analyze(news)
    market = fetch_market_snapshot()

    now_utc = datetime.now(timezone.utc)
    payload = {
        "updated_at_utc": now_utc.isoformat(),
        "title": f"財經AI快報 {now_utc.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')}",
        "report": report_text,
        "news": news,
        "market": market,
    }

    # latest
    write_json(OUT_FILE, payload)

    # history（每天一份）
    os.makedirs(HISTORY_DIR, exist_ok=True)
    history_name = now_utc.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d") + ".json"
    write_json(os.path.join(HISTORY_DIR, history_name), payload)


if __name__ == "__main__":
    run_daily()
