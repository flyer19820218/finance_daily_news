import requests
import pandas as pd
import re
import io
import os
import datetime

# =========================
# 1. 基礎設定 (雲端自動抓取金鑰)
# =========================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# =========================
# 2. Telegram 發送模組
# =========================
def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 未設定 Telegram 金鑰，無法發送。")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        requests.post(url, data=data, timeout=10)
        print("✅ Telegram 發送成功")
    except Exception as e:
        print(f"❌ Telegram 發送失敗: {e}")

# =========================
# 3. 爬蟲模組 (景氣燈號、融資維持率、VIX、DXY)
# =========================
def get_economic_light():
    try:
        url = "https://www.moneydj.com/KMDJ/MacroEconomic/MacroEconomicList.aspx?a=1050000"
        r = requests.get(url, headers=HEADERS, timeout=10)
        dfs = pd.read_html(io.StringIO(r.text))
        for df in dfs:
            for i in range(min(len(df), 10)):
                row = [str(x) for x in df.iloc[i].values]
                date = next((v for v in row if re.match(r'^202\d/\d{2}$', v)), None)
                score_str = next((v for v in row if v.isdigit() and 9 <= int(v) <= 45), None)
                if date and score_str:
                    score = int(score_str)
                    if score >= 38: light = "🔴 紅燈 (過熱)"
                    elif score >= 32: light = "🟡 黃紅燈"
                    elif score >= 23: light = "🟢 綠燈 (穩定)"
                    elif score >= 17: light = "🟡 黃藍燈"
                    else: light = "🔵 藍燈 (低迷)"
                    return date, score, light
        return "-", "-", "查無資料"
    except: return "-", "-", "讀取失敗"

def get_margin_rate():
    try:
        r = requests.get("https://histock.tw/stock/margin.aspx", headers=HEADERS, timeout=10)
        match = re.search(r'([1-2]\d{2}\.\d+)\s*%', r.text)
        return float(match.group(1)) if match else None
    except: return None

def get_vix():
    try:
        r = requests.get("https://query1.finance.yahoo.com/v7/finance/quote?symbols=%5EVIX", headers=HEADERS, timeout=10).json()
        return round(float(r["quoteResponse"]["result"][0]["regularMarketPrice"]), 2)
    except: return None

def get_dxy():
    try:
        r = requests.get("https://query1.finance.yahoo.com/v7/finance/quote?symbols=DX-Y.NYB", headers=HEADERS, timeout=10).json()
        return round(float(r["quoteResponse"]["result"][0]["regularMarketPrice"]), 2)
    except: return None

def market_sentiment(vix, margin):
    if vix is None or margin is None: return "⚖️ 資料不足，保持中立"
    if vix < 15 and margin > 170: return "🔥 市場偏多 (貪婪)"
    if vix > 25: return "⚠️ 市場恐慌 (警戒)"
    return "⚖️ 市場中性 (觀望)"

# =========================
# 4. 主程式執行
# =========================
def main():
    print("🚀 啟動市場監控機器人...")
    tw_tz = datetime.timezone(datetime.timedelta(hours=8))
    today = datetime.datetime.now(tw_tz).strftime("%Y-%m-%d")
    
    date, score, light = get_economic_light()
    margin = get_margin_rate()
    vix = get_vix()
    dxy = get_dxy()
    sentiment = market_sentiment(vix, margin)
    
    margin_str = f"{margin} %" if margin else "⚠️ 讀取失敗"
    vix_str = f"{vix}" if vix else "⚠️ 讀取失敗"
    dxy_str = f"{dxy}" if dxy else "⚠️ 讀取失敗"
    
    msg = f"""<b>📊 台股市場戰略監控</b>
📅 日期：{today}

🚦 <b>景氣對策信號</b>：
{date} | {score}分 {light}

💰 <b>大盤融資維持率</b>：
{margin_str}

😱 <b>恐慌指數 (VIX)</b>：
{vix_str}

💵 <b>美元指數 (DXY)</b>：
{dxy_str}

🎯 <b>AI 情緒判定</b>：
{sentiment}
"""
    print(msg)
    send_telegram(msg)

# =========================
# 執行引擎 (這次真的在最下面，而且沒吃掉上面的肉！)
# =========================
if __name__ == "__main__":
    main()
