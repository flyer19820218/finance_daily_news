import yfinance as yf
import os
import re
import json
import calendar
import requests
from datetime import datetime, timedelta, timezone, time
import feedparser
import google.generativeai as genai
import pandas as pd
from curl_cffi import requests as stealth_requests
import io

# ==========================================
# 1. 基礎設定與環境變數 (Settings)
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
# 2. 曉臻財經小教室 - 特務專屬單字庫
# ==========================================
FINANCE_TERMS = [
    # --- 總經與央行政策 ---
    "VIX 恐慌指數", "CPI (消費者物價指數)", "PCE (個人消費支出物價指數)", "PPI (生產者物價指數)", "非農就業數據 (NFP)", 
    "聯準會 (Fed)", "FOMC (聯邦公開市場委員會)", "點陣圖 (Dot Plot)", "基準利率", "降息與升息", 
    "量化寬鬆 (QE)", "量化緊縮 (QT)", "殖利率倒掛", "殖利率曲線 (Yield Curve)", "無風險利率", 
    "GDP (國內生產毛額)", "PMI (採購經理人指數)", "ISM 製造業指數", "初領失業金人數", "褐皮書 (Beige Book)",
    "停滯性通膨 (Stagflation)", "通膨預期", "核心通膨", "軟著陸 (Soft Landing)", "硬著陸 (Hard Landing)",
    "不著陸 (No Landing)", "黑色星期五 (Black Friday)", "黑色星期一", "熔斷機制", "流動性陷阱",
    "布蘭特原油", "西德州原油 (WTI)", "OPEC+ (石油輸出國組織)", "避險貨幣", "美元指數 (DXY)",
    "外匯存底", "熱錢 (Hot Money)", "匯率操縱國", "雙赤字 (Twin Deficits)", "購買力平價 (PPP)",

    # --- 基本面與財報分析 ---
    "EPS (每股盈餘)", "本益比 (PE)", "股價淨值比 (PB)", "ROE (股東權益報酬率)", "ROA (資產報酬率)", 
    "毛利率 (Gross Margin)", "營業利益率 (Operating Margin)", "淨利率 (Net Margin)", "EBITDA", "自由現金流 (FCF)", 
    "資本支出 (CapEx)", "營收成長率 (YoY/MoM)", "庫存週轉天數", "應收帳款週轉率", "負債比率", 
    "流動比率", "速動比率", "利息保障倍數", "商譽 (Goodwill)", "無形資產", 
    "法說會 (Earnings Call)", "財測 (Guidance)", "三率三升", "除權息", "填息與貼息", 
    "現金殖利率", "股票股利", "現金股利", "減資 (Capital Reduction)", "庫藏股 (Stock Buyback)", 
    "IPO (首次公開募股)", "SPO (現金增資)", "私募 (Private Placement)", "併購 (M&A)", "敵意併購", 
    "下市 (Delisting)", "ADR (美國存託憑證)", "GDR (全球存託憑證)", "KY股", "全額交割股",

    # --- 台股籌碼與交易機制 ---
    "融資維持率", "融資餘額", "融券餘額", "軋空行情 (Short Squeeze)", "借券賣出餘額", 
    "三大法人", "外資買賣超", "投信作帳", "自營商避險", "八大行庫 (國家隊)", 
    "國安基金", "官股券商", "散戶指標 (小台散戶多空比)", "大額交易人未平倉", "主力進出", 
    "隔日沖", "當沖 (Day Trading)", "現股當沖", "信用交易", "斷頭 (Margin Call)", 
    "限空令", "平盤下不得融券賣出", "處置股票 (關緊閉)", "注意股票", "警示股", 
    "零股交易", "盤後定價交易", "鉅額交易", "集合競價", "逐筆交易",

    # --- 技術分析與型態 ---
    "K線 (陰陽燭)", "跳空缺口", "島狀反轉", "黃金交叉", "死亡交叉", 
    "移動平均線 (MA)", "季線 (生命線)", "年線 (牛熊分界線)", "乖離率 (BIAS)", "均線糾結", 
    "RSI (相對強弱指標)", "MACD (平滑異同移動平均線)", "KD指標 (隨機指標)", "布林通道 (Bollinger Bands)", "OBV (能量潮指標)", 
    "DMI (動向指標)", "SAR (拋物線指標)", "CCI (順勢指標)", "威廉指標 (W%R)", "ATR (真實波動幅度)", 
    "支撐線與壓力線", "頸線 (Neckline)", "頭肩頂", "頭肩底", "W底 (雙重底)", 
    "M頭 (雙重頂)", "箱型整理", "三角收斂", "旗型型態", "杯柄型態 (Cup and Handle)", 
    "波浪理論", "費波那契回撤 (黃金分割)", "量價背離", "爆量長黑", "量縮價跌", 
    "跳水", "誘多與誘空", "洗盤", "拉尾盤", "殺尾盤",

    # --- 科技與半導體產業 ---
    "晶圓代工 (Foundry)", "IC 設計 (Fabless)", "IDM (整合元件製造廠)", "封測 (OSAT)", "摩爾定律", 
    "先進製程", "成熟製程", "EUV (極紫外光微影)", "DUV (深紫外光)", "良率 (Yield)", 
    "CoWoS 先進封裝", "SoIC", "InFO", "2.5D/3D 封裝", "異質整合", 
    "FinFET (鰭式場效電晶體)", "GAA (環繞閘極電晶體)", "矽光子 (Silicon Photonics)", "CPO (共封裝光學)", "ABF 載板", 
    "HBM (高頻寬記憶體)", "DRAM", "NAND Flash", "NOR Flash", "固態硬碟 (SSD)", 
    "ASIC (客製化晶片)", "FPGA (現場可程式化邏輯閘陣列)", "MCU (微控制器)", "CIS (影像感測器)", "PMIC (電源管理IC)", 
    "EDA (電子設計自動化)", "IP (矽智財)", "ARM 架構", "x86 架構", "RISC-V", 
    "GPU (圖形處理器)", "NPU (神經處理單元)", "TPU (張量處理單元)", "邊緣運算 (Edge Computing)", "伺服器 BMC (遠端控制晶片)", 
    "CSP (雲端服務供應商)", "液冷散熱 (Liquid Cooling)", "均熱板 (VC)", "BBU (伺服器備援電池)", "GB200 (輝達AI伺服器)",
    "低軌衛星", "O-RAN (開放網路架構)", "Wi-Fi 7", "第三代半導體 (SiC/GaN)", "車用電子",

    # --- 衍生性商品、期貨與選擇權 ---
    "四巫日 (Quadruple Witching)", "結算日", "期貨正價差", "期貨逆價差", "未平倉量 (Open Interest)", 
    "選擇權 (Options)", "買權 (Call)", "賣權 (Put)", "履約價 (Strike Price)", "權利金 (Premium)", 
    "隱含波動率 (IV)", "歷史波動率 (HV)", "Delta (對沖值)", "Gamma", "Theta (時間價值)", 
    "Vega", "價內 (ITM)", "價平 (ATM)", "價外 (OTM)", "買權賣權比 (Put/Call Ratio)", 
    "保證金 (Margin)", "追繳保證金", "強制平倉", "VIX 期貨", "選擇權賣方 (莊家)",

    # --- 基金、ETF 與資產配置 ---
    "ETF (指數股票型基金)", "主動型基金", "被動投資", "成分股調整", "折溢價", 
    "高股息 ETF", "市值型 ETF", "債券 ETF", "槓桿型 ETF", "反向型 ETF (反一)", 
    "淨值 (NAV)", "追蹤誤差", "內扣費用 (總開銷費用)", "收益平準金", "配息率", 
    "避險基金 (Hedge Fund)", "主權基金", "私募基金 (PE Fund)", "創投 (VC)", "家族辦公室", 
    "資產配置", "股債平衡", "60/40 法則", "定時定額", "單筆投資"
]

