"""회의록 업로드 파일을 읽고 보관합니다. (S05 파일 업로드 예제 응용)"""

import streamlit as st
import hashlib


def update_meeting_file(uploaded_file) -> str:
    if uploaded_file is None:
        st.session_state.meeting_content = ""
        st.session_state.meeting_file_id = None
        st.session_state.meeting_analysis = None
        st.session_state.meeting_summary = ""
        st.session_state.meeting_analysis_hash = None
        return ""

    raw=uploaded_file.getvalue()
    # 이름이 같은 회의록을 다시 올려도 내용 변경을 정확히 감지합니다.
    file_id = hashlib.sha256(raw).hexdigest()
    if file_id != st.session_state.meeting_file_id:
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            st.session_state.meeting_content = ""
            st.session_state.meeting_file_id = None
            raise
        st.session_state.meeting_content = content
        st.session_state.meeting_file_id = file_id
        st.session_state.meeting_analysis = None
        st.session_state.meeting_summary = ""
        st.session_state.meeting_analysis_hash = None
    return st.session_state.meeting_content
