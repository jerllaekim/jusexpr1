import json
import streamlit as st
from google import genai
from google.genai import types
from google.oauth2 import service_account

# ====================================================================
# 0. 스트림릿 기본 UI 페이지 설정
# ====================================================================
st.set_page_config(page_title="한-러 법률 번역 실험실", page_icon="🧪", layout="wide")
st.title("🧪 한-러 법률 및 해석례 번역 실험실")
st.caption("30만 문장 파인튜닝이 완료된 Gemini 3 Flash 모델의 번역 성능을 직접 테스트하는 샌드박스입니다.")

# ====================================================================
# 1. 친구분 GCP 계정 기반 백엔드 인증 처리 (Secrets 로드)
# ====================================================================
try:
    # 스트림릿이 TOML을 해석해 자동 생성한 AttrDict 객체를 그대로 활용 (json.loads 제거)
    gcp_account_info = st.secrets["gcp_service_account"]
    
    credentials = service_account.Credentials.from_service_account_info(
        gcp_account_info
    ).with_scopes(["https://www.googleapis.com/auth/cloud-platform"])
    
except Exception as e:
    st.error(f"❌ 백엔드 환경 설정(Secrets) 로드 실패: {e}")
    st.stop()

# ====================================================================
# 2. 족보 일치 핵심 변수 정의 (친구 프로젝트 ID 및 튜닝 모델 ID 매칭)
# ====================================================================
PROJECT_ID = "groovy-design-496111-h1"     # 👈 친구분 GCP 프로젝트 ID 일치화
LOCATION = "us-central1"                   # Vertex AI 파인튜닝 기본 리전
MY_TUNED_MODEL = "groovy-design-496111-h1-5da41a59f7fc" # 👈 정래님의 30만 문장 찐 뇌 ID

# 구글 Vertex AI 클라이언트 초기화 
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
# 3. 파인튜닝 모델 직접 호출 번역 함수
# ====================================================================
def predict_law_translation(law_title, law_context):
    # 정래님이 파인튜닝할 때 모델에 주입했던 가이드라인 프롬프트 구조 그대로 세팅
    prompt = f"""
    당신은 대한민국 관세 및 법률 전문가이자 최고의 번역가입니다.
    다음 [제공된 대한민국 법률 및 해석례 정보]를 정밀히 분석하고, 정래님의 파인튜닝 가이드라인 스타일에 맞춰 이 내용의 요약 정보와 가이드를 정확한 러시아어(Russian)로 변환하여 출력하세요.

    [대상 안건/법령명]: {law_title}
    [제공된 대한민국 법률 및 해석례 정보]:
    {law_context}
    """
    try:
        # 일반 gemini-2.5-flash 대신 30만 문장으로 구운 우리 튜닝 모델 ID 조준
        response = client.models.generate_content(
            model=MY_TUNED_MODEL,  
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        return response.text
    except Exception as e:
        return f"❌ 구글 튜닝 모델 호출 실패: {e}"

# ====================================================================
# 4. 사용자 UI 및 텍스트 마이닝 입력창 생성
# ====================================================================
st.write("---")
st.write("### 🔍 테스트할 법률 안건 및 본문 입력")

col_in1, col_in2 = st.columns([1, 2])

with col_in1:
    input_title = st.text_input(
        "⚖️ 안건명 또는 법령명 입력", 
        value="고용노동부 법령해석 안건 테스트",
        placeholder="예: 채용시 건강진단 비용 관련 질의"
    )

with col_in2:
    input_context = st.text_area(
        "📂 법률 본문 또는 질의/회답 내용 입력 (Fact)",
        value="[질의요지]\n06.1.1 이후 채용 시 건강진단 비용을 산업안전보건관리비로 사용할 수 있는지 여부\n\n[회답]\n산업안전보건법 제30조 및 동법 시행령에 의거하여, 근로자의 건강관리를 위한 비용은 소관 규격에 따라 산정될 수 있으나 채용 시 건강진단 비용은 사업주가 전액 부담해야 하는 법적 의무 사항이므로...",
        height=200,
        placeholder="학습 데이터셋에 포함되지 않았던 찐 고용노동부 회답 문장을 복사해서 넣어보세요."
    )

st.write("---")

# ====================================================================
# 5. 번역 실행 트리거 및 결과 화면 매칭
# ====================================================================
if st.button("🚀 30만 문장 파인튜닝 모델 번역 가동", type="primary"):
    
    if not input_title.strip() or not input_context.strip():
        st.warning("⚠️ 안건명과 본문 내용을 모두 채워주셔야 프롬프팅이 완벽히 작동합니다.")
        st.stop()
        
    # 화면을 깔끔하게 데칼코마니 형태로 반반 분할
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("### 🇰🇷 입력된 한국어 팩트 원문")
        st.markdown(f"**⚖️ 대상 명칭:** {input_title}")
        st.info(input_context)
        
    with col2:
        st.success("### 🇷🇺 파인튜닝 모델 러시아어 가이드 출력")
        with st.spinner("🤖 정래님의 튜닝 모델(groovy-design-...)이 정밀 번역 중..."):
            translated_result = predict_law_translation(input_title, input_context)
        st.markdown(translated_result)
