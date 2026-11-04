"""ABLE AI assistant: questions, meeting summaries and email-draft tool calls."""
import json
from openai import OpenAI

MODEL = "gpt-4o-mini"
ROLE = """당신은 김 대리의 개인 비서 '에이블'입니다.
김 대리의 질문에 한국어로 친절하고 정확하게 답변합니다.
회의 기록에 근거하여 핵심 내용과 결정 사항을 요약하고, 김 대리의 담당 업무·기한·관련자를 구체적으로 정리합니다.
배정된 업무가 없으면 '배정된 업무가 없습니다'라고 알립니다.
회의에 없는 사실은 지어내지 않습니다.
음성 답변에도 적합하도록 자연스럽고 명확한 문장으로 작성합니다.
"""

EMAIL_TOOL = [{
    "type": "function", "name": "send_email",
    "description": "사용자가 이메일 발송을 명시적으로 요청한 경우에만 이메일 초안을 준비합니다. 실제 발송은 사용자의 최종 확인 후 별도로 수행됩니다.",
    "parameters": {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "사용자가 명시적으로 제공한 수신자 이메일"},
            "subject": {"type": "string", "description": "이메일 제목"},
            "body": {"type": "string", "description": "회의 요약과 김 대리 업무를 포함하는 이메일 본문"}
        },
        "required": ["to", "subject", "body"],
        "additionalProperties": False
    }, "strict": True
}]


def ask_assistant(question: str, meeting_text: str = "") -> dict:
    """Return answer and optional un-sent email draft."""
    if not question.strip():
        raise ValueError("질문을 입력해 주세요.")
    prompt = f"[사용자 요청]\n{question.strip()}"
    if meeting_text.strip():
        prompt += f"\n\n[미팅 내용]\n{meeting_text}"
    prompt += "\n\n수신자 이메일 주소가 명확하지 않으면 이메일 도구를 호출하지 말고 수신자 주소를 물어보세요."

    client = OpenAI()
    response = client.responses.create(
        model=MODEL,
        input=[{"role": "system", "content": ROLE}, {"role": "user", "content": prompt}],
        tools=EMAIL_TOOL, tool_choice="auto"
    )
    calls = [item for item in response.output if item.type == "function_call" and item.name == "send_email"]
    if calls:
        draft = json.loads(calls[0].arguments)
        return {"answer": "이메일 초안을 준비했습니다. 수신자와 내용을 확인한 뒤 발송 버튼을 눌러 주세요.", "email_draft": draft}
    return {"answer": response.output_text, "email_draft": None}


def summarize_meeting(meeting_text: str) -> str:
    if not meeting_text.strip():
        raise ValueError("먼저 회의록을 업로드해 주세요.")
    return ask_assistant("회의 전체의 핵심 내용과 결정 사항을 요약하고 김 대리에게 배정된 업무, 기한, 관련자를 자세히 알려주세요.", meeting_text)["answer"]
