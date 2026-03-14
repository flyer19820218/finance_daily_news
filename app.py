import streamlit as st
import pandas as pd
import requests
import fitz
import streamlit.components.v1 as components
import base64
import time

# 1. 頁面設定
st.set_page_config(page_title="會考自然-iPad教學戰車", layout="wide")

st.markdown("""
<style>
    .stApp { background: #ffffff; }
    #MainMenu, footer, header {visibility: hidden;}
    .stSelectbox label { font-size: 20px !important; font-weight: bold; color: #1e40af; }
</style>
""", unsafe_allow_html=True)

# 資料讀取 (絕不用 cache)
def load_sheet():
    url = "https://docs.google.com/spreadsheets/d/1qcWBnMUgHVHO5XrN79NhVOWSnExzc8Mnc5wf4uUXbw4/export?format=csv"
    try:
        # 在網址加入隨機數，強迫 Google 給最新版
        r = requests.get(f"{url}&nocache={time.time()}")
        from io import StringIO
        return pd.read_csv(StringIO(r.text))
    except:
        return None

def get_pdf_page_64(page_idx):
    try:
        doc = fitz.open("notes.pdf")
        page = doc.load_page(page_idx)
        pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0)) 
        return base64.b64encode(pix.tobytes("png")).decode('utf-8')
    except:
        return ""

# ==========================================
# 2. 佈局實作
# ==========================================
df = load_sheet()

if df is not None:
    st.title("🚀 自然科衝刺教學系統")
    
    # 頂部控制台
    col_sel, col_btn = st.columns([2, 1])
    
    with col_sel:
        page_list = [f"第 {i+1} 頁" for i in range(len(df))]
        selected_page = st.selectbox("🎯 選擇今天要講哪一頁？", page_list)
        idx = page_list.index(selected_page)

    with col_btn:
        st.write("###") # 補位
        # ✨ 這是我們的終極大招：點了才去抓，且帶上時間標記
        go = st.button("🔥 確定載入 / 抓取最新檔案", use_container_width=True, type="primary")

    if go:
        row = df.iloc[idx]
        audio_file = str(row['Audio_Path']).strip().lstrip('/')
        
        # 💡 生成一個絕對唯一的網址，讓 CDN 沒辦法快取
        unique_v = int(time.time())
        audio_url = f"https://raw.githubusercontent.com/flyer19820218/thelast60days/main/{audio_file}?v={unique_v}"
        json_url = f"https://raw.githubusercontent.com/flyer19820218/thelast60days/main/{audio_file.replace('.mp3', '_script.json')}?v={unique_v}"
        
        pdf_b = get_pdf_page_64(idx)
        
        # 抓字幕
        try:
            res = requests.get(json_url)
            script_json = res.text if res.status_code == 200 else "[]"
        except:
            script_json = "[]"

        # --- HTML 介面 ---
        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            body {{ font-family: sans-serif; margin: 0; padding: 0; background: white; }}
            .play-bar {{ background: #1e40af; color: white; padding: 20px; display: flex; align-items: center; justify-content: space-between; }}
            .btn {{ background: white; color: #1e40af; border: none; padding: 15px 30px; border-radius: 10px; font-weight: bold; font-size: 20px; cursor: pointer; }}
            .pdf-img {{ width: 100%; display: block; }}
            .prog-box {{ background: #f1f5f9; padding: 20px; display: flex; align-items: center; gap: 15px; }}
            input[type=range] {{ flex: 1; accent-color: #1e40af; height: 15px; }}
            .sub-box {{ min-height: 200px; padding: 30px; display: flex; flex-direction: column; }}
            .bubble {{ max-width: 85%; padding: 25px; border-radius: 20px; font-size: 30px; line-height: 1.4; opacity: 0; transition: 0.2s; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
            .yj {{ align-self: flex-start; background: #dbeafe; color: #1e3a8a; }}
            .xz {{ align-self: flex-end; background: #ffe4e6; color: #881337; }}
        </style>
        </head>
        <body>
            <div class="play-bar">
                <span style="font-size: 24px; font-weight: bold;">正在教學：{selected_page}</span>
                <button id="pBtn" class="btn">▶️ 開始講解</button>
            </div>
            
            <audio id="aud" src="{audio_url}"></audio>
            
            <img src="data:image/png;base64,{pdf_b}" class="pdf-img">
            
            <div class="prog-box">
                <input type="range" id="sk" value="0" step="0.1">
                <span id="time" style="font-family: monospace; font-weight: bold;">0:00 / 0:00</span>
            </div>
            
            <div class="sub-box">
                <div id="bb" class="bubble yj"></div>
            </div>

            <script>
                const aud = document.getElementById('aud');
                const pBtn = document.getElementById('pBtn');
                const sk = document.getElementById('sk');
                const bb = document.getElementById('bb');
                const script = {script_json};

                pBtn.onclick = () => {{
                    if(aud.paused) {{ aud.play(); pBtn.innerText = "⏸️ 暫停"; }}
                    else {{ aud.pause(); pBtn.innerText = "▶️ 繼續"; }}
                }};

                aud.onloadedmetadata = () => {{
                    document.getElementById('time').innerText = "0:00 / " + fmt(aud.duration);
                    sk.max = aud.duration;
                }};

                aud.ontimeupdate = () => {{
                    const t = aud.currentTime;
                    document.getElementById('time').innerText = fmt(t) + " / " + fmt(aud.duration);
                    sk.value = t;
                    let hit = false;
                    for(let s of script) {{
                        if(t >= s.start && t <= s.end) {{
                            bb.innerText = s.text;
                            bb.className = "bubble " + (s.speaker === '彥君' ? 'yj' : 'xz');
                            bb.style.opacity = 1;
                            hit = true; break;
                        }}
                    }}
                    if(!hit) bb.style.opacity = 0;
                }};

                sk.oninput = () => aud.currentTime = sk.value;
                function fmt(s) {{ return Math.floor(s/60) + ":" + String(Math.floor(s%60)).padStart(2,'0'); }}
            </script>
        </body>
        </html>
        """
        components.html(html_code, height=2000, scrolling=True)
    else:
        st.info("👋 彥君老師您好！請選好頁碼後，按下「🔥 確定載入」開始上課。")

else:
    st.error("Sheet 資料讀不到，請檢查網路！")
