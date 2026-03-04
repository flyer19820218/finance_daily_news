import os
import re
import json
import calendar
import requests
from datetime import datetime, timedelta, timezone, time
import feedparser
import google.generativeai as genai

RSS_LIST = [
    "https://news.google.com/rss/search?q=finance+OR+stock&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    "https://news.google.com/rss/search?q=台股+OR+美股&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
]

CACHE_FILE = "data/news_cache.json"
OUT_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"
HOT_STOCKS_FILE = "hot_stocks.json"

TW_TZ = timezone(timedelta(hours=8))

def clean_html(text: str) -> str:
    return re.sub(r"<.*?>", "", text or "")

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except: return []
    return []

def save_cache(cache_list):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
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
            if not hasattr(e, "published_parsed"): continue
            unix = calendar.timegm(e.published_parsed)
            dt = datetime.fromtimestamp(unix, tz=timezone.utc)
            if dt < cutoff: continue
            link = getattr(e, "link", None)
            if not link or link in cache_set: continue
            news.append({
                "title": getattr(e, "title", "(no title)"),
                "link": link,
                "summary": clean_html(e.get("summary", ""))[:200],
                "dt_utc": dt.isoformat(),
            })
            cache_set.add(link)
            cache_list.append(link)
    save_cache(cache_list)
    news.sort(key=lambda x: x["dt_utc"], reverse=True)
    return news[:limit]

def update_hot_stocks():
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX20"
        res = requests.get(url, timeout=10)
        data = res.json()
        top_6 = {f"{item['Code']}.TW": item['Name'] for item in data[:6]}
        with open(HOT_STOCKS_FILE, "w", encoding="utf-8") as f:
            json.dump({"top_volume_pool": top_6}, f, ensure_ascii=False, indent=4)
    except: print("⚠️ 抓取爆量名單失敗，保留舊有名單。")

def ai_analyze(news, period_str):
    if not news: return f"📰 今日目前無更新之重大財經事件。({period_str})"
    text = "\n".join([f"{n['title']} | {n['summary']}" for n in news])
    
    # 🌟 邏輯大師精選：Gemini 智慧人格切換
    if "美股週收盤" in period_str:
        role = "你是頂級美股策略師。請總結本週美股表現與個股波動，並分析對下週一台灣相關供應鏈（如台積電ADR）的衝擊。"
    elif "下週展望" in period_str:
        role = "你是最強 AI 選股專家。請執行【Gemini 強勢選股任務】：從新聞中找出下週最可能噴發的 3-5 個產業板塊，點名具潛力個股，並提醒關鍵經濟數據。"
    elif "盤前" in period_str:
        role = "你是總體經濟分析師。現在是早晨盤前，請針對昨晚美股影響，提供今日台股觀盤重點。"
    else:
        role = "你是台股操盤手。現在是下午盤後，請分析今日盤勢動態並總結法人籌碼動向。"

    prompt = f"""
    {role}
    新聞素材：{text}
    輸出格式：
    🌟財經AI快報 {datetime.now(TW_TZ).strftime("%Y-%m-%d")} ({period_str})
    📊重大事件
    🔥市場情緒
    💰台股影響
    📈【下週強勢展望 & AI 精選股】(若非週日則顯示投資觀察)
    """
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
    model = genai.GenerativeModel("gemini-2.0-flash") # 確保使用最新模型
    try:
        return model.generate_content(prompt).text
    except Exception as e: return f"AI 分析失敗: {e}"

def run_daily():
    update_hot_stocks()
    news = fetch_news()
    now_tw = datetime.now(TW_TZ)
    weekday = now_tw.weekday() # 0=Mon, 5=Sat, 6=Sun
    
    # 🌟 自動判定人格標籤
    if weekday == 5: period_str = "週末特刊-美股週收盤"
    elif weekday == 6: period_str = "週末特刊-下週展望"
    else: period_str = "盤前" if now_tw.hour < 12 else "盤後"

    report_text = ai_analyze(news, period_str)
    payload = {
        "updated_at_utc": now_tw.strftime("%Y-%m-%d %H:%M:%S (TW)"),
        "title": f"財經AI快報 {now_tw.strftime('%Y-%m-%d')} {period_str}",
        "report": report_text,
        "news": news,
    }
    
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    
    os.makedirs(HISTORY_DIR, exist_ok=True)
    hist_name = f"{now_tw.strftime('%Y-%m-%d')}_{period_str}.json"
    with open(os.path.join(HISTORY_DIR, hist_name), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_daily()
