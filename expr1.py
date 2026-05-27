import streamlit as st
import requests
import random
import os
import google.generativeai as genai_std
from google import genai as genai_vtx
from google.oauth2 import service_account

# 1. 인증 및 클라이언트 설정
@st.cache_resource(show_spinner=False)
def get_clients():
    # 파인튜닝 전용 (Vertex AI)
    gcp_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(gcp_info)
    vtx_client = genai_vtx.Client(vertexai=True, project="groovy-design-496111-h1", 
                                 location="us-central1", credentials=creds)
    
    # 일반 모델 전용 (API KEY)
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai_std.configure(api_key=api_key)
    
    return vtx_client

vtx_client = get_clients()

# 일반 모델 호출 함수 (매번 설정)
def call_gemini_std(prompt):
    model = genai_std.GenerativeModel('gemini-1.5-flash')
    return model.generate_content(prompt)

# 2. 데이터 로드
@st.cache_data
def get_data_from_github():
    urls = {
        "난민법": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/난민법.txt",
        "출입국관리법": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/출입국관리법.txt",
        "법령해석": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/법령해석.txt"
    }
    return {k: requests.get(v).text for k, v in urls.items() if requests.get(v).status_code == 200}

# 3. UI
st.set_page_config(page_title="한-러 법률 번역 실험실", layout="wide")
tab1, tab2, tab3 = st.tabs(["💬 질문하기", "✍️ 번역 연습", "🚀 파인튜닝 번역"])

with tab1:
    query = st.text_input("질문 입력")
    if st.button("답변받기"):
        data = get_data_from_github()
        res = call_gemini_std(f"데이터: {str(data)[:10000]}\n질문: {query}\n\n데이터를 기반으로 답변해.")
        st.info(res.text)

with tab2:
    data = get_data_from_github()
    sentences = [s.strip() for s in " ".join(data.values()).split(".") if len(s) > 30]
    if st.button("문장 뽑기"): st.session_state.p_text = random.choice(sentences)
    p_text = st.session_state.get("p_text", "버튼을 눌러주세요.")
    st.markdown(f"> **원문:** {p_text}")
    trans = st.text_area("번역 입력")
    if st.button("피드백 받기"):
        fb = call_gemini_std(f"원문:{p_text}\n번역:{trans}\n법률적 수정안을 제시하시오.")
        st.success(fb.text)

with tab3:
    title = st.text_input("안건명")
    ctx = st.text_area("본문")
    if st.button("번역 실행"):
        path = "projects/groovy-design-496111-h1/locations/us-central1/endpoints/36530724077043712"
        res = vtx_client.models.generate_content(model=path, contents=f"안건:{title}\n본문:{ctx}")
        st.markdown(res.text)
