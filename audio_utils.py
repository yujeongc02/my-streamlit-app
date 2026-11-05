# (출처: 6 - 미션 4. STT / 6 - 미션 5. TTS / 7 - 2. 음성 처리 로직)
from openai import OpenAI
from io import BytesIO
from pathlib import Path

def transcribe_audio(client: OpenAI, audio_file) -> str:
    """
    사용자의 음성 입력(audio_input 또는 오디오 파일)을 텍스트로 변환(STT)합니다.
    """
    # Streamlit UploadedFile/AudioInput은 여러 번 읽을 수 있도록 바이트를 복사합니다.
    data = audio_file.getvalue() if hasattr(audio_file, 'getvalue') else audio_file.read()
    if not data:
        raise ValueError('빈 녹음 파일입니다. 다시 녹음해 주세요.')
    buffered = BytesIO(data)
    filename = getattr(audio_file, 'name', '') or 'recording.wav'
    extension = Path(filename).suffix.lower()
    buffered.name = filename if extension in {'.wav','.mp3','.m4a','.mp4','.webm','.ogg','.oga','.flac','.mpeg','.mpga'} else 'recording.wav'
    transcript = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=buffered,
        language='ko',
    )
    return transcript.text

def text_to_speech(client: OpenAI, text: str) -> bytes:
    """
    LLM의 텍스트 응답을 음성 바이너리 데이터(MP3)로 변환(TTS)합니다.
    """
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text[:1000]  # 브라우저 재생 지연 방지를 위해 최대 1000자 제한
    )
    return response.content
