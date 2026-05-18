import json
import streamlit as st
from google.cloud import aiplatform
from google.oauth2 import service_account
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value

# ====================================================================
# 1. 서비스 계정 JSON 키 인증 (Streamlit Secrets에서 가져옴)
# ====================================================================
try:
    # 이메일 ID가 아니라, 다운로드받은 JSON 파일 내용 전체를 사전 형태로 읽어옵니다.
    key_dict = json.loads(st.secrets["gcp_service_account"])
    credentials = service_account.Credentials.from_service_account_info(key_dict)
except Exception as e:
    st.error(f"⚠️ Secrets 인증 오류: {e}")
    st.stop()

# ====================================================================
# 2. 정래님이 확인한 구글 클라우드 정보 입력
# ====================================================================
PROJECT_ID = "gen-lang-client-0036116601"
LOCATION = "us-central1"               # 👈 [확인필요] 엔드포인트 화면에 적힌 지역명 입력
ENDPOINT_ID = "4166613057352499200"    # 👈 정래님이 찾으신 4로 시작하는 배포 키

# 인증 정보를 가지고 Vertex AI 시스템 초기화
aiplatform.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

# ====================================================================
# 3. 모델 호출 함수 정의
# ====================================================================
def predict_law_translation(text):
    # 4...번 엔드포인트 주소로 찾아갑니다.
    endpoint = aiplatform.Endpoint(
        endpoint_name=f"projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{ENDPOINT_ID}"
    )
    
    # [수정] 복잡한 Value() 포장 대신, 파이썬 기본 딕셔너리 구조로 직접 전달합니다.
    instances = [
        {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": text}]
                }
            ]
        }
    ]
    
    # 구글 서버에 예측 요청
    response = endpoint.predict(instances=instances)
    
    # [수정] 결과가 프로토콜 버퍼 형태로 돌아오므로 정석대로 첫 번째 답변의 텍스트를 추출합니다.
    # 일반적으로 Gemini 계열 엔드포인트는 predictions[0] 내에 대답 텍스트를 담아 보냅니다.
    try:
        # 응답 구조가 복잡할 경우를 대비해 안전하게 텍스트 추출 시도
        return response.predictions[0]['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, TypeError, IndexError):
        # 만약 구조가 단순화되어 들어오는 환경이라면 기존 방식대로 반환
        return response.predictions[0]
# ====================================================================
# 4. Streamlit 챗봇 UI 
# ====================================================================
st.set_page_config(page_title="한-러 법률 번역기", page_icon="⚖️")
st.title("⚖️ 한-러 법률 번역 AI 챗봇")

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
        with st.spinner("파인튜닝된 모델이 번역 중입니다..."):
            try:
                answer = predict_law_translation(user_input)
                st.write(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"호출 실패: {e}\n\n지역(LOCATION) 설정이나 서비스 계정 권한을 다시 확인해보세요.")
