import os
import re
import json
import calendar
import requests
from datetime import datetime, timedelta, timezone, time
import feedparser
import google.generativeai as genai

# === 基礎設定 ===
RSS_LIST = [
    "https://news.google.com/rss/search?q=finance+OR+stock+OR+geopolitics&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    "https://news.google.com/rss/search?q=股市+OR+地緣政治+OR+軍事+OR+傳聞&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
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

def fetch_news(hours=24, limit=30):
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
                "summary": clean_html(e.get("summary", ""))[:300],
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
    except Exception as e:
        print(f"⚠️ 抓取爆量名單失敗: {e}")

# === 🌟 核心 AI 大腦 (Gemini 2.5 Flash 定製) ===
def ai_analyze(news, period_str):
    if not news: 
        return f"📰 目前偵蒐範圍內無重大市場波動事件。({period_str})"
        
    text = "\n".join([f"{n['title']} | {n['summary']}" for n in news])
    
    strategy_prompt = """
    你現在是 2035 戰情室的首席情報官。
    任務：偵測全球地緣政治蝴蝶效應。
    
    【核心偵蒐邏輯】：
    1. 🛡️ **地緣政治 (Geopolitics)**：重點掃描全球軍事對抗、外交摩擦、政經變局。
    2. ⚠️ **市場心理警示**：納入未經證實的重大傳聞或突發言論，評估其對市場避險情緒的衝擊。
    3. 🌡️ **籌碼壓力測試**：分析全球恐慌情緒 (VIX) 與台股融資結構壓力。
    """

    if period_str == "週末特刊-美股週收盤":
        role = "分析本週全球收盤表現，並評估地緣政治對週一開盤的預期影響。"
    elif period_str == "週末特刊-下週展望":
        role = "執行【全球局勢與長線趨勢掃描】，找出未來一週的潛在爆發點。"
    elif period_str == "盤前":
        role = "結合昨晚美股收盤、最新 VIX 與凌晨突發局勢，為今日台股盤前定調。"
    else: # 盤後
        role = "總結今日籌碼消長，並觀察市場對最新地緣政治訊息的消化程度。"

    prompt = f"""
{strategy_prompt}
{role}

【素材】：
{text}

請嚴格依照格式輸出：
🌟財經AI快報 {datetime.now(TW_TZ).strftime("%Y-%m-%d")} ({period_str})

🚩【全球局勢與地緣政治警示】
📊【市場壓力測試】 (VIX、匯率、融資分析)
💰【台股戰略定調】
💎【產業長線觀察】
"""
    
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
    # 確保使用確定存在的 2.5 版本
    model = genai.GenerativeModel("gemini-2.5-flash") #
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: 
        return f"AI 情報官連線失敗: {e}"

def run_daily():
    update_hot_stocks()
    news = fetch_news()
    now_tw = datetime.now(TW_TZ)
    weekday = now_tw.weekday()
    period_str = "盤前" if now_tw.hour < 12 else "盤後"
    if weekday == 5: period_str = "週末特刊-美股週收盤"
    if weekday == 6: period_str = "週末特刊-下週展望"

    report_text = ai_analyze(news, period_str)
    
    payload = {
        "updated_at_utc": now_tw.strftime("%Y-%m-%d %H:%M:%S (TW)"),
        "title": f"財經AI快報 {now_tw.strftime('%Y-%m-%d')} {period_str}",
        "report": report_text,
        "news": news,
    }
    
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    
    os.makedirs(HISTORY_DIR, exist_ok=True)
    hist_name = f"{now_tw.strftime('%Y-%m-%d')}_{period_str}.json"
    with open(os.path.join(HISTORY_DIR, hist_name), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_daily()
