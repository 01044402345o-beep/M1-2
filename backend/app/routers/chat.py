from fastapi import APIRouter, Depends

from app.core.deps import get_conversation_repo, get_data_repo
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import chat_service
from app.services.llm import get_llm

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse,
             summary="AI 대화 (데이터 요약 주입 -> GPT 호출 -> 대화 자동 저장)")
def chat(body: ChatRequest, data_repo=Depends(get_data_repo),
         conv_repo=Depends(get_conversation_repo), llm=Depends(get_llm)):
    return chat_service.chat(body.message.strip(), body.conversation_id, data_repo, conv_repo, llm)
