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
    "https://news.google.com/rss/search?q=finance+OR+stock&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    "https://news.google.com/rss/search?q=台股+OR+美股&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
]

CACHE_FILE = "data/news_cache.json"
OUT_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"
HOT_STOCKS_FILE = "hot_stocks.json"

# 設定台灣時區
TW_TZ = timezone(timedelta(hours=8))

# === 工具函數 ===
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
    except Exception as e:
        print(f"⚠️ 抓取爆量名單失敗: {e}")

# === 🌟 核心 AI 大腦 (結合資深投資人思維) ===
def ai_analyze(news, period_str):
    if not news: 
        return f"📰 今日目前無更新之重大財經事件。({period_str})"
        
    text = "\n".join([f"{n['title']} | {n['summary']}" for n in news])
    
    # 預設：平日絕不點名個股，避免誤導短線交易
    investment_section = "📈【投資觀察】\n(請提供大盤趨勢與總經觀察，勿點名個股，避免誘使短線跟風)"
    
    # 根據排程時間，切換 AI 角色與任務
    if period_str == "週末特刊-美股週收盤":
        role = "你是頂級美股策略師。請總結本週美股表現，並分析對下週一台灣相關供應鏈的總經衝擊。"
        
    elif period_str == "週末特刊-下週展望":
        role = "你是信奉長期價值的資深投資專家。請執行【一週產業趨勢與價值投資檢視】。"
        # 👑 邏輯大師限定：只有週日才給長線護城河選股
        investment_section = """💎【AI 價值投資與長波段觀察】
(聲明：以下基於產業長線趨勢推演，適合中長期波段佈局，絕非短線進出建議，請自負盈虧)
請挑選新聞中具備「長線保護短線、基本面良好、產業趨勢成型」的 3 檔個股，並詳述其長線護城河與投資邏輯，絕對避免任何煽動性的極短線預測。"""
        
    elif period_str == "盤前":
        role = "你是總體經濟分析師。現在是早晨盤前，請針對昨晚美股影響，提供今日台股總體觀盤重點。"
        
    else: # 盤後
        role = "你是台股操盤手。現在是下午盤後，請分析今日大盤勢態並總結法人籌碼動向。"

    prompt = f"""
{role}

新聞素材：
{text}

請依照以下格式輸出報告：
🌟財經AI快報 {datetime.now(TW_TZ).strftime("%Y-%m-%d")} ({period_str})

📊重大事件
🔥市場情緒
💰台股大盤影響
{investment_section}
"""
    
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    try:
        return model.generate_content(prompt).text
    except Exception as e: 
        return f"AI 分析失敗: {e}"

# === 主程式執行 ===
def run_daily():
    # 1. 抓取當日爆量名單 (供前端使用)
    update_hot_stocks()
    
    # 2. 抓取新聞
    news = fetch_news()
    
    # 3. 判斷台灣時間與星期幾
    now_tw = datetime.now(TW_TZ)
    weekday = now_tw.weekday() # 0=週一, 5=週六, 6=週日
    
    if weekday == 5:
        period_str = "週末特刊-美股週收盤"
    elif weekday == 6:
        period_str = "週末特刊-下週展望"
    else:
        if now_tw.hour < 12:
            period_str = "盤前"
        else:
            period_str = "盤後"

    # 4. 呼叫 AI 進行分析
    report_text = ai_analyze(news, period_str)
    
    # 5. 打包資料
    payload = {
        "updated_at_utc": now_tw.strftime("%Y-%m-%d %H:%M:%S (TW)"),
        "title": f"財經AI快報 {now_tw.strftime('%Y-%m-%d')} {period_str}",
        "report": report_text,
        "news": news,
    }
    
    # 6. 存入最新報告 (覆蓋)
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    
    # 7. 存入歷史紀錄 (永不覆蓋，保留珍貴資產)
    os.makedirs(HISTORY_DIR, exist_ok=True)
    hist_name = f"{now_tw.strftime('%Y-%m-%d')}_{period_str}.json"
    with open(os.path.join(HISTORY_DIR, hist_name), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_daily()
