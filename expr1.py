import streamlit as st
import requests
import random
from google import genai
from google.genai import types
from google.oauth2 import service_account

# 1. 인증 설정 (검증된 방식)
st.set_page_config(page_title="한-러 법률 번역 실험실", layout="wide")

@st.cache_resource
def get_client():
    gcp_account_info = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(
        gcp_account_info
    ).with_scopes(["https://www.googleapis.com/auth/cloud-platform"])
    
    return genai.Client(
        vertexai=True, 
        project="groovy-design-496111-h1", 
        location="us-central1", 
        credentials=credentials
    )

client = get_client()
MODEL_PATH = "projects/groovy-design-496111-h1/locations/us-central1/endpoints/36530724077043712"

# 2. 통합 엔진 함수
def get_model_response(prompt):
    try:
        response = client.models.generate_content(
            model=MODEL_PATH,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        return response.text
    except Exception as e:
        return f"에러: {e}"

# 3. 데이터 로드 (일반 웹 호출)
@st.cache_data
def get_data_from_github():
    urls = {
        "난민법": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/난민법.txt",
        "출입국관리법": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/출입국관리법.txt",
        "법령해석": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/법령해석.txt"
    }
    return {k: requests.get(v).text for k, v in urls.items() if requests.get(v).status_code == 200}

# 4. UI 탭 구성
st.title("한-러 법률 번역 및 분석 샌드박스")
tab1, tab2, tab3 = st.tabs(["💬 법률 질문/분석", "✍️ 번역 연습", "🚀 파인튜닝 번역"])

with tab1:
    st.subheader("법률 질의응답")
    query = st.text_input("질문 입력", placeholder="법령 내용이나 해석에 대해 물어보세요.")
    if st.button("질문 분석"):
        data = get_data_from_github()
        prompt = f"데이터베이스 정보: {str(data)[:2000]}\n질문: {query}\n위 데이터를 바탕으로 법률 전문가로서 답변하시오, 위 데이터에서 알맞은 내용이 없으면 찾을 수 없다고 제시하세요."
        st.info(get_model_response(prompt))

with tab2:
    st.subheader("번역 연습")
    if st.button("연습할 문장 뽑기"):
        data = get_data_from_github()
        sentences = [s.strip() for s in " ".join(data.values()).split(".") if len(s) > 30]
        st.session_state.p_text = random.choice(sentences)
    
    p_text = st.session_state.get("p_text", "버튼을 눌러 문장을 불러오세요.")
    st.markdown(f"> **원문:** {p_text}")
    trans = st.text_area("당신의 번역:")
    if st.button("피드백 받기"):
        prompt = f"원문: {p_text}\n번역: {trans}\n법률적 관점에서 번역을 한국어 한문장, 러시아어 한문장으로 간결히 평가하고 올바른 번역안은 러시아어로 제시하시오."
        st.success(get_model_response(prompt))

with tab3:
    st.subheader("파인튜닝 번역 실행")
    title = st.text_input("안건명")
    ctx = st.text_area("번역할 본문")
    if st.button("번역 실행"):
        prompt = f"안건: {title}\n본문: {ctx}\n위 본문을 법률 용어에 맞게 러시아어로 번역하시오."
        st.markdown(get_model_response(prompt))
