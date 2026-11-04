"""Streamlit interface for ABLE meeting assistant."""
import streamlit as st
from assistant import ask_assistant, summarize_meeting
from audio_utils import speech_to_text, text_to_speech
from email_utils import send_email

st.set_page_config(page_title="에이블 | AI 개인비서", page_icon="🤖", layout="wide")
st.title("🤖 에이블 — 음성인식 AI 개인비서")
st.caption("회의록 요약 · 김 대리 담당 업무 · 음성 질문과 답변 · 이메일 발송")

for key, default in {"meeting_text": "", "answer": "", "transcript": "", "email_draft": None}.items():
    if key not in st.session_state:
        st.session_state[key] = default

uploaded_file = st.file_uploader("회의록 TXT 업로드", type=["txt"])
if uploaded_file is not None:
    try:
        text = uploaded_file.getvalue().decode("utf-8-sig")
        if text != st.session_state.meeting_text:
            st.session_state.meeting_text = text
            st.session_state.email_draft = None
        st.success("회의록을 불러왔습니다.")
    except UnicodeDecodeError:
        st.error("UTF-8로 저장한 TXT 파일을 올려 주세요.")

st.subheader("요청하기")
mode = st.radio("입력 방식", ["텍스트", "음성"], horizontal=True)
question = st.text_area("에이블에게 질문", placeholder="회의 내용을 요약하고 제 업무를 알려줘", key="typed_question") if mode == "텍스트" else ""
audio = st.audio_input("음성 지시 녹음") if mode == "음성" else None

col1, col2 = st.columns(2)
run = col1.button("질문 실행", type="primary", use_container_width=True)
summary = col2.button("회의록 요약", use_container_width=True)

if run or summary:
    st.session_state.email_draft = None
    try:
        if summary:
            with st.spinner("회의록을 요약하고 있습니다..."):
                st.session_state.answer = summarize_meeting(st.session_state.meeting_text)
        else:
            user_text = question
            if mode == "음성":
                if audio is None:
                    st.warning("먼저 음성을 녹음해 주세요.")
                    st.stop()
                with st.spinner("음성을 인식하고 있습니다..."):
                    user_text = speech_to_text(audio.getvalue())
                st.session_state.transcript = user_text
            with st.spinner("에이블이 답변을 준비하고 있습니다..."):
                result = ask_assistant(user_text, st.session_state.meeting_text)
            st.session_state.answer = result["answer"]
            st.session_state.email_draft = result["email_draft"]
    except Exception as exc:
        st.error(f"요청 처리 오류: {exc}")

if st.session_state.transcript:
    st.info(f"인식된 음성 지시: {st.session_state.transcript}")

if st.session_state.answer:
    st.subheader("에이블의 답변")
    st.write(st.session_state.answer)
    if st.button("🔊 답변 음성으로 듣기"):
        try:
            with st.spinner("음성을 생성하고 있습니다..."):
                sound = text_to_speech(st.session_state.answer)
            st.audio(sound, format="audio/mp3")
        except Exception as exc:
            st.error(f"음성 출력 오류: {exc}")

draft = st.session_state.email_draft
if draft:
    st.subheader("📧 이메일 발송 전 확인")
    with st.form("email_confirmation"):
        to = st.text_input("받는 사람", value=draft.get("to", ""))
        subject = st.text_input("제목", value=draft.get("subject", ""))
        body = st.text_area("본문", value=draft.get("body", ""), height=240)
        confirm = st.form_submit_button("확인 후 이메일 발송")
    if confirm:
        outcome = send_email(to, subject, body)
        if outcome["status"] == "success":
            st.success("이메일 발송 요청이 성공적으로 처리되었습니다.")
            st.session_state.email_draft = None
        else:
            st.error(f"발송 실패: {outcome['error']}")
