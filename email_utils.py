"""SMTP email sending. No messages are sent on import."""
import os
import smtplib
from email.message import EmailMessage
from email.utils import parseaddr


def send_email(to: str, subject: str, body: str) -> dict:
    sender = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")
    address = parseaddr(to)[1]
    if not sender or not password:
        return {"status": "failed", "error": "GMAIL_ADDRESS 또는 GMAIL_APP_PASSWORD 설정이 없습니다."}
    if not address or "@" not in address or address != to.strip():
        return {"status": "failed", "error": "수신자 이메일 주소를 확인해 주세요."}
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = address
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(sender, password)
            smtp.send_message(msg)
        return {"status": "success"}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}
