import json
import random
import requests
import streamlit as st
from google import genai
from google.genai import types
from google.oauth2 import service_account

st.set_page_config(page_title="법률 번역 실험실", page_icon="🧪", layout="wide")
st.title("🧪 한-러 법률 번역 및 API 연동 실험실")
st.caption("버튼을 누르면 실시간 법제처 데이터를 가져와 파인튜닝 모델로 번역합니다.")

# ====================================================================
# 1. 백엔드 인증 일괄 처리 (Secrets 로드)
# ====================================================================
try:
    key_dict = json.loads(st.secrets["gcp_service_account"])
    credentials = service_account.Credentials.from_service_account_info(
        key_dict
    ).with_scopes(["https://www.googleapis.com/auth/cloud-platform"])
    
    DATA_GO_KR_KEY = st.secrets["data_go_kr_key"]
except Exception as e:
    st.error(f"❌ 백엔드 환경 설정(Secrets) 로드 실패: {e}")
    st.stop()

# ====================================================================
# 2. 구글 클라우드 환경 설정값 및 클라이언트 초기화
# ====================================================================
PROJECT_ID = "gen-lang-client-0036116601"
LOCATION = "us-central1"               
ENDPOINT_ID = "4166613057352499200"    

try:
    client = genai.Client(
        vertexai=True,              
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
            st.error(f"⚠️ API 서버 응답 오류 (Status: {response.status_code})")
            return None
            
        data = response.json()
        items_list = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
            
        if not items_list:
            st.warning("조회된 데이터가 없습니다.")
            return None
            
        # 20개 안건 목록 중 백엔드에서 무작위 1건 추출
        return random.choice(items_list)
    except Exception as e:
        st.error(f"⚠️ 법제처 API 통신 실패: {e}")
        return None

# ====================================================================
# 4. 파인튜닝 엔드포인트 호출 함수
# ====================================================================
def predict_law_translation(user_text, law_context):
    full_model_path = f"projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{ENDPOINT_ID}"
    
    prompt = f"""
    당신은 대한민국 관세 및 법률 전문가이자 최고의 번역가입니다.
    [법제처 API 실시간 참조 데이터]의 내용을 바탕으로, 사용자의 입력에 대해 정확한 러시아어(Russian) 번역 및 안내를 제공하세요.
    제공된 정보의 법적 의미를 왜곡하지 말고, 파인튜닝된 스타일 가이드에 맞춰 전문적인 어조로 답변하세요.

    [사용자 입력]: {user_text}
    [법제처 API 실시간 참조 데이터]:
    {law_context}
    """

    try:
        response = client.models.generate_content(
            model=full_model_path,  
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        return response.text
    except Exception as e:
        st.error(f"❌ 구글 튜닝 모델 호출 실패: {e}")
        return None

# ====================================================================
# 5. 실험실 UI 가동 (버튼 구조)
# ====================================================================
st.write("---")
st.write("### 🎲 무작위 데이터 추출 및 번역 테스트")
st.write("아래 버튼을 누르면 법제처 API에서 새로운 관세 해석례를 뽑아와 번역을 수행합니다.")

# 대망의 테스트 가동 버튼!
if st.button("🚀 법제처 데이터 랜덤 호출 및 러시아어 번역 시작", type="primary"):
    
    # 1단계: 데이터 가져오기
    with st.spinner("1. 법제처 API 실시간 노크 중..."):
        raw_item = get_random_law_from_public_api()
        
    if raw_item:
        # 알맹이 변수 정리
        title = raw_item.get("안건명", "제목 없음")
        question = raw_item.get("질의요지", "내용 없음")
        answer_text = raw_item.get("회답", "내용 없음")
        org_name = raw_item.get("해석기관명", "관세청")
        
        # 주입할 컨텍스트 조립
        law_context = f"[해석기관]: {org_name}\n[안건명]: {title}\n[질의요지]: {question}\n[회답]: {answer_text}"
        
        st.toast(f"📥 데이터 가져오기 성공: {title}", icon="✅")
        
        # 화면을 좌우 2분할(Column)해서 왼쪽엔 한국어 원문, 오른쪽엔 러시아어 번역 매칭
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("### 🇰🇷 법제처 원문 데이터 (입력 팩트)")
            st.markdown(f"**🏢 해석 기관:** {org_name}")
            st.markdown(f"**📌 안 건 명:** {title}")
            with st.expander("🔎 상세 질의요지 보기", expanded=True):
                st.write(question)
            with st.expander("📝 공식 회답 보기", expanded=True):
                st.write(answer_text)
                
        # 2단계: 튜닝 모델 찌르기
        with col2:
            st.success("### 🇷🇺 파인튜닝 Gemini 3 Flash 번역 결과")
            with st.spinner("2. 튜닝 엔드포인트에서 러시아어 문장 생성 중..."):
                # 버튼 기반 테스트이므로 사용자 입력 자리에 안건명을 대표로 주입
                translated_result = predict_law_translation(title, law_context)
                
            if translated_result:
                st.markdown(translated_result)
            else:
                st.error("러시아어 답변 추출 실패")
    else:
        st.error("법제처로부터 데이터를 가져오지 못했습니다.")
