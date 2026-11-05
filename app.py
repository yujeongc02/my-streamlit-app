"""호준님 비서 로직 + 개선된 일정/To-do 화면의 통합 진입점."""
import hashlib
import os

import streamlit as st
from openai import OpenAI

from app_state import initialize_state, reset_state, save_response
from assistant import ASSISTANT_BUILD, DEFAULT_SYS_ROLE
from audio_utils import text_to_speech
from calendar_ui_v2 import render_calendar, render_details, render_todos
from command_service import MissingInputError, run_command
from meeting_planner import analyze_meeting, add_schedule
from meeting_utils import update_meeting_file

st.set_page_config(page_title="ABLE | 에이블 업무 비서",page_icon="☁️",layout="wide",initial_sidebar_state="expanded")
initialize_state()

st.markdown('''<style>
  .stApp {background:linear-gradient(165deg,#f6fcfc 0%,#ffffff 44%,#fffaf6 100%);}
  [data-testid="stSidebar"] {background:linear-gradient(180deg,#e9faf7 0%,#f6f9fc 90%);}
  .st-key-able_hero {border:1px solid #dcefed;background:linear-gradient(110deg,#e4faf5,#f8fbff 58%,#fff3e6);
      border-radius:22px;padding:14px 22px;margin-bottom:14px;}
  .st-key-able_hero h1 {font-weight:800;letter-spacing:-.04em;color:#1d4547;}
  .stButton > button[kind="primary"] {background:#08b9ad;border-color:#08b9ad;}
  .stButton > button {border-radius:11px;}
  [data-testid="stMetric"] {background:#fff;border:1px solid #e5efef;border-radius:14px;padding:12px;}
</style>''',unsafe_allow_html=True)

# 호준님 파일의 사이드바·멀티턴 처리 방식을 유지합니다.
with st.sidebar:
    st.image('able_mascot.webp',width=180)
    st.header("☁️ 에이블")
    st.caption('언제든 곁에서 도와주는 AI 업무 비서')
    st.subheader("📥 회의록과 명령")
    uploaded_file=st.file_uploader("회의록 텍스트 파일 (.txt)",type=["txt"],key=f"meeting_file_{st.session_state.upload_version}")
    try:
        meeting_content=update_meeting_file(uploaded_file)
    except UnicodeDecodeError:
        meeting_content=""
        st.error("UTF-8 형식의 TXT 파일을 업로드해 주세요.")

    if uploaded_file is None:
        st.info("회의록을 올리면 요약과 일정·To-do 추천을 분석합니다.")
    elif meeting_content:
        st.caption(f"업로드: {uploaded_file.name}")
        with st.expander("회의록 본문 보기"):
            st.text_area("미팅 본문",meeting_content,height=180,disabled=True)
        file_key=hashlib.sha256(meeting_content.encode('utf-8')).hexdigest()
        if st.session_state.get('meeting_analysis_hash') != file_key:
            with st.spinner('회의록 분석 중...'):
                try:
                    analysis=analyze_meeting(OpenAI(),meeting_content)
                    st.session_state.meeting_analysis=analysis
                    st.session_state.meeting_summary=analysis.get('summary','')
                    st.session_state.meeting_questions=analysis.get('questions',[])
                    st.session_state.meeting_analysis_hash=file_key
                    # To-do는 사용자가 추천 목록에서 고르고, 날짜 확정 일정만 자동 등록합니다.
                    added_dates=[]
                    rejected=[]
                    for event in analysis.get('schedules',[]):
                        try:
                            if add_schedule(event['title'],event['date'],event.get('time',''),event.get('assignee',''),event.get('parent','')):
                                from datetime import date
                                added_dates.append(date.fromisoformat(event['date']))
                        except (ValueError,TypeError,KeyError):
                            rejected.append(event.get('title','제목 없음'))
                    if added_dates:
                        first=min(added_dates)
                        st.session_state.selected_date=first
                        st.session_state.calendar_year=first.year
                        st.session_state.calendar_month=first.month
                    st.session_state.meeting_questions += [f'날짜 확인 필요: {name}' for name in rejected]
                    # 업로드한 회의록에 대한 요약 음성을 한 번만 생성합니다.
                    try:
                        st.session_state.summary_audio_bytes=text_to_speech(OpenAI(),st.session_state.meeting_summary)
                        st.session_state.summary_audio_error=None
                    except Exception as audio_exc:
                        st.session_state.summary_audio_bytes=None
                        st.session_state.summary_audio_error=str(audio_exc)
                    st.session_state.summary_audio_hash=file_key
                    st.session_state.summary_autoplay_pending=True
                    st.success(f'분석 완료 · 일정 {len(added_dates)}건 자동 등록 · To-do는 추천 목록에서 선택하세요.')
                    if rejected:
                        st.warning(f'날짜를 확인할 수 없어 등록하지 않은 일정: {len(rejected)}건')
                except Exception as exc:
                    st.error(f'회의록 분석 오류: {exc}')

    st.divider()
    recipient_email=st.text_input("수신자 이메일 주소",value=os.getenv('RECIPIENT_EMAIL',''))
    with st.expander('에이블 페르소나 (프롬프트)'):
        sys_role=st.text_area('시스템 역할',value=DEFAULT_SYS_ROLE,height=220)
    if st.button('대화 및 일정 초기화',use_container_width=True):
        reset_state()
        st.session_state.meeting_analysis_hash=None
        st.rerun()
    # st.audio_input은 폼 밖에 두어 녹음 완료 후 확실히 갱신되게 합니다.
    text_query=st.text_input('텍스트 질문/명령',key='assistant_text_query')
    audio_query=st.audio_input('음성으로 질문하기',key='assistant_voice_query',sample_rate=16000)
    fallback_audio=st.file_uploader('녹음이 안 되면 오디오 파일로 질문하기',type=['wav','mp3','m4a','mp4','webm','ogg'],key='assistant_audio_upload',help='녹음 오류가 뜨면 휴대폰/Windows 녹음 파일을 올려 주세요.')
    audio_query=audio_query if audio_query is not None else fallback_audio
    submitted=st.button('실행하기',use_container_width=True,key='assistant_submit')

