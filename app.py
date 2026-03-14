import streamlit as st
import pandas as pd
import requests
import fitz
import streamlit.components.v1 as components
import base64
import time

# ==========================================
# 1. 頁面設定 (移植財金快報的視覺感)
# ==========================================
st.set_page_config(page_title="會考自然-iPad教學戰車", layout="wide")

st.markdown("""
<style>
    /* 模仿財金快報的乾淨字體與背景 */
    .stApp { background: #ffffff; }
    #MainMenu, footer, header {visibility: hidden;}
    
    /* iPad 觸控按鈕優化 */
    .stButton>button {
        border-radius: 12px;
        height: 3em;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# 徹底打碎快取的讀取 (參考財金快報 load_json 精神)
def load_data_fresh():
    url = "https://docs.google.com/spreadsheets/d/1qcWBnMUgHVHO5XrN79NhVOWSnExzc8Mnc5wf4uUXbw4/export?format=csv"
    try:
        # 加入 timestamp 確保每次都是新請求
        r = requests.get(f"{url}&t={time.time()}")
        from io import StringIO
        return pd.read_csv(StringIO(r.text))
    except:
        return None

def get_pdf_page_as_base64(local_pdf_path, page_index):
    try:
        doc = fitz.open(local_pdf_path)
        page = doc.load_page(page_index)
        pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0)) 
        img_data = pix.tobytes("png")
        doc.close()
        return base64.b64encode(img_data).decode('utf-8')
    except:
        return ""

# ==========================================
# 2. 核心邏輯：仿財金快報模式切換
# ==========================================
df = load_data_fresh()

if df is not None:
    # 🌟 使用 Session State 存儲當前頁面索引，這是穩定關鍵
    if 'current_idx' not in st.session_state:
        st.session_state.current_idx = 0

    # --- 頂部控制區 (仿財金快報 Layout) ---
    st.markdown("### 📊 教學進度控制")
    top_c1, top_c2, top_c3 = st.columns([2, 1, 1])
    
    with top_c1:
        # 選單切換
        page_list = [f"第 {i+1} 頁" for i in range(len(df))]
        selected_label = st.selectbox("切換頁碼", page_list, index=st.session_state.current_idx)
        new_idx = page_list.index(selected_label)
        
        # 🌟 仿財金快報模式：如果變動了，立刻 rerun
        if new_idx != st.session_state.current_idx:
            st.session_state.current_idx = new_idx
            st.rerun()

    with top_c2:
        st.write("") # 調整高度
        if st.button("🔄 同步新內容", use_container_width=True):
            st.rerun()

    with top_c3:
        st.write("")
        st.success(f"目前位置：{selected_label}")

    st.markdown("---")

    # --- 資料渲染區 ---
    try:
        row = df.iloc[st.session_state.current_idx]
        audio_file = str(row['Audio_Path']).strip().lstrip('/')
        
        # 加上極長 timestamp，完全打破快取
        ts = int(time.time() * 1000)
        audio_url = f"https://raw.githubusercontent.com/flyer19820218/thelast60days/main/{audio_file}?v={ts}"
        json_url = f"https://raw.githubusercontent.com/flyer19820218/thelast60days/main/{audio_file.replace('.mp3', '_script.json')}?v={ts}"
        
        pdf_b64 = get_pdf_page_as_base64("notes.pdf", st.session_state.current_idx)
        
        # 抓取字幕
        res_json = requests.get(json_url)
        script_data = res_json.text if res_json.status_code == 200 else "[]"

        # --- 教學滿版 HTML (字幕絕對會有！) ---
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            body {{ font-family: sans-serif; margin: 0; padding: 0; background: white; }}
            .header-bar {{ display: flex; align-items: center; justify-content: space-between; padding: 10px 20px; border-bottom: 2px solid #2563eb; }}
            .title {{ color: #2563eb; font-size: 28px; font-weight: 900; }}
            .play-btn {{ background: #2563eb; color: white; padding: 12px 24px; border-radius: 50px; border: none; font-size: 18px; font-weight: bold; cursor: pointer; }}
            .pdf-view {{ width: 100%; }}
            .pdf-img {{ width: 100%; display: block; }}
            .seek-panel {{ width: 100%; background: #f8fafc; padding: 15px 20px; display: flex; align-items: center; gap: 15px; box-sizing: border-box; }}
            input[type=range] {{ flex: 1; accent-color: #2563eb; height: 12px; }}
            .time-box {{ font-size: 14px; color: #64748b; min-width: 90px; text-align: right; font-family: monospace; }}
            .subtitle-stage {{ width: 100%; min-height: 180px; display: flex; flex-direction: column; padding: 20px; box-sizing: border-box; }}
            .bubble {{ max-width: 80%; padding: 20px; border-radius: 18px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); font-size: 26px; line-height: 1.5; opacity: 0; transition: 0.2s; }}
            .yanjun {{ align-self: flex-start; background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; }}
            .xiaozhen {{ align-self: flex-end; background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }}
            .name {{ font-size: 12px; font-weight: bold; margin-bottom: 5px; opacity: 0.7; }}
        </style>
        </head>
        <body>
            <div class="header-bar"><div class="title">🚀 {selected_label} 同步教學</div><button id="pBtn" class="play-btn">▶️ 播放講解</button></div>
            <div id="audio-target"></div>
            <div class="pdf-view"><img src="data:image/png;base64,{pdf_b64}" class="pdf-img"></div>
            <div class="seek-panel"><input type="range" id="sk" value="0" step="0.1"><div class="time-box"><span id="cur">0:00</span> / <span id="dur">0:00</span></div></div>
            <div class="subtitle-stage"><div id="bubble" class="bubble yanjun"><div id="spk" class="name"></div><div id="msg"></div></div></div>
            <script>
                // 使用 JS 暴力創建音軌，防止緩存
                const target = document.getElementById('audio-target');
                const aud = document.createElement('audio');
                aud.src = "{audio_url}";
                aud.preload = "auto";
                target.appendChild(aud);

                const pBtn = document.getElementById('pBtn');
                const sk = document.getElementById('sk');
                const bubble = document.getElementById('bubble');
                const spk = document.getElementById('spk');
                const msg = document.getElementById('msg');
                const script = {script_data};

                pBtn.onclick = () => {{
                    if(aud.paused) {{ aud.play(); pBtn.innerText = "⏸️ 暫停"; }}
                    else {{ aud.pause(); pBtn.innerText = "▶️ 繼續"; }}
                }};
                aud.onloadedmetadata = () => {{
                    document.getElementById('dur').innerText = fmt(aud.duration);
                    sk.max = aud.duration;
                }};
                aud.ontimeupdate = () => {{
                    const t = aud.currentTime;
                    document.getElementById('cur').innerText = fmt(t);
                    sk.value = t;
                    let hit = false;
                    for(let s of script) {{
                        if(t >= s.start && t <= s.end) {{
                            spk.innerText = (s.speaker === '彥君' ? '👨‍🏫 彥君老師' : '👩‍🔬 曉臻助教');
                            msg.innerText = s.text;
                            bubble.className = "bubble " + (s.speaker === '彥君' ? 'yanjun' : 'xiaozhen');
                            bubble.style.opacity = 1;
                            hit = true; break;
                        }}
                    }}
                    if(!hit) bubble.style.opacity = 0;
                }};
                sk.oninput = () => aud.currentTime = sk.value;
                function fmt(s) {{ return Math.floor(s/60) + ":" + String(Math.floor(s%60)).padStart(2,'0'); }}
            </script>
        </body>
        </html>
        """
        # 🌟 最終殺招：components.html 雖然不能帶 key，但我們每次 rerun 都是重新生成
        components.html(full_html, height=1800, scrolling=True)

    except Exception as e:
        st.error(f"⚠️ 資料解析錯誤：{e}")
