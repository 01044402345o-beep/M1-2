"""OpenAI 호출 래퍼. 테스트에서는 같은 인터페이스의 가짜 객체로 교체한다."""
from openai import APIError, OpenAI, OpenAIError

from app.core.config import settings
from app.core.errors import ExternalServiceError


class OpenAILLM:
    def __init__(self):
        if not settings.openai_api_key:
            raise ExternalServiceError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        self.client = OpenAI(api_key=settings.openai_api_key, timeout=40, max_retries=1)

    def complete(self, messages: list[dict], tools: list[dict]):
        """assistant 메시지 객체(.content, .tool_calls)를 반환."""
        try:
            resp = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                tools=tools,
                # 비용 관리: 응답 토큰 상한
                max_completion_tokens=settings.openai_max_tokens,
            )
        except (APIError, OpenAIError) as e:
            raise ExternalServiceError(f"OpenAI API 호출 실패: {e}") from e
        return resp.choices[0].message


def get_llm():
    return OpenAILLM()