if submitted:
    if not text_query.strip() and audio_query is None:
        st.warning('텍스트 입력 또는 음성 녹음이 필요합니다.')
    else:
        with st.spinner('에이블이 처리 중입니다...'):
            try:
                result=run_command(OpenAI(),text_query,audio_query,meeting_content,sys_role,st.session_state.messages,recipient_email)
            except MissingInputError as exc:
                st.warning(str(exc))
            except Exception as exc:
                st.error(f'명령 실행 오류: {exc}')
            else:
                save_response(result.user_prompt,result.answer,result.audio_bytes)
                if audio_query is not None:
                    st.info(f'🎙️ 음성 인식 결과: {result.user_prompt}')
                if result.email_status:
                    if result.email_status.startswith('이메일 발송 완료'):
                        st.success(result.email_status)
                    else:
                        st.error(result.email_status)
                if result.audio_error:
                    st.warning(f'음성 응답 생성 오류: {result.audio_error}')

with st.container(key='able_hero'):
    hero_image,hero_text=st.columns([1,4],vertical_alignment='center')
    with hero_image:
        st.image('able_mascot.webp',width=170)
    with hero_text:
        st.title('ABLE · 나만의 업무 비서')
        st.caption('회의는 똑똑하게 정리하고, 오늘의 일정은 산뜻하게 관리해요. ☁️')

# 왼쪽 사이드바 / 가운데 넓은 영역 / 오른쪽 좁은 영역
main,right=st.columns([3.6,1.15],gap='large')
with main:
    render_calendar()
    st.divider()
    render_details()
with right:
    st.subheader('📋 회의 요약')
    if st.session_state.meeting_summary:
        st.write(st.session_state.meeting_summary)
        if st.session_state.summary_audio_bytes:
            st.audio(st.session_state.summary_audio_bytes,format='audio/mp3',autoplay=st.session_state.summary_autoplay_pending)
            st.session_state.summary_autoplay_pending=False
        elif st.session_state.summary_audio_error:
            st.caption('음성 요약을 생성하지 못했습니다. 텍스트 요약은 정상 표시됩니다.')
    else:
        st.info('회의록을 업로드하면 요약이 바로 나타납니다.')
    st.divider()
    render_todos()

st.divider()
st.subheader('💬 에이블의 답변')
if st.session_state.audio_bytes:
    st.audio(st.session_state.audio_bytes,format='audio/mp3')
if st.session_state.messages:
    # 최신 질문과 답변 한 묶음이 맨 위로 오게 표시 순서만 뒤집습니다.
    turns=[st.session_state.messages[i:i+2] for i in range(0,len(st.session_state.messages),2)]
    for turn in reversed(turns):
      for message in turn:
        with st.chat_message(message['role']):
            st.write(message['content'])
else:
    st.info('사이드바에서 텍스트 또는 음성 명령을 실행하면 답변이 표시됩니다.')

st.caption('일정·To-do는 현재 접속 세션에만 유지되며 서버 재시작 후 사라질 수 있습니다.')
