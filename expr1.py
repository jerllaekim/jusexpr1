import streamlit as st
import requests
import random
import json
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# 1. 인증 설정 (Secrets에 있는 값을 직접 읽어옵니다)
gcp_info = st.secrets["gcp_service_account"]
creds = service_account.Credentials.from_service_account_info(gcp_info)
api_key = st.secrets["GEMINI_API_KEY"]

# 2. 데이터 로드
@st.cache_data
def get_data_from_github():
    urls = {
        "난민법": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/난민법.txt",
        "출입국관리법": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/출입국관리법.txt",
        "법령해석": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/법령해석.txt"
    }
    return {k: requests.get(v).text for k, v in urls.items() if requests.get(v).status_code == 200}

# 3. 직접 API 호출 함수 (SDK 충돌 방지용)
def call_gemini(prompt, is_finetune=False):
    if is_finetune:
        # 파인튜닝 모델 호출 (Vertex AI 직접 호출)
        auth_req = Request()
        creds.refresh(auth_req)
        token = creds.token
        url = "https://us-central1-aiplatform.googleapis.com/v1/projects/groovy-design-496111-h1/locations/us-central1/endpoints/36530724077043712:predict"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"instances": [{"content": prompt}]}
        response = requests.post(url, headers=headers, json=payload)
        return response.json()['predictions'][0]['content']
    else:
        # 일반 모델 호출 (Gemini API 직접 호출)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload)
        return response.json()['candidates'][0]['content']['parts'][0]['text']

# 4. UI
st.set_page_config(page_title="한-러 법률 번역 실험실", layout="wide")
tab1, tab2, tab3 = st.tabs(["💬 질문하기", "✍️ 번역 연습", "🚀 파인튜닝 번역"])

with tab1:
    query = st.text_input("질문 입력")
    if st.button("답변받기"):
        data = get_data_from_github()
        st.info(call_gemini(f"데이터:{str(data)[:10000]}\n질문:{query}\n데이터에서만 답해."))

with tab2:
    data = get_data_from_github()
    sentences = [s.strip() for s in " ".join(data.values()).split(".") if len(s) > 30]
    if st.button("문장 뽑기"): st.session_state.p_text = random.choice(sentences)
    p_text = st.session_state.get("p_text", "버튼을 누르세요.")
    st.markdown(f"> **원문:** {p_text}")
    trans = st.text_area("번역 입력")
    if st.button("피드백 받기"):
        st.success(call_gemini(f"원문:{p_text}\n번역:{trans}\n법률 전문가 관점에서 수정안 제시."))

with tab3:
    title = st.text_input("안건명")
    ctx = st.text_area("본문")
    if st.button("번역 실행"):
        st.markdown(call_gemini(f"안건:{title}\n본문:{ctx}", is_finetune=True))
