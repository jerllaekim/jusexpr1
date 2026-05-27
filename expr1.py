import streamlit as st
import requests
import random
import os
from google import genai as genai_vtx
import google.generativeai as genai_std
from google.oauth2 import service_account

# ====================================================================
# 1. 인증 및 클라이언트 호출 로직
# ====================================================================
@st.cache_resource(show_spinner=False)
def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
    return genai_std.configure(api_key=api_key) if api_key else None

# 파인튜닝 모델용 클라이언트 (Vertex AI)
@st.cache_resource(show_spinner=False)
def get_vertex_client():
    gcp_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(gcp_info)
    return genai_vtx.Client(vertexai=True, project="groovy-design-496111-h1", 
                            location="us-central1", credentials=creds)

# 클라이언트 호출
get_gemini_client()
vtx_client = get_vertex_client()
model_std = genai_std.GenerativeModel('gemini-1.5-flash')

# ====================================================================
# 2. 데이터 로드 (깃허브 연동)
# ====================================================================
@st.cache_data
def get_data_from_github():
    urls = {
        "난민법": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/난민법.txt",
        "출입국관리법": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/출입국관리법.txt",
        "법령해석": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/법령해석.txt"
    }
    return {k: requests.get(v).text for k, v in urls.items() if requests.get(v).status_code == 200}

# ====================================================================
# 3. UI 및 기능 구현
# ====================================================================
st.set_page_config(page_title="한-러 법률 번역 실험실", layout="wide")
st.title("🧪 한-러 법률 및 해석례 번역 실험실")

tab1, tab2, tab3 = st.tabs(["💬 질문하기", "✍️ 번역 연습", "🚀 파인튜닝 번역"])

with tab1: # RAG 질문
    query = st.text_input("질문 입력")
    if st.button("답변받기"):
        data = get_data_from_github()
        prompt = f"다음 데이터에서 질문에 대한 관련 조문/해석례를 3개 이내로 요약해줘.\n데이터: {str(data)[:10000]}\n질문: {query}"
        res = model_std.generate_content(prompt)
        st.info(res.text)

with tab2: # 번역 연습
    data = get_data_from_github()
    all_sentences = [s.strip() for s in " ".join(data.values()).split(".") if len(s) > 30]
    if st.button("문장 뽑기"): st.session_state.p_text = random.choice(all_sentences)
    
    p_text = st.session_state.get("p_text", "버튼을 눌러 문장을 불러오세요.")
    st.markdown(f"> **원문:** {p_text}")
    trans = st.text_area("러시아어 번역 입력:")
    
    if st.button("피드백 받기"):
        fb = model_std.generate_content(f"원문:{p_text}\n번역:{trans}\n법률 전문가 관점에서 수정안을 제시하시오.")
        st.success(fb.text)

with tab3: # 파인튜닝 모델
    title = st.text_input("안건명")
    ctx = st.text_area("본문")
    if st.button("번역 실행"):
        path = "projects/groovy-design-496111-h1/locations/us-central1/endpoints/36530724077043712"
        res = vtx_client.models.generate_content(model=path, contents=f"안건:{title}\n본문:{ctx}")
        st.markdown(res.text)
