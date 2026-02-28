import os
import re
import json
import calendar
from datetime import datetime, timedelta, timezone

import feedparser
import requests
import yfinance as yf
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

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        # 沒 key 也不要壞：讓網站能顯示市場快照/新聞
        return "（本機測試模式：未設定 GEMINI_API_KEY，因此略過 AI 分析）"

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    r = model.generate_content(prompt)

    return r.text if hasattr(r, "text") else "AI分析失敗"


def escape_md_v2(text: str) -> str:
    chars = r"\_*[]()~`>#+-=|{}.!"
    for c in chars:
        text = text.replace(c, "\\" + c)
    return text


def send_telegram(msg: str):
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return  # 本機可不送

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": escape_md_v2(msg),
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
    }
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()


def _safe_float(x):
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def yf_quote_any(tickers):
    """
    依序嘗試多個 ticker，成功就回傳 (ticker_used, price, prev_close)
    """
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
                return tk, last, prev
        except Exception:
            continue

    return None, None, None


def build_market_snapshot():
    """
    回傳給 app 用的 market dict：
    key 一律是固定中文名稱（避免順序亂）
    value 格式：{ok, ticker, price, prev_close, change, pct, asof_utc}
    """

    # ✅ 富台指：yfinance 可能會抽風，所以做多代碼 fallback
    # 你堅持「富台指」：先試 FTX=F，再試 FTX1!
    # 都失敗才退回 ^TWII（台股加權指數）當救命（可自行刪掉）
    ftx_try = ["FTX=F", "FTX1!", "^TWII"]

    mapping = [
        ("富台指（FTX）", ftx_try),
        ("費半（SOX）", ["^SOX"]),
        ("道瓊期（YM）", ["YM=F"]),
        ("納指期（NQ）", ["NQ=F"]),
        ("台積電 ADR（TSM）", ["TSM"]),
        ("NVIDIA（NVDA）", ["NVDA"]),
    ]

    market = {}
    now = datetime.now(timezone.utc).isoformat()

    for name, tickers in mapping:
        used, price, prev = yf_quote_any(tickers)

        if price is None:
            market[name] = {
                "ok": False,
                "ticker": used or (tickers[0] if tickers else ""),
                "price": None,
                "prev_close": None,
                "change": None,
                "pct": None,
                "asof_utc": now,
            }
            continue

        ch = (price - prev) if (prev is not None) else None
        pct = (ch / prev * 100) if (ch is not None and prev not in (None, 0)) else None

        market[name] = {
            "ok": True,
            "ticker": used or (tickers[0] if tickers else ""),
            "price": price,
            "prev_close": prev,
            "change": ch,
            "pct": pct,
            "asof_utc": now,
        }

    return market


def run_daily():
    news = fetch_news()
    report_text = ai_analyze(news)
    market = build_market_snapshot()

    payload = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "title": f"財經AI快報 {datetime.now().strftime('%Y-%m-%d')}",
        "report": report_text,
        "news": news,
        "market": market,
    }

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    os.makedirs(HISTORY_DIR, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    history_path = os.path.join(HISTORY_DIR, f"{date_str}.json")
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    send_telegram(report_text)


if __name__ == "__main__":
    run_daily()