# ==========================================
# 3. 新聞快取與爬蟲機制 (News Fetching)
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
# 4. 輔助資料抓取 (人氣股與真實市場指標)
# ==========================================
def update_hot_stocks():
    try:
        # 1. 改為抓取「所有上市個股」的日成交資訊
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        res = requests.get(url, timeout=10)
        data = res.json()
        
        # 2. 準備一個陣列來裝處理後的資料
        processed_data = []
        for item in data:
            try:
                # 取得成交金額 (TradeValue)，移除可能的逗號並轉為整數
                val_str = str(item.get("TradeValue", "0")).replace(",", "")
                val_int = int(val_str)
                processed_data.append({
                    "Code": item["Code"],
                    "Name": item["Name"],
                    "TradeValue": val_int
                })
            except:
                pass
                
        # 3. 依照「成交金額」由大到小 (降冪) 排序
        sorted_data = sorted(processed_data, key=lambda x: x["TradeValue"], reverse=True)
        
        # 4. 取出成交值最高的前 6 名
        top_6 = {f"{item['Code']}.TW": item['Name'] for item in sorted_data[:6]}
        
        # ⚠️ 注意：這裡的存檔 Key 故意保持 "top_volume_pool"，是為了與前端無縫接軌
        with open(HOT_STOCKS_FILE, "w", encoding="utf-8") as f:
            json.dump({"top_volume_pool": top_6}, f, ensure_ascii=False, indent=4)
            
    except Exception as e:
        print(f"⚠️ 抓取成交值排行榜失敗: {e}")

