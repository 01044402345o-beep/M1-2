from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=8000)
    created_at: Optional[str] = None


class ConversationCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "환율 추세 질문",
                "messages": [
                    {"role": "user", "content": "요즘 환율 어때?"},
                    {"role": "assistant", "content": "최근 30영업일 평균이 1.2% 올랐어요."},
                ],
            }
        }
    )

    title: Optional[str] = Field(None, max_length=100, description="없으면 첫 질문으로 자동 생성")
    messages: list[Message] = Field(..., min_length=1, max_length=200)


class ConversationMeta(BaseModel):
    """목록 조회용. messages 는 포함하지 않는다(용량 절약) — 전체는 GET /api/conversations/{id}."""

    id: str
    title: str
    message_count: int
    last_message: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConversationDetail(ConversationMeta):
    messages: list[Message]


class ConversationList(BaseModel):
    count: int
    items: list[ConversationMeta]
