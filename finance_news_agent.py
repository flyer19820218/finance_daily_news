import yfinance as yf
import os
import re
import json
import calendar
import requests
from datetime import datetime, timedelta, timezone, time
import feedparser
import google.generativeai as genai
import pandas as pd  # 🌟 修復：補上 Pandas，不然抓融資維持率會當機！

# ==========================================
# 1️⃣ 基礎設定與環境變數 (Settings)
# ==========================================
RSS_LIST = [
    "https://news.google.com/rss/search?q=finance+OR+stock+OR+geopolitics&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
    "https://news.google.com/rss/search?q=股市+OR+地緣政治+OR+軍事+OR+傳聞&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
]

CACHE_FILE = "data/news_cache.json"
OUT_FILE = "data/latest_report.json"
HISTORY_DIR = "data/history"
HOT_STOCKS_FILE = "hot_stocks.json"

TW_TZ = timezone(timedelta(hours=8))

# ==========================================
# 2️⃣ 新聞快取與爬蟲機制 (News Fetching)
# ==========================================
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

def fetch_news(hours=24, limit=64):
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

# ==========================================
# 3️⃣ 輔助資料抓取 (人氣股與真實市場指標)
# ==========================================
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

def fetch_risk_indicators():
    """全自動抓取：VIX、匯率、融資維持率(HiStock)、大盤估值(以0050為代理)"""
    risk_data = {
        "vix": "-", "vix_trend": "",
        "usd_twd": "-", "usd_trend": "",
        "pe": "-", "pb": "-",
        "margin_ratio": "-" 
    }
    
    # 1. 抓取 VIX
    try:
        vix_data = yf.Ticker("^VIX").history(period="1d")
        vix_close = vix_data['Close'].iloc[-1]
        vix_open = vix_data['Open'].iloc[-1]
        risk_data["vix"] = f"{vix_close:.2f}"
        risk_data["vix_trend"] = f"▲ {vix_close-vix_open:.2f}" if vix_close > vix_open else f"▼ {vix_open-vix_close:.2f}"
    except: pass

    # 2. 抓取 匯率
    try:
        twd_data = yf.Ticker("TWD=X").history(period="1d")
        twd_close = twd_data['Close'].iloc[-1]
        twd_open = twd_data['Open'].iloc[-1]
        risk_data["usd_twd"] = f"{twd_close:.2f}"
        risk_data["usd_trend"] = f"▲ {twd_close-twd_open:.2f}" if twd_close > twd_open else f"▼ {twd_open-twd_close:.2f}"
    except: pass

    # 3. 抓取大盤融資維持率 (從 HiStock)
    try:
        url_margin = "https://histock.tw/stock/margin.aspx"
        headers = {"User-Agent": "Mozilla/5.0"}
        res_m = requests.get(url_margin, headers=headers, timeout=10)
        res_m.encoding = 'utf-8'
        dfs = pd.read_html(res_m.text)
        df_margin = dfs[0]
        if '維持率' in df_margin.columns:
            risk_data['margin_ratio'] = str(df_margin['維持率'].iloc[0])
    except Exception as e: 
        print(f"融資維持率抓取失敗: {e}")

    # 4. 抓取大盤估值 (以 0050 作為大盤代理)
    try:
        url_twse = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"
        res_t = requests.get(url_twse, timeout=10)
        data_t = res_t.json()
        for item in data_t:
            if item.get('Code') == '0050':
                risk_data['pe'] = item.get('PEratio', '-')
                risk_data['pb'] = item.get('PBratio', '-')
                break
    except Exception as e:
        print(f"PE/PB抓取失敗: {e}")
        
    return risk_data

def get_market_indicators_text(risk_data):
    indicators = []
    if risk_data["vix"] != "-": indicators.append(f"👉 VIX 恐慌指數：{risk_data['vix']} ({risk_data['vix_trend']})")
    if risk_data["usd_twd"] != "-": indicators.append(f"👉 美元/台幣匯率：{risk_data['usd_twd']} ({risk_data['usd_trend']})")
    if risk_data["margin_ratio"] != "-": indicators.append(f"👉 大盤融資維持率：{risk_data['margin_ratio']}")
    if risk_data["pe"] != "-": indicators.append(f"👉 台灣大盤本益比(PE)：{risk_data['pe']} | 股價淨值比(PB)：{risk_data['pb']}")
    return "【當前真實市場指標】\n" + "\n".join(indicators)