# ==========================================
def fetch_risk_indicators():
    """方案 2 修正版：政府 API 精準對位系統"""
    risk_data = {
        "vix": "-", "vix_trend": "",
        "usd_twd": "-", "usd_trend": "",
        "margin_ratio": "-",
        "business_light": "-"
    }
    
    # 1. VIX & 匯率 (yf 依然是最穩的，不變)
    try:
        vix_df = yf.Ticker("^VIX").history(period="2d")
        v, p = vix_df['Close'].iloc[-1], vix_df['Close'].iloc[-2]
        risk_data["vix"] = f"{v:.2f}"
        risk_data["vix_trend"] = f"▲ {v-p:.2f}" if v > p else f"▼ {p-v:.2f}"
        
        twd_df = yf.Ticker("TWD=X").history(period="2d")
        v, p = twd_df['Close'].iloc[-1], twd_df['Close'].iloc[-2]
        risk_data["usd_twd"] = f"{v:.2f}"
        risk_data["usd_trend"] = f"▲ {v-p:.2f}" if v > p else f"▼ {p-v:.2f}"
    except: pass

    # 2. 🚀 大盤融資維持率 (證交所 BFT41U 暴力解碼)
    try:
        url_margin = "https://www.twse.com.tw/exchangeReport/BFT41U?response=json"
        res = requests.get(url_margin, timeout=10)
        data = res.json()
        if "data" in data and len(data["data"]) > 0:
            latest_row = data["data"][-1]
            # 💡 策略：維持率通常是數值最大的那個欄位 (通常 > 140)
            # 我們過濾出所有數值，找最像維持率的那個
            potential_rates = []
            for val in latest_row:
                clean_val = str(val).replace(",", "").replace("%", "")
                try:
                    num = float(clean_val)
                    if 130 < num < 200: # 正常的維持率區間
                        potential_rates.append(num)
                except: continue
            
            if potential_rates:
                risk_data['margin_ratio'] = f"{potential_rates[-1]}%"
            else:
                # 備案：如果過濾失敗，強制取最後一欄
                risk_data['margin_ratio'] = f"{latest_row[-1]}%"
    except Exception as e: print(f"維持率錯誤: {e}")

    # 3. 🚀 台灣景氣對策信號 (國發會官方 CSV 接口 - 最穩)
    try:
        # 改用 CSV 格式，這種格式政府最少變動
        url_light = "https://ods.ndc.gov.tw/api/v1/rest/datastore/A09000000E-000021-001?format=json"
        res = requests.get(url_light, timeout=10)
        records = res.json().get("result", {}).get("records", [])
        if records:
            # 找到最新的那一筆紀錄
            latest = records[0] 
            # 抓取年月、分數、燈號顏色
            date_v = latest.get("年月", latest.get("PERIOD", "-"))
            score = latest.get("綜合分數", latest.get("SCORE", "0"))
            
            # 判定燈號
            s = int(score)
            if s >= 38: L = "🔴 紅燈"
            elif s >= 32: L = "🟡 黃紅燈"
            elif s >= 23: L = "🟢 綠燈"
            elif s >= 17: L = "🟡 黃藍燈"
            else: L = "🔵 藍燈"
            risk_data['business_light'] = f"{date_v} | {s}分 {L}"
    except Exception as e: print(f"景氣燈號錯誤: {e}")
        
    return risk_data

# ==========================================
def get_market_indicators_text(risk_data):
    """格式化數據供 AI 分析使用"""
    indicators = []
    if risk_data["vix"] != "-": indicators.append(f"👉 VIX 恐慌指數：{risk_data['vix']} ({risk_data['vix_trend']})")
    if risk_data["usd_twd"] != "-": indicators.append(f"👉 美元/台幣匯率：{risk_data['usd_twd']} ({risk_data['usd_trend']})")
    if risk_data["margin_ratio"] != "-": indicators.append(f"👉 大盤融資維持率：{risk_data['margin_ratio']}")
    if risk_data["business_light"] != "-": indicators.append(f"👉 台灣景氣對策信號：{risk_data['business_light']}")
    return "【當前真實市場指標】\n" + "\n".join(indicators)
    
