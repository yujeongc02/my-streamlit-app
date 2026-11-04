"""Speech-to-text and text-to-speech helpers for Streamlit."""
from io import BytesIO
from openai import OpenAI


def speech_to_text(audio_bytes: bytes, filename: str = "recording.wav") -> str:
    audio = BytesIO(audio_bytes)
    audio.name = filename
    result = OpenAI().audio.transcriptions.create(
        model="gpt-4o-mini-transcribe", file=audio
    )
    return result.text


def text_to_speech(text: str) -> bytes:
    if not text.strip():
        raise ValueError("읽을 답변이 없습니다.")
    result = OpenAI().audio.speech.create(
        model="gpt-4o-mini-tts", voice="nova", input=text,
        response_format="mp3"
    )
    return result.content
