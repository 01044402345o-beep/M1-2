"""메모리 저장소 (테스트 전용)."""
import copy
import uuid


class MemoryDataRepository:
    def __init__(self):
        self.items: dict[str, dict] = {}

    def list(self, start=None, end=None, limit=None, desc=False):
        rows = [
            {"id": k, **copy.deepcopy(v)}
            for k, v in self.items.items()
            if (not start or v["date"] >= start) and (not end or v["date"] <= end)
        ]
        rows.sort(key=lambda r: r["date"], reverse=desc)
        return rows[:limit] if limit else rows

    def get(self, item_id):
        v = self.items.get(item_id)
        return {"id": item_id, **copy.deepcopy(v)} if v else None

    def find_by_date(self, date):
        return next((self.get(k) for k, v in self.items.items() if v["date"] == date), None)

    def create(self, data):
        item_id = uuid.uuid4().hex[:20]
        self.items[item_id] = copy.deepcopy(data)
        return {"id": item_id, **data}

    def update(self, item_id, data):
        if item_id not in self.items:
            return None
        self.items[item_id].update(copy.deepcopy(data))
        return self.get(item_id)

    def delete(self, item_id):
        return self.items.pop(item_id, None) is not None


class MemoryConversationRepository:
    def __init__(self):
        self.items: dict[str, dict] = {}

    def list_meta(self, limit=50):
        rows = [
            {"id": k, **{f: v.get(f) for f in ("title", "message_count", "last_message", "created_at", "updated_at")}}
            for k, v in self.items.items()
        ]
        rows.sort(key=lambda r: r["updated_at"] or "", reverse=True)
        return rows[:limit]

    def get(self, conv_id):
        v = self.items.get(conv_id)
        return {"id": conv_id, **copy.deepcopy(v)} if v else None

    def create(self, data):
        conv_id = uuid.uuid4().hex[:20]
        self.items[conv_id] = copy.deepcopy(data)
        return {"id": conv_id, **data}

    def update(self, conv_id, data):
        if conv_id not in self.items:
            return None
        self.items[conv_id].update(copy.deepcopy(data))
        return self.get(conv_id)

    def delete(self, conv_id):
        return self.items.pop(conv_id, None) is not None