# ==========================================
# 5. Telegram 推播功能 (Notification)
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
            print("✅ Telegram 推播成功！")
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
# 6. 核心 AI 大腦 (Gemini 2.5 Flash)
# ==========================================
def ai_analyze(news, period_str, risk_data, today_term):
    if not news: 
        return f"📰 目前偵蒐範圍內無重大市場波動事件。({period_str})"
        
    text = "\n".join([f"{n['title']} | {n['summary']}" for n in news])
    market_data_section = get_market_indicators_text(risk_data)
    
    today_date = datetime.now(TW_TZ).strftime('%Y-%m-%d')
    
    print("\n=== 🕵️‍♂️ 系統抓到的盤前真實數據 ===")
    print(market_data_section)


    strategy_prompt = f"""
    你是全球頂級政經情報中心的資深戰略分析官。
    任務：偵蒐並深度分析全球政經事件對台股與全球市場的衝擊。
    
    【提供給你的素材】：
    👉 今日日期：{today_date}
    {market_data_section}
    {text}
    
    【撰寫規範】：
    請嚴格依照以下 Markdown 格式輸出，必須保持極高的專業度。
    ⚠️【最高指令一】：所有條列項目的開頭，都必須使用「★」符號！嚴禁使用「-」或「•」。
    ⚠️【最高指令二】：嚴禁輸出任何問候語（如「好的長官」、「我是分析官」等廢話）。你的回答第一行必須直接是「★ 🎯 【一分鐘戰略速讀】」。
    ⚠️【最高指令三】：如果今日日期是每個月的 1 號（不管有無交易），請務必在報告中針對台灣宏觀景氣循環進行「長線投資觀察」的戰略補充。

    ★ 🎯 【一分鐘戰略速讀】
    請撰寫約 150~200 字的精華摘要（設計為剛好適合語音播報 45~60 秒的長度）。請用 3 到 4 個結構完整的列點(開頭用★)，深度解析全局多空定調、資金板塊轉移邏輯，以及潛在風險警戒。

    ★ 📊 【重大事件】
    請挑選 4-6 件對市場影響最大的政經或產業新聞進行解析。
    X. [事件精簡標題]
       ★ 重要性：[以 ★ 表示，最高五顆星]
       ★ 解讀：[深度分析該事件對經濟或資金流向的影響]

    ★ 🔥 【市場情緒與壓力測試】
    必須「明確引述」提供的 VIX、匯率與大盤融資維持率，以此作為籌碼與情緒壓力的佐證！

    ★ 💰 【台股影響與板塊點名】
    ★ 短期影響：[說明利多、利空或震盪。具體點名受惠與受衝擊產業]
    ★ 長期趨勢：[說明哪些產業仍具備基本面護城河]

    ★ 📈 【投資觀察指引】
    請給出 3-5 點具體、可操作的投資與觀察建議(開頭用★)。

    ★ 🏫 【曉臻財經小教室】
    ⚠️今日指定教學名詞：【{today_term}】
    請針對這個指定名詞，用 2 到 3 句「麻瓜也聽得懂」的生動白話文，向新手解釋它的含義以及對股市的代表意義。
    """

    genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    try:
        response = model.generate_content(strategy_prompt)
        return response.text
    except Exception as e: 
        return f"AI 情報官連線失敗: {e}"

# ==========================================
# 7. 主程式執行流程 (Main Pipeline)
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

    # 🌟 取得最新風險指標 (已拔除 PE/PB)
    current_risk_data = fetch_risk_indicators()

    # ====================================================
    # 🌟 曉臻小教室：絕對序位系統 (順序播放，絕對不重複)
    # ====================================================
    # 以 2024 年 1 月 1 日為基準點
    base_date = datetime(2024, 1, 1, tzinfo=TW_TZ)
    # 計算今天距離基準日總共過了幾天
    total_days_passed = (now_tw - base_date).days
    
    # 用總天數對詞庫長度取餘數，保證 800 個詞會「按順序」走完一輪
    term_index = total_days_passed % len(FINANCE_TERMS)
    today_term = FINANCE_TERMS[term_index]

    if task_type == "full_report":
        # 在終端機印出序號，方便教官核對進度
        print(f"🧠 執行任務：呼叫 AI 撰寫深度報告... (今日單字序號：{term_index}，單字：{today_term})")
        report_text = ai_analyze(final_news, period_str, current_risk_data, today_term)
        send_telegram_message(report_text) 
    else:
        print("📰 執行任務：僅靜默更新新聞，不呼叫 AI。")
        report_text = old_report 
    
    # 🌟 準備存檔封包
    payload = {
        "updated_at_utc": now_tw.strftime("%Y-%m-%d %H:%M:%S (TW)"),
        "title": f"全球局勢與市場情報 {now_tw.strftime('%Y-%m-%d')} {period_str}",
        "report": report_text,
        "news": final_news, 
        "risk_indicators": current_risk_data, 
    }
    
    # 🌟 存入最新報告
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    
    # 🌟 存入歷史紀錄夾
    os.makedirs(HISTORY_DIR, exist_ok=True)
    hist_name = f"{now_tw.strftime('%Y-%m-%d')}_{period_str}.json"
    with open(os.path.join(HISTORY_DIR, hist_name), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

# --- 程式進入點 ---
if __name__ == "__main__":
    run_daily()