# ==========================================
# 4️⃣ Telegram 推播功能 (Notification)
# ==========================================
def send_telegram_message(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("⚠️ 未設定 Telegram Token 或 Chat ID，跳過推播。")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = { "chat_id": chat_id, "text": text, "parse_mode": "Markdown" }
    
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("✅ Telegram 推播成功！(格式渲染完美)")
        elif res.status_code == 400 and "can't parse entities" in res.text:
            print("⚠️ Telegram 格式解析失敗，改用純文字重發...")
            safe_payload = { "chat_id": chat_id, "text": text }
            safe_res = requests.post(url, json=safe_payload, timeout=10)
            if safe_res.status_code == 200: print("✅ Telegram 安全模式推播成功！")
            else: print(f"❌ 安全模式也推播失敗: {safe_res.text}")
        else:
            print(f"⚠️ Telegram 推播失敗: {res.text}")
    except Exception as e:
        print(f"⚠️ Telegram 請求發生錯誤: {e}")

# ==========================================
# 5️⃣ 核心 AI 大腦 (Gemini 2.5 Flash)
# ==========================================
def ai_analyze(news, period_str, risk_data):
    if not news: 
        return f"📰 目前偵蒐範圍內無重大市場波動事件。({period_str})"
        
    text = "\n".join([f"{n['title']} | {n['summary']}" for n in news])
    market_data_section = get_market_indicators_text(risk_data)
    
    print("\n=== 🕵️‍♂️ 系統抓到的盤前真實數據 ===")
    print(market_data_section)
    print("==================================\n")

    # 🌟 升級版 Prompt：強制要求金星星，並下達最高禁言令
    strategy_prompt = f"""
    你是全球頂級政經情報中心的資深戰略分析官。
    任務：偵蒐並深度分析全球政經事件對台股與全球市場的衝擊。
    
    【提供給你的素材】：
    {market_data_section}
    {text}
    
    【撰寫規範】：
    請嚴格依照以下 Markdown 格式輸出，必須保持極高的專業度。
    ⚠️【最高指令一】：所有條列項目的開頭，都必須使用「★」符號！嚴禁使用「-」或「•」。
    ⚠️【最高指令二】：嚴禁輸出任何問候語（如「好的長官」、「我是分析官」等廢話）。你的回答第一行必須直接是「★ 🎯 【一分鐘速讀懶人包】」。
    ⚠️【最高指令三】：每月月初，請自動在報告中針對台灣宏觀景氣循環進行長線投資觀察的補充。

    ★ 🎯 【一分鐘速讀懶人包】
    請用 3 句極簡的列點(開頭用★)，直接點出今日市場的「核心多空風向」、「最需留意的風險」與「強勢板塊」。

    ★ 📊 【重大事件】
    請挑選 4-6 件對市場影響最大的政經或產業新聞進行解析。
    X. [事件精簡標題]
       ★ 重要性：[以 ★ 表示，最高五顆星]
       ★ 解讀：[深度分析該事件對經濟或資金流向的影響]

    ★ 🔥 【市場情緒與壓力測試】
    必須「明確引述」提供的 VIX、匯率、融資維持率與 PE/PB，以此作為籌碼與估值壓力的佐證！

    ★ 💰 【台股影響與板塊點名】
    ★ 短期影響：[說明利多、利空或震盪。具體點名受惠與受衝擊產業]
    ★ 長期趨勢：[說明哪些產業仍具備基本面護城河]

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
    task_type = os.environ.get("TASK_TYPE", "full_report")
    print(f"🎯 接收到指令，啟動任務模式：【{task_type}】")

    update_hot_stocks() 
    new_fetched_news = fetch_news() 
    
    now_tw = datetime.now(TW_TZ)
    weekday = now_tw.weekday()
    period_str = "盤前" if now_tw.hour < 12 else "盤後"
    if weekday == 5: period_str = "週末特刊-美股週收盤"
    if weekday == 6: period_str = "週末特刊-下週展望"

    old_report = "📊 AI 報告將於指定發報時間自動生成。"
    old_news = []
    if os.path.exists(OUT_FILE):
        try:
            with open(OUT_FILE, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                old_report = old_data.get("report", old_report)
                old_news = old_data.get("news", [])
        except: pass

    combined_news = new_fetched_news + old_news
    seen_links = set()
    final_news = []
    
    for n in combined_news:
        if n["link"] not in seen_links:
            seen_links.add(n["link"])
            final_news.append(n)
            
    final_news.sort(key=lambda x: x["dt_utc"], reverse=True)
    final_news = final_news[:64]

    current_risk_data = fetch_risk_indicators()

    if task_type == "full_report":
        print("🧠 執行任務：呼叫 AI 撰寫深度報告並推播...")
        report_text = ai_analyze(final_news, period_str, current_risk_data)
        send_telegram_message(report_text) 
    else:
        print("📰 執行任務：僅靜默更新新聞，不呼叫 AI。")
        report_text = old_report 
    
    payload = {
        "updated_at_utc": now_tw.strftime("%Y-%m-%d %H:%M:%S (TW)"),
        "title": f"全球局勢與市場情報 {now_tw.strftime('%Y-%m-%d')} {period_str}",
        "report": report_text,
        "news": final_news, 
        "risk_indicators": current_risk_data, 
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
