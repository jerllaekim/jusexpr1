import streamlit as st
import requests
import random
import google.generativeai as genai_std
from google import genai as genai_vtx
from google.oauth2 import service_account

# 인증 설정
gcp_info = st.secrets["gcp_service_account"]
creds = service_account.Credentials.from_service_account_info(gcp_info)
vtx_client = genai_vtx.Client(vertexai=True, project="groovy-design-496111-h1", location="us-central1", credentials=creds)

genai_std.configure(api_key=st.secrets["GEMINI_API_KEY"])
model_std = genai_std.GenerativeModel('gemini-1.5-flash-latest') # 모델명 변경

@st.cache_data
def get_data_from_github():
    urls = {
        "난민법": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/난민법.txt",
        "출입국관리법": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/출입국관리법.txt",
        "법령해석": "https://raw.githubusercontent.com/jerllaekim/jusexpr1/main/data/법령해석.txt"
    }
    return {k: requests.get(v).text for k, v in urls.items() if requests.get(v).status_code == 200}

tab1, tab2, tab3 = st.tabs(["💬 질문하기", "✍️ 번역 연습", "🚀 파인튜닝 번역"])

with tab1:
    query = st.text_input("질문 입력")
    if st.button("답변받기"):
        data = get_data_from_github()
        # 개선된 컨텍스트 추출 로직 적용
        context = ""
        for name, text in data.items():
            p = f"질문: {query}\n데이터({name}): {text[:10000]}\n위 데이터에서 질문과 직접적으로 관련된 조문이나 해석례만 추출하여 띄어쓰기를 유지하며 답변해."
            res = model_std.generate_content(p)
            context += f"\n\n--- {name} ---\n{res.text}"
        st.info(context)

with tab2:
    data = get_data_from_github()
    # 띄어쓰기가 보존되도록 문장 단위 분할 개선
    all_sentences = [s.strip() for s in " ".join(data.values()).split(".") if len(s) > 30]
    if st.button("문장 뽑기"): st.session_state.p_text = random.choice(all_sentences)
    
    p_text = st.session_state.get("p_text", "")
    st.markdown(f"> **원문:** {p_text}")
    trans = st.text_area("번역 입력")
    if st.button("피드백 받기"):
        # 모델명 변경 반영
        fb = model_std.generate_content(f"원문:{p_text}\n번역:{trans}\n법률적 관점에서 피드백하시오.")
        st.success(fb.text)

with tab3:
    # 파인튜닝 모델은 기존대로 유지 (여기는 vertex_client가 담당)
    title = st.text_input("안건명")
    ctx = st.text_area("본문")
    if st.button("번역 실행"):
        path = "projects/groovy-design-496111-h1/locations/us-central1/endpoints/36530724077043712"
        res = vtx_client.models.generate_content(model=path, contents=f"안건:{title}\n본문:{ctx}")
        st.markdown(res.text)
