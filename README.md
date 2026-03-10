🚀 Lyu-Science-Cloud Financial AI Daily | 財經 AI 快報
A fully automated, dual-platform (Web & Mobile) financial analysis system powered by AI and Edge computing.
一套全自動化、雙端部署（網頁與手機）的 AI 財經分析與語音播報系統。

💡 Core Philosophy / 產品核心理念
"Investing is a marathon, not a sprint." / 「投資是一場馬拉松，而不是百米衝刺。」

This platform is deliberately designed to foster long-term investment mindsets. While it provides real-time equity indices and institutional data, it explicitly excludes high-volatility, short-term speculative commodities like Gold and Crude Oil. The UI/UX is engineered to deliver macro-trends and reduce daily trading anxiety, guiding users towards financial freedom through steady, long-term perspectives.

本系統的設計初衷為建立健康的長線投資思維。雖然系統提供即時的股市指數與法人籌碼動向，但我們刻意在系統層面阻斷了黃金、原油等高波動、易誘發短線投機的報價資訊。整體的 UI/UX 旨在呈現總體經濟趨勢，降低使用者的看盤焦慮，引導受眾透過穩健的長線視角通往財務自由。

✨ Key Features / 核心功能
1. 🤖 AI-Powered Market Analysis (多模態 AI 盤勢分析)
(EN) Integrates LLMs (Gemini) to automatically aggregate and summarize global financial events, pre-market/post-market trends, and weekend special reports.

(TW) 深度整合 Gemini AI，全自動統整全球財經事件，依據時段自動產出「盤前速讀」、「盤後精華」與「週末特報」。

2. 🎙️ Zero-Latency Neural Voice Broadcast (零延遲神經網路語音播報)
(EN) Utilizes edge-tts (HsiaoChen Neural Voice) with asynchronous I/O (asyncio) for seamless audio generation. Includes a custom pronunciation dictionary for financial jargon.

(TW) 採用 edge-tts 神經語音引擎，結合 asyncio 協程技術達成前端零延遲播放。內建專屬財經破音字字典（如：重挫、重擊）以確保播報專業度。

3. 📱 Dual-Microservice Architecture (雙端微服務架構)
(EN) Independent routing and UI rendering for Desktop (app.py) and Mobile (mapp.py), featuring customized CSS, responsive grids, and iOS dark-mode fixes.

(TW) 電腦版與手機版獨立架構。手機版具備專屬特務級 UI、動態漲跌方塊、富途牛牛風格的 24H 新聞垂直時間軸，並完美修復 iOS 瀏覽器渲染問題。

4. ⚙️ 100% Unattended Automation (全自動化無人值守)
(EN) Decoupled data generation and frontend rendering. Uses JSON as the data bridge, driven by fully automated Cron-job triggers for uninterrupted daily updates.

(TW) 資料產出與前端展示完全解耦。以 JSON 作為資料橋樑，透過 Cron-job 節點打破雲端休眠限制，達成 100% 免人工介入的全自動化運作。

🏗️ System Architecture / 系統架構
Data Aggregation: yfinance (Global/Taiwan equities) + HiStock (Institutional movements) + 24H News Crawlers.

Data Processing: LLM Summarization -> Local JSON storage (latest_report.json).

Frontend Caching: Advanced Streamlit @st.cache_data implementation to prevent memory leaks (Out of Memory) and handle high-frequency wake-ups.

Hosting Pipeline: GitHub repository connected to Streamlit Community Cloud with CI/CD deployment.
🛠️ Tech Stack / 技術堆疊
Backend & Automation: Python 3.10+, asyncio, requests, pandas, Cron-job.org

Frontend: Streamlit, HTML5/CSS3 Custom Components

AI & Voice: Gemini API, edge-tts

Financial Data: yfinance, Web Scraping (BeautifulSoup / lxml)

🚀 Quick Start / 快速啟動
Clone the repository (複製專案)

Bash
git clone https://github.com/your-username/Lyu-Science-Cloud-APP.git
cd Lyu-Science-Cloud-APP
Install dependencies (安裝套件)

Bash
pip install -r requirements.txt
Run the Application (啟動伺服器)

For Desktop Web (電腦網頁版):

Bash
streamlit run app.py
For Mobile App (手機特務版):

Bash
streamlit run mapp.py
📄 Disclaimer / 免責聲明
(EN) The financial data and AI-generated summaries provided by this application are for informational and educational purposes only. They do not constitute financial advice. Users should conduct their own research before making any investment decisions.

(TW) 本系統提供之財經數據與 AI 摘要僅供學術交流與資訊參考，不構成任何投資建議。使用者在進行任何金融交易前，應自行審慎評估風險。

Built with ❤️ for Long-Term Investors.
