import json
import streamlit as st
from google.cloud import aiplatform
from google.oauth2 import service_account

st.set_page_config(page_title="한-러 법률 번역기 디버깅 모드", page_icon="⚖️")
st.title("⚖️ 한-러 법률 번역 AI (디버깅 모드)")

# ====================================================================
# 1. 스트림릿 세팅(Secrets) 및 오타 검증 단계
# ====================================================================
try:
    key_dict = json.loads(st.secrets["gcp_service_account"])
    credentials = service_account.Credentials.from_service_account_info(key_dict)
except Exception as e:
    st.error(f"❌ [Secrets 파일 오류] 스트림릿 세팅창에 JSON 키를 잘못 넣었거나 형식이 깨졌습니다: {e}")
    st.stop()

# 정보가 제대로 매칭되었는지 화면에 투명하게 출력 (보안상 민감한 key_id만 가림)
with st.sidebar.expander("🔍 현재 적용된 서비스 계정 정보 확인", expanded=False):
    st.write(f"**Project ID (JSON 내):** `{key_dict.get('project_id')}`")
    st.write(f"**Client Email:** `{key_dict.get('client_email')}`")

# ====================================================================
# 2. 정래님의 구글 클라우드 환경 설정값 입력
# ====================================================================
# ⚠️ 혹시 여기에 오타나 공백(스페이스바)이 들어가 있는지 꼭 확인하세요!
PROJECT_ID = "gen-lang-client-0036116601"
LOCATION = "us-central1"               # 👈 엔드포인트가 있는 지역 (us-central1 아니면 asia-northeast3)
ENDPOINT_ID = "4166613057352499200	"    # 👈 아까 찾으신 4로 시작하는 긴 숫자 키

with st.sidebar.expander("📍 환경 설정값 확인", expanded=True):
    st.write(f"**하드코딩된 PROJECT_ID:** `{PROJECT_ID}`")
    st.write(f"**LOCATION:** `{LOCATION}`")
    st.write(f"**ENDPOINT_ID:** `{ENDPOINT_ID}`")
    
    # JSON 파일 내부의 프로젝트 ID와 코드의 ID가 일치하는지 자동 검증
    if key_dict.get('project_id') != PROJECT_ID:
        st.error("⚠️ 경고: JSON 키 파일의 project_id와 코드에 적힌 PROJECT_ID가 서로 다릅니다! 오타를 확인하세요.")

# 구글 시스템 초기화
aiplatform.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

# ====================================================================
# 3. 모델 호출 함수 정의 (문법 최소화로 직렬화 에러 원천 차단)
# ====================================================================
def predict_law_translation(text):
    # 엔드포인트 풀 주소 찍어서 서랍장 찾아가기
    endpoint_full_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{ENDPOINT_ID}"
    endpoint = aiplatform.Endpoint(endpoint_name=endpoint_full_path)
    
    # 💥 에러 추적을 위한 디버깅 창 생성
    debug_box = st.empty()
    debug_box.info("🔄 구글 인프라에 데이터를 실어서 보내는 중...")

    # 가장 단순하고 날것(Raw) 그대로의 구조로 전송
    instances = [{"contents": [{"role": "user", "parts": [{"text": text}]}]}]
    
    try:
        # 이 단계에서 터지는지 감시
        response = endpoint.predict(instances=instances)
        debug_box.success("✅ 구글 서버가 데이터를 정상적으로 수신하고 답변을 보냈습니다!")
        
        # 구글이 돌려준 날것의 응답 구조를 화면에 그대로 찍어서 검사
        with st.expander("📦 구글 서버에서 넘어온 원본 데이터(Raw Response) 보기", expanded=False):
            st.json(response.predictions)
            
        # 첫 번째 결과 추출 시도
        return response.predictions[0]
        
    except Exception as e:
        debug_box.error("❌ 구글 API 서버 통신 단계에서 실패했습니다.")
        # 직렬화 에러 유발용 원인 분석문 출력
        st.error(f"**상세 에러 내용:** {e}")
        st.info("💡 만약 이 단계에서 에러가 났다면 `LOCATION`이 틀렸거나, 서비스 계정에 `Vertex AI User` 권한이 빠졌을 확률이 99%입니다.")
        return None

# ====================================================================
# 4. UI 및 챗봇 실행
# ====================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if user_input := st.chat_input("테스트할 문장을 입력하세요..."):
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("assistant"):
        answer = predict_law_translation(user_input)
        if answer:
            st.write(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
