from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"message": "요즘 환율 추세가 어때?", "conversation_id": None}}
    )

    message: str = Field(..., min_length=1, max_length=1000, description="사용자 질문")
    conversation_id: Optional[str] = Field(None, description="이어서 대화할 대화 ID (없으면 새 대화)")


class ToolCallLog(BaseModel):
    name: str
    arguments: dict


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    tool_calls: list[ToolCallLog] = Field(default_factory=list, description="AI가 호출한 도구 기록")
    summary_period: str = Field(description="답변에 주입된 데이터 요약의 기간")
