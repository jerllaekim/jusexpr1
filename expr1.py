import streamlit as st
import requests
import random
import json

# 1. 환경 설정 및 API Key 로드
st.set_page_config(page_title="한-러 법률 번역 실험실", layout="wide")
st.title("🧪 한-러 법률 및 해석례 번역 실험실")

# 2. 범용 모델(Gemini) API 호출 함수 (SDK 없이 직접 호출)
def call_gemini(prompt):
    api_key = st.secrets["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    else:
        st.error(f"API Error: {response.text}")
        return "답변을 생성할 수 없습니다."

# 3. Vertex AI 파인튜닝 모델 호출 함수
def call_finetune(title, ctx):
    # 서비스 계정으로 인증 토큰 생성
    from google.oauth2 import service_account
    
    info = {
        "type": st.secrets["GCP_TYPE"],
        "project_id": st.secrets["GCP_PROJECT_ID"],
        "private_key_id": st.secrets["GCP_PRIVATE_KEY_ID"],
        "private_key": st.secrets["GCP_PRIVATE_KEY"].replace('\\n', '\n'),
        "client_email": st.secrets["GCP_CLIENT_EMAIL"],
        "client_id": st.secrets["GCP_CLIENT_ID"],
        "token_uri": st.secrets["GCP_TOKEN_URI"]
    }
    creds = service_account.Credentials.from_service_account_info(info)
    auth_req = requests.Session()
    creds.refresh(google.auth.transport.requests.Request())
    
    url = "https://us-central1-aiplatform.googleapis.com/v1/projects/groovy-design-496111-h1/locations/us-central1/endpoints/36530724077043712:predict"
    headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}
    payload = {"instances": [{"content": f"안건:{title}\n본문:{ctx}"}]}
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()['predictions'][0]['content']
    return "번역 오류"

# 4. 데이터 로드
@st.cache_data
def get_data_from_github():
    urls = {
        "난민법": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/난민법.txt",
        "출입국관리법": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/출입국관리법.txt",
        "법령해석": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/법령해석.txt"
    }
    return {k: requests.get(v).text for k, v in urls.items() if requests.get(v).status_code == 200}

# 5. UI 구성
tab1, tab2, tab3 = st.tabs(["💬 질문하기", "✍️ 번역 연습", "🚀 파인튜닝 번역"])

with tab1:
    query = st.text_input("질문 입력")
    if st.button("질문 분석"):
        data = get_data_from_github()
        st.info(call_gemini(f"데이터: {str(data)[:5000]}\n질문: {query}"))

with tab2:
    data = get_data_from_github()
    sents = [s.strip() for s in " ".join(data.values()).split(".") if len(s) > 30]
    if st.button("문장 뽑기"): st.session_state.p_text = random.choice(sents)
    st.markdown(f"> **원문:** {st.session_state.get('p_text', '버튼 클릭')}")
    trans = st.text_area("러시아어 번역:")
    if st.button("피드백"):
        st.success(call_gemini(f"원문:{st.session_state.p_text}\n번역:{trans}\n평가하시오."))

with tab3:
    title = st.text_input("안건명")
    ctx = st.text_area("본문 입력")
    if st.button("실행"):
        st.markdown(call_finetune(title, ctx))
