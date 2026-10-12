"""대화 기록 저장/조회 로직."""
from typing import Optional

from app.core.errors import NotFoundError
from app.repositories.base import ConversationRepository
from app.services.data_service import now_iso


def _title_from(messages: list[dict]) -> str:
    first = next((m["content"] for m in messages if m["role"] == "user"), "새 대화")
    return first if len(first) <= 30 else first[:30] + "…"


def _meta_fields(messages: list[dict]) -> dict:
    return {"message_count": len(messages),
            "last_message": messages[-1]["content"][:80] if messages else ""}


def _stamp(messages: list[dict]) -> list[dict]:
    ts = now_iso()
    return [{**m, "created_at": m.get("created_at") or ts} for m in messages]


def create(repo: ConversationRepository, messages: list[dict], title: Optional[str] = None) -> dict:
    ts = now_iso()
    messages = _stamp(messages)
    return repo.create({"title": title or _title_from(messages), "messages": messages,
                        **_meta_fields(messages), "created_at": ts, "updated_at": ts})


def append(repo: ConversationRepository, conv_id: str, new_messages: list[dict]) -> dict:
    conv = get(repo, conv_id)
    messages = conv["messages"] + _stamp(new_messages)
    return repo.update(conv_id, {"messages": messages, **_meta_fields(messages),
                                 "updated_at": now_iso()})


def list_meta(repo: ConversationRepository, limit: int) -> list[dict]:
    return repo.list_meta(limit)


def get(repo: ConversationRepository, conv_id: str) -> dict:
    conv = repo.get(conv_id)
    if conv is None:
        raise NotFoundError(f"대화 {conv_id} 를 찾을 수 없습니다.")
    return conv


def delete(repo: ConversationRepository, conv_id: str) -> None:
    if not repo.delete(conv_id):
        raise NotFoundError(f"대화 {conv_id} 를 찾을 수 없습니다.")
