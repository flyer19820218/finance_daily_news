import yfinance as yf
import os
import re
import json
import calendar
import requests
from datetime import datetime, timedelta, timezone, time
import feedparser
import google.generativeai as genai

# ==========================================
# 1️⃣ 基礎設定與環境變數 (Settings)
# ==========================================
# 告訴爬蟲要去哪裡抓新聞 (Google News RSS)
RSS_LIST = [
    "https://news.google.com/rss/search?q=finance+OR+stock+OR+geopolitics&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    "https://news.google.com/rss/search?q=股市+OR+地緣政治+OR+軍事+OR+傳聞&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
]

# 設定資料要存放在哪裡
CACHE_FILE = "data/news_cache.json"
OUT_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"
HOT_STOCKS_FILE = "hot_stocks.json"

# 設定台灣時區
TW_TZ = timezone(timedelta(hours=8))

# ==========================================
# 2️⃣ 新聞快取與爬蟲機制 (News Fetching)
# ==========================================
def clean_html(text: str) -> str:
    """清除新聞摘要中的 HTML 標籤，讓文字乾淨"""
    return re.sub(r"<.*?>", "", text or "")

def load_cache():
    """讀取已經抓過的新聞連結，避免重複抓取"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except: return []
    return []

def save_cache(cache_list):
    """把最新抓到的新聞連結存起來"""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_list[-200:], f, ensure_ascii=False, indent=2)

def fetch_news(hours=24, limit=64):
    """去 RSS 抓取過去 24 小時內的新聞，最多回傳 64 筆"""
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
            if dt < cutoff: continue # 太舊的新聞不要
            link = getattr(e, "link", None)
            if not link or link in cache_set: continue # 抓過的不要
                
            news.append({
                "title": getattr(e, "title", "(no title)"),
                "link": link,
                "summary": clean_html(e.get("summary", ""))[:300], # 擷取摘要
                "dt_utc": dt.isoformat(),
            })
            cache_set.add(link)
            cache_list.append(link)
            
    save_cache(cache_list)
    news.sort(key=lambda x: x["dt_utc"], reverse=True)
    return news[:limit] # 🌟 這裡原本的錯字已經修復為 return

# ==========================================
# 3️⃣ 輔助資料抓取 (人氣股與真實市場指標)
# ==========================================
def update_hot_stocks():
    """去證交所抓取當天成交量前 20 名的人氣股"""
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX20"
        res = requests.get(url, timeout=10)
        data = res.json()
        top_6 = {f"{item['Code']}.TW": item['Name'] for item in data[:6]}
        with open(HOT_STOCKS_FILE, "w", encoding="utf-8") as f:
            json.dump({"top_volume_pool": top_6}, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ 抓取爆量名單失敗: {e}")

def fetch_risk_indicators():
    """抓取 VIX、匯率、大盤 PE/PB 與景氣燈號 (前端儀表板專用)"""
    risk_data = {
        "vix": "-", "vix_trend": "",
        "usd_twd": "-", "usd_trend": "",
        "pe": "-", "pb": "-",
        "light": "紅燈 (39分)", # 手動設定當月燈號
        "light_month": f"{datetime.now(TW_TZ).year}年最新資料"
    }
    
    # 抓取 VIX
    try:
        vix_data = yf.Ticker("^VIX").history(period="1d")
        vix_close = vix_data['Close'].iloc[-1]
        vix_open = vix_data['Open'].iloc[-1]
        risk_data["vix"] = f"{vix_close:.2f}"
        risk_data["vix_trend"] = f"▲ {vix_close-vix_open:.2f}" if vix_close > vix_open else f"▼ {vix_open-vix_close:.2f}"
    except: pass

    # 抓取 匯率
    try:
        twd_data = yf.Ticker("TWD=X").history(period="1d")
        twd_close = twd_data['Close'].iloc[-1]
        twd_open = twd_data['Open'].iloc[-1]
        risk_data["usd_twd"] = f"{twd_close:.2f}"
        risk_data["usd_trend"] = f"▲ {twd_close-twd_open:.2f}" if twd_close > twd_open else f"▼ {twd_open-twd_close:.2f}"
    except: pass

    # 抓取 大盤 PE / PB
    try:
        url = "https://www.twse.com.tw/exchangeReport/BWIBBU_d?response=json"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            twse_data = res.json()
            latest_day_data = twse_data.get("data", [])[-1]
            risk_data["pe"] = latest_day_data[3]
            risk_data["pb"] = latest_day_data[4]
    except: pass
    
    return risk_data

def get_market_indicators_text(risk_data):
    """將抓到的風險數據轉成文字，準備餵給 AI"""
    indicators = []
    if risk_data["vix"] != "-": indicators.append(f"👉 VIX 恐慌指數：{risk_data['vix']} ({risk_data['vix_trend']})")
    if risk_data["usd_twd"] != "-": indicators.append(f"👉 美元/台幣匯率：{risk_data['usd_twd']} ({risk_data['usd_trend']})")
    if risk_data["pe"] != "-": indicators.append(f"👉 大盤本益比(PE)：{risk_data['pe']} | 股價淨值比(PB)：{risk_data['pb']}")
    indicators.append(f"👉 目前台灣景氣對策信號：{risk_data['light']}")
    
    return "【當前真實市場指標】\n" + "\n".join(indicators)

# ==========================================
# 4️⃣ Telegram 推播功能 (Notification)
# ==========================================
def send_telegram_message(text):
    """將生成的 AI 報告傳送到您的 Telegram 手機裡（具備格式錯誤自動重發防禦機制）"""
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("⚠️ 未設定 Telegram Token 或 Chat ID，跳過推播。")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # 第一次嘗試：帶有 Markdown 格式發送
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown" 
    }
    
    try:
        res = requests.post(url, json=payload, timeout=10)
        
        # 如果成功發送
        if res.status_code == 200:
            print("✅ Telegram 推播成功！(格式渲染完美)")
            
        # 🚨 如果遇到格式解析錯誤 (Error 400) -> 啟動安全氣囊，改用純文字重發！
        elif res.status_code == 400 and "can't parse entities" in res.text:
            print("⚠️ Telegram 格式解析失敗，啟動【純文字安全模式】重新發送...")
            safe_payload = {
                "chat_id": chat_id,
                "text": text
                # 故意拿掉 parse_mode，當作純文字發送，保證絕對不會被擋！
            }
            safe_res = requests.post(url, json=safe_payload, timeout=10)
            if safe_res.status_code == 200:
                print("✅ Telegram 安全模式推播成功！(已還原為純文字)")
            else:
                print(f"❌ 安全模式也推播失敗: {safe_res.text}")
                
        else:
            print(f"⚠️ Telegram 推播失敗: {res.text}")
            
    except Exception as e:
        print(f"⚠️ Telegram 請求發生錯誤: {e}")

# ==========================================
# 5️⃣ 核心 AI 大腦 (Gemini 2.5 Flash 終極深度版)
# ==========================================
def ai_analyze(news, period_str, risk_data):
    """把新聞和數據餵給 Gemini，並要求它產出高質量的深度報告"""
    if not news: 
        return f"📰 目前偵蒐範圍內無重大市場波動事件。({period_str})"
        
    text = "\n".join([f"{n['title']} | {n['summary']}" for n in news])
    
    # 將風險數據轉成給 AI 讀的文字
    market_data_section = get_market_indicators_text(risk_data)
    
    print("\n=== 🕵️‍♂️ 系統抓到的盤前真實數據 ===")
    print(market_data_section)
    print("==================================\n")

    # 🌟 升級版 Prompt：強制要求金星星與指標引述
    strategy_prompt = f"""
    你是全球頂級政經情報中心的資深戰略分析官。
    任務：偵蒐並深度分析全球政經事件對台股與全球市場的衝擊。
    
    【提供給你的素材】：
    {market_data_section}
    {text}
    
    【撰寫規範】：
    請嚴格依照以下 Markdown 格式輸出，必須保持極高的專業度、層次分明，且分析具備深度。
    ⚠️【絕對強制要求】：所有條列項目的開頭，都必須使用「★」符號！嚴禁使用「-」或「•」。

    ★ 🎯 【一分鐘速讀懶人包】
    請用 3 句極簡的列點(開頭用★)，直接點出今日市場的「核心多空風向」、「最需留意的風險」與「強勢板塊」，讓讀者 10 秒內掌握全局。

    ★ 📊 【重大事件】
    請從素材中挑選 4-6 件對市場影響最大的政經或產業新聞，依序進行深度解析。
    X. [事件精簡標題]
       ★ 重要性：[以 ★ 表示，最高五顆星，例如 ★★★★☆]
       ★ 解讀：[深度分析該事件對全球經濟、供應鏈或資金流向的具體影響]

    ★ 🔥 【市場情緒與壓力測試】
    ⚠️【強制執行事項】：必須「明確引述」提供的 VIX 數值、匯率、PE/PB 以及景氣燈號，並以此作為籌碼與估值壓力的佐證！
    請統整目前的市場心理狀態，分析資金板塊轉移的可能方向。

    ★ 💰 【台股影響與板塊點名】
    請綜合評估對台股的影響，分為兩個維度：
    ★ 短期影響：[說明利多、利空或震盪。必須具體點名受惠與受衝擊產業]
    ★ 長期趨勢：[說明在當前局勢下，哪些產業仍具備基本面護城河]

    ★ 📈 【投資觀察指引】
    請給出 3-5 點具體、可操作的投資與觀察建議(開頭用★)。
    """

    genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    try:
        response = model.generate_content(strategy_prompt)
        return response.text
    except Exception as e: 
        return f"AI 情報官連線失敗: {e}"

# ==========================================
# 6️⃣ 主程式執行流程 (Main Pipeline)
# ==========================================
def run_daily():
    """接收 YAML 經理的指令，執行對應任務"""
    
    task_type = os.environ.get("TASK_TYPE", "full_report")
    print(f"🎯 接收到指令，啟動任務模式：【{task_type}】")

    update_hot_stocks() # 抓人氣股
    new_fetched_news = fetch_news() # ⚠️ 這裡爬蟲只會回傳「沒抓過的全新新聞」
    
    # 判斷該寫哪個時段的報告名稱
    now_tw = datetime.now(TW_TZ)
    weekday = now_tw.weekday()
    period_str = "盤前" if now_tw.hour < 12 else "盤後"
    if weekday == 5: period_str = "週末特刊-美股週收盤"
    if weekday == 6: period_str = "週末特刊-下週展望"

    # 🌟 讀取上次存檔的「舊報告」與「舊新聞」
    old_report = "📊 AI 報告將於指定發報時間自動生成。"
    old_news = []
    if os.path.exists(OUT_FILE):
        try:
            with open(OUT_FILE, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                old_report = old_data.get("report", old_report)
                old_news = old_data.get("news", [])
        except: pass

    # 🌟 關鍵修復：把「新抓的」跟「舊有的」新聞大合體！
    combined_news = new_fetched_news + old_news
    seen_links = set()
    final_news = []
    
    # 去除重複的新聞
    for n in combined_news:
        if n["link"] not in seen_links:
            seen_links.add(n["link"])
            final_news.append(n)
            
    # 按照時間由新到舊重新排隊，並嚴格切出最熱騰騰的前 64 則！
    final_news.sort(key=lambda x: x["dt_utc"], reverse=True)
    final_news = final_news[:64]

    # 🌟 抓取最新鮮的市場風險指標
    current_risk_data = fetch_risk_indicators()

    # 根據任務指令，決定要不要叫醒 AI
    if task_type == "full_report":
        print("🧠 執行任務：呼叫 AI 撰寫深度報告並推播...")
        # ⚠️ 把 64 則新聞與風險指標一起餵給 AI
        report_text = ai_analyze(final_news, period_str, current_risk_data)
        send_telegram_message(report_text) 
    else:
        print("📰 執行任務：僅靜默更新新聞，不呼叫 AI。")
        report_text = old_report 
    
    # 組裝成 JSON 格式準備存檔
    payload = {
        "updated_at_utc": now_tw.strftime("%Y-%m-%d %H:%M:%S (TW)"),
        "title": f"全球局勢與市場情報 {now_tw.strftime('%Y-%m-%d')} {period_str}",
        "report": report_text,
        "news": final_news, 
        "risk_indicators": current_risk_data, # 🌟 關鍵：將前端儀表板要用的數據存入！
    }
    
    # 存檔：覆寫最新報告
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    
    # 存檔：保留一份歷史紀錄
    os.makedirs(HISTORY_DIR, exist_ok=True)
    hist_name = f"{now_tw.strftime('%Y-%m-%d')}_{period_str}.json"
    with open(os.path.join(HISTORY_DIR, hist_name), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_daily()
