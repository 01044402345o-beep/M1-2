from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import get_conversation_repo
from app.schemas.conversation import ConversationCreate, ConversationDetail, ConversationList
from app.services import conversation_service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationDetail, status_code=status.HTTP_201_CREATED,
             summary="대화 저장")
def create_conversation(body: ConversationCreate, repo=Depends(get_conversation_repo)):
    messages = [m.model_dump(exclude_none=True) for m in body.messages]
    return conversation_service.create(repo, messages, body.title)


@router.get("", response_model=ConversationList,
            summary="대화 목록 조회 (messages 미포함, 최근 수정순)")
def list_conversations(limit: int = Query(50, ge=1, le=200), repo=Depends(get_conversation_repo)):
    items = conversation_service.list_meta(repo, limit)
    return {"count": len(items), "items": items}


@router.get("/{conv_id}", response_model=ConversationDetail, summary="특정 대화 전체 messages 조회")
def get_conversation(conv_id: str, repo=Depends(get_conversation_repo)):
    return conversation_service.get(repo, conv_id)


@router.delete("/{conv_id}", status_code=status.HTTP_204_NO_CONTENT, summary="대화 삭제")
def delete_conversation(conv_id: str, repo=Depends(get_conversation_repo)):
    conversation_service.delete(repo, conv_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
