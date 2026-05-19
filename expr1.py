import json
import random
import requests
import streamlit as st
from google import genai
from google.genai import types
from google.oauth2 import service_account

st.set_page_config(page_title="한-러 법률 번역기", page_icon="⚖️")
st.title("⚖️ 실시간 법제처 연동 한-러 AI 챗봇 (튜닝 모델 버전)")

# ====================================================================
# 1. 백엔드 인증 일괄 처리 (구글 서비스 계정 & 법제처 호출키)
# ====================================================================
try:
    # [구글 인증] 스트림릿 Secrets에서 클라우드 키 로드
    key_dict = json.loads(st.secrets["gcp_service_account"])
    
    # 구글 클라우드 플랫폼 전체 권한 스코프 명시 (invalid_scope 에러 해결)
    credentials = service_account.Credentials.from_service_account_info(
        key_dict
    ).with_scopes(["https://www.googleapis.com/auth/cloud-platform"])
    
    # [법제처 인증] Secrets에서 법제처 API 호출키 로드
    DATA_GO_KR_KEY = st.secrets["data_go_kr_key"]
    
except Exception as e:
    st.error(f"❌ 백엔드 환경 설정(Secrets) 로드 실패: {e}")
    st.info("💡 스트림릿 대시보드의 Settings -> Secrets 설정을 확인하세요.")
    st.stop()

# ====================================================================
# 2. 구글 클라우드 환경 설정값 및 클라이언트 초기화
# ====================================================================
PROJECT_ID = "gen-lang-client-0036116601"
LOCATION = "us-central1"               
ENDPOINT_ID = "4166613057352499200"    # 👈 정래님의 파인튜닝 엔드포인트 ID

try:
    client = genai.Client(
        vertexai=True,              # Vertex AI 인프라 명시
        project=PROJECT_ID,         
        location=LOCATION,          
        credentials=credentials     
    )
except Exception as e:
    st.error(f"❌ 구글 클라이언트 초기화 실패: {e}")
    st.stop()

# ====================================================================
# 3. 법제처 API 실시간 랜덤 호출 함수
# ====================================================================
def get_random_law_from_public_api():
    url = "http://apis.data.go.kr/1220000/CgmExpcService/getCgmExpcList"
    params = {
        "serviceKey": DATA_GO_KR_KEY, 
        "pageNo": "1",                 
        "numOfRows": "20",             
        "_type": "json"                
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            st.error(f"⚠️ 법제처 API 호출 실패 (Status Code: {response.status_code})")
            return None
            
        data = response.json()
        
        try:
            items_list = data["response"]["body"]["items"]["item"]
        except KeyError:
            st.error(f"⚠️ API 응답 구조 매칭 실패. 원본 데이터: {data}")
            return None
            
        if not items_list:
            return None
            
        # 20개 안건 목록 중 백엔드에서 무작위 1건 초고속 선택
        selected_item = random.choice(items_list)
        
        title = selected_item.get("안건명", "제목 없음")
        question = selected_item.get("질의요지", "질의 내용 없음")
        answer_text = selected_item.get("회답", "회답 내용 없음")
        org_name = selected_item.get("해석기관명", "관세청")
        
        st.toast(f"🎲 실시간 팩트 매칭 성공: {title}")
        
        context = f"""
        [해석기관]: {org_name}
        [안건명]: {title}
        [질의요지]: {question}
        [회답]: {answer_text}
        """
        return context
        
    except Exception as e:
        st.error(f"⚠️ 법제처 API 통신 실패: {e}")
        return None

# ====================================================================
# 4. 파인튜닝 엔드포인트 호출 함수 (법제처 데이터 결합 프롬프트)
# ====================================================================
def predict_law_translation(user_text, law_context):
    full_model_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{ENDPOINT_ID}"
    
    # 법제처에서 긁어온 팩트가 있을 경우와 없을 경우를 나누어 프롬프트 구성
    if law_context:
        prompt = f"""
        당신은 대한민국 관세 및 법률 전문가이자 최고의 번역가입니다.
        [법제처 API 실시간 참조 데이터]의 내용을 바탕으로, 사용자의 입력에 대해 정확한 러시아어(Russian) 번역 및 안내를 제공하세요.
        제공된 정보의 법적 의미를 왜곡하지 말고, 파인튜닝된 스타일 가이드에 맞춰 전문적인 어조로 답변하세요.

        [사용자 입력]: {user_text}
        [법제처 API 실시간 참조 데이터]:
        {law_context}
        """
    else:
        # 혹시 법제처 API가 다운되었을 때를 대비한 기본 폴백(Fallback) 프롬프트
        prompt = user_text

    try:
        response = client.models.generate_content(
            model=full_model_path,  
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
            ),
        )
        return response.text
    except Exception as e:
        st.error(f"❌ 구글 API 호출 실패: {e}")
        st.info("💡 404 에러가 발생한다면 엔드포인트 ID가 유효한지 또는 삭제되지 않았는지 확인하세요.")
        return None

# ====================================================================
# 5. 챗봇 UI 및 대화 처리
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
        # 1단계: 백엔드에서 법제처 API 실시간 랜덤 호출
        with st.spinner("법제처 API에서 실시간 참조 데이터를 가져오는 중..."):
            fetched_law = get_random_law_from_public_api()
        
        # 2단계: 가져온 팩트 데이터와 유저 입력을 정래님의 파인튜닝 모델에 찔러넣음
        with st.spinner("파인튜닝된 Gemini 모델이 법령 기반 번역 중..."):
            answer = predict_law_translation(user_input, fetched_law)
            if answer:
                st.write(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
