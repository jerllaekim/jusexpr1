import json
import streamlit as st
from google import genai
from google.genai import types
from google.oauth2 import service_account

st.set_page_config(page_title="한-러 법률 번역기", page_icon="⚖️")
st.title("⚖️ 한-러 법률 번역 AI 챗봇")

# ====================================================================
# 1. 서비스 계정 인증 (Streamlit Secrets)
# ====================================================================
try:
    key_dict = json.loads(st.secrets["gcp_service_account"])
    
    # [수정] 구글 클라우드 플랫폼 전체 권한 스코프를 명시해 줍니다. (invalid_scope 에러 해결)
    credentials = service_account.Credentials.from_service_account_info(
        key_dict
    ).with_scopes(["https://www.googleapis.com/auth/cloud-platform"])
    
except Exception as e:
    st.error(f"❌ [Secrets 파일 오류] JSON 키 형식을 확인하세요: {e}")
    st.stop()
# ====================================================================
# 2. 정래님의 구글 클라우드 환경 설정값
# ====================================================================
PROJECT_ID = "gen-lang-client-0036116601"
LOCATION = "us-central1"               
ENDPOINT_ID = "4166613057352499200"    

# [수정] No API key 에러를 방지하기 위해 Vertex AI 환경임을 명시하여 초기화합니다.
try:
    client = genai.Client(
        vertexai=True,              # 👈 Vertex AI 인프라를 사용하겠다고 명시
        project=PROJECT_ID,         # 👈 프로젝트 ID 명시
        location=LOCATION,          # 👈 지역 명시
        credentials=credentials     # 👈 다운로드받은 만능열쇠 주입
    )
except Exception as e:
    st.error(f"❌ 구글 클라이언트 초기화 실패: {e}")
    st.stop()

# ====================================================================
# 3. 모델 호출 함수 정의 (개인 엔드포인트 전용 풀 경로 적용)
# ====================================================================
def predict_law_translation(text):
    # [수정] 최신 SDK가 오해하지 않도록 프로젝트와 리전이 포함된 '풀 경로'를 완성합니다.
    full_model_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{ENDPOINT_ID}"
    
    try:
        response = client.models.generate_content(
            model=full_model_path,  # 👈 endpoints/... 대신 풀 경로 변수를 그대로 주입
            contents=text,
            config=types.GenerateContentConfig(
                temperature=0.2,
            ),
        )
        return response.text
    except Exception as e:
        st.error(f"❌ 구글 API 호출 실패: {e}")
        st.info("💡 만약 여기서 404가 또 뜬다면 LOCATION(리전)이 us-central1이 맞는지 콘솔에서 최종 확인해보셔야 합니다.")
        return None
# ====================================================================
# 4. 챗봇 UI 및 대화 처리
# ====================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if user_input := st.chat_input("법제처 등에서 가져온 한국어 법률 문장을 입력하세요..."):
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("assistant"):
        with st.spinner("파인튜닝된 Gemini 모델이 번역 중..."):
            answer = predict_law_translation(user_input)
            if answer:
                st.write(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
