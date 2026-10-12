"""AI 챗봇: 데이터 요약을 시스템 프롬프트에 주입(컨텍스트 주입)하고 GPT를 호출한 뒤 대화를 자동 저장한다.

흐름
  1) 데이터 요약 조회 (GET /api/data/summary 와 같은 함수)
  2) 요약을 시스템 프롬프트에 삽입
  3) GPT 호출 (필요하면 도구 호출 -> 결과 전달 -> 재호출, 최대 MAX_TOOL_ROUNDS 회)
  4) 질문/답변을 conversations 컬렉션에 저장
"""
import json

from app.core.errors import ExternalServiceError
from app.repositories.base import ConversationRepository, DataRepository
from app.schemas.data import today_kst
from app.services import conversation_service, data_service, summary_service
from app.services.tools import TOOLS, run_tool

HISTORY_LIMIT = 10      # 이어지는 대화에서 GPT에 함께 보낼 이전 메시지 수 (토큰 절약)
MAX_TOOL_ROUNDS = 3

SYSTEM_PROMPT = """당신은 사용자의 시계열 데이터를 분석해 주는 데이터 분석 비서입니다.
오늘 날짜: {today}

[사용자 데이터 요약]
{summary}

규칙
- 위 데이터를 근거로 구체적인 숫자(날짜, 값, 변화율)를 들어 한국어로 간결하게 답하세요.
- 요약에 없는 특정 날짜/기간 값이나 이동평균·변동성이 필요하면 제공된 도구를 호출하세요.
- 데이터에 없는 내용은 추측하지 말고 "데이터에 없다"고 말하세요. 투자 권유는 하지 마세요.
- 값의 단위는 '원'(1달러당 원화)입니다."""


def build_system_prompt(summary: dict) -> str:
    return SYSTEM_PROMPT.format(today=today_kst().isoformat(),
                                summary=summary_service.summary_to_prompt(summary))


def chat(message: str, conversation_id: str | None, data_repo: DataRepository,
         conv_repo: ConversationRepository, llm) -> dict:
    # 이어지는 대화라면 먼저 존재 여부를 확인 (없으면 404, GPT 비용 발생 전)
    history = []
    if conversation_id:
        conv = conversation_service.get(conv_repo, conversation_id)
        history = [{"role": m["role"], "content": m["content"]} for m in conv["messages"][-HISTORY_LIMIT:]]

    # 1) 요약 조회  2) 시스템 프롬프트 주입
    summary = summary_service.build_summary(data_service.get_all_rows(data_repo))
    messages = [{"role": "system", "content": build_system_prompt(summary)},
                *history, {"role": "user", "content": message}]

    # 3) GPT 호출 + 도구 호출 루프
    tool_log = []
    reply = None
    for _ in range(MAX_TOOL_ROUNDS + 1):
        msg = llm.complete(messages, TOOLS)
        if not msg.tool_calls:
            reply = (msg.content or "").strip()
            break
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_log.append({"name": tc.function.name, "arguments": args})
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": run_tool(tc.function.name, args, data_repo, conv_repo)})
    if not reply:
        raise ExternalServiceError("AI가 답변을 생성하지 못했습니다. 다시 시도해 주세요.")

    # 4) 대화 자동 저장
    new_messages = [{"role": "user", "content": message}, {"role": "assistant", "content": reply}]
    if conversation_id:
        conversation_service.append(conv_repo, conversation_id, new_messages)
    else:
        conversation_id = conversation_service.create(conv_repo, new_messages)["id"]

    return {"conversation_id": conversation_id, "reply": reply,
            "tool_calls": tool_log, "summary_period": summary["period"]}
