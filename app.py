{\rtf1\ansi\ansicpg950\cocoartf2867
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww37860\viewh20540\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import json\
from datetime import datetime, timezone\
import streamlit as st\
\
DATA_FILE = "data/latest_report.json"\
\
st.set_page_config(page_title="\uc0\u36001 \u32147 AI\u24555 \u22577 ", page_icon="\u55357 \u56520 ", layout="wide")\
\
st.title("\uc0\u55357 \u56520  \u36001 \u32147 AI\u24555 \u22577 ")\
st.caption("\uc0\u27599 \u26085  06:00\u65288 \u21488 \u21271 \u65289 \u33258 \u21205 \u26356 \u26032 \u65372 Telegram \u25512 \u25773 \u21516 \u27493 \u65372 \u37325 \u22823 \u20107 \u20214 \u25490 \u24207 \u65372 \u21488 \u32929 \u24433 \u38911 \u21028 \u35712 \u65372 \u25237 \u36039 \u35264 \u23519 ")\
\
@st.cache_data(ttl=60)\
def load_report():\
    try:\
        with open(DATA_FILE, "r", encoding="utf-8") as f:\
            return json.load(f)\
    except FileNotFoundError:\
        return None\
    except json.JSONDecodeError:\
        return None\
\
data = load_report()\
\
if not data:\
    st.warning("\uc0\u23578 \u26410 \u29986 \u29983 \u20170 \u26085 \u22577 \u21578 \u65288 \u25110 \u27284 \u26696 \u35712 \u21462 \u22833 \u25943 \u65289 \u12290 \u35531 \u30906 \u35469  GitHub Actions \u25490 \u31243 \u26159 \u21542 \u24050 \u22519 \u34892 \u12290 ")\
    st.stop()\
\
updated_at_utc = data.get("updated_at_utc", "")\
title = data.get("title", "\uc0\u36001 \u32147 AI\u24555 \u22577 ")\
report = data.get("report", "")\
news = data.get("news", [])\
\
# \uc0\u39023 \u31034 \u26356 \u26032 \u26178 \u38291 \
try:\
    dt_utc = datetime.fromisoformat(updated_at_utc.replace("Z", "")).replace(tzinfo=timezone.utc)\
    st.info(f"\uc0\u26368 \u24460 \u26356 \u26032 \u65288 UTC\u65289 \u65306 \{dt_utc.strftime('%Y-%m-%d %H:%M')\}\u65372 \u65288 \u21488 \u21271 \u65289 \u32004  \{dt_utc.astimezone().strftime('%Y-%m-%d %H:%M')\}")\
except Exception:\
    st.info(f"\uc0\u26368 \u24460 \u26356 \u26032 \u65306 \{updated_at_utc\}")\
\
left, right = st.columns([1.25, 0.75], gap="large")\
\
with left:\
    st.subheader("\uc0\u55358 \u56800  AI \u24555 \u22577 ")\
    st.markdown(report)\
\
with right:\
    st.subheader("\uc0\u55357 \u56798 \u65039  \u26032 \u32862 \u20358 \u28304 ")\
    q = st.text_input("\uc0\u25628 \u23563 \u65288 \u27161 \u38988 /\u25688 \u35201 \u65289 ", placeholder="\u20363 \u22914 \u65306 Fed\u12289 CPI\u12289 \u21488 \u31309 \u38651 \u12289 AI\u12289 \u27833 \u20729 \'85")\
    if q:\
        ql = q.lower()\
        filtered = []\
        for n in news:\
            text = (n.get("title", "") + " " + n.get("summary", "")).lower()\
            if ql in text:\
                filtered.append(n)\
        news_show = filtered\
    else:\
        news_show = news\
\
    st.write(f"\uc0\u20849  \{len(news_show)\} \u21063 \u65288 \u36817  24 \u23567 \u26178 \u65289 ")\
\
    for n in news_show:\
        with st.container(border=True):\
            st.markdown(f"**\{n.get('title','')\}**")\
            dt = n.get("dt_utc", "")\
            if dt:\
                st.caption(f"\uc0\u26178 \u38291 \u65288 UTC\u65289 \u65306 \{dt\}")\
            link = n.get("link", "")\
            if link:\
                st.markdown(f"[\uc0\u38321 \u35712 \u21407 \u25991 ](\{link\})")\
            with st.expander("\uc0\u25688 \u35201 "):\
                st.write(n.get("summary", ""))}