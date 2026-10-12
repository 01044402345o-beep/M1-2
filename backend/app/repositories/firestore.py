"""Firestore 구현.

컬렉션 구조
- data/{autoId}          : { date: "YYYY-MM-DD", value: float, memo: str, created_at, updated_at }
- conversations/{autoId} : { title, messages: [{role, content, created_at}], message_count,
                             last_message, created_at, updated_at }
"""
from typing import Optional

from google.cloud.firestore_v1.base_query import FieldFilter

DATA = "data"
CONVERSATIONS = "conversations"
META_FIELDS = ["title", "message_count", "last_message", "created_at", "updated_at"]


def _to_dict(snap) -> dict:
    return {"id": snap.id, **snap.to_dict()}


class FirestoreDataRepository:
    def __init__(self, db):
        self.col = db.collection(DATA)

    def list(self, start=None, end=None, limit=None, desc=False):
        q = self.col
        if start:
            q = q.where(filter=FieldFilter("date", ">=", start))
        if end:
            q = q.where(filter=FieldFilter("date", "<=", end))
        q = q.order_by("date", direction="DESCENDING" if desc else "ASCENDING")
        if limit:
            q = q.limit(limit)
        return [_to_dict(s) for s in q.stream()]

    def get(self, item_id):
        snap = self.col.document(item_id).get()
        return _to_dict(snap) if snap.exists else None

    def find_by_date(self, date):
        snaps = list(self.col.where(filter=FieldFilter("date", "==", date)).limit(1).stream())
        return _to_dict(snaps[0]) if snaps else None

    def create(self, data):
        ref = self.col.document()
        ref.set(data)
        return {"id": ref.id, **data}

    def update(self, item_id, data):
        ref = self.col.document(item_id)
        if not ref.get().exists:
            return None
        ref.update(data)
        return _to_dict(ref.get())

    def delete(self, item_id):
        ref = self.col.document(item_id)
        if not ref.get().exists:
            return False
        ref.delete()
        return True


class FirestoreConversationRepository:
    def __init__(self, db):
        self.col = db.collection(CONVERSATIONS)

    def list_meta(self, limit=50):
        # 목록에서는 messages 필드를 읽지 않도록 select 로 필요한 필드만 가져온다.
        q = self.col.select(META_FIELDS).order_by("updated_at", direction="DESCENDING").limit(limit)
        return [_to_dict(s) for s in q.stream()]

    def get(self, conv_id):
        snap = self.col.document(conv_id).get()
        return _to_dict(snap) if snap.exists else None

    def create(self, data):
        ref = self.col.document()
        ref.set(data)
        return {"id": ref.id, **data}

    def update(self, conv_id, data):
        ref = self.col.document(conv_id)
        if not ref.get().exists:
            return None
        ref.update(data)
        return _to_dict(ref.get())

    def delete(self, conv_id):
        ref = self.col.document(conv_id)
        if not ref.get().exists:
            return False
        ref.delete()
        return True
