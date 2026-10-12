"""데이터 CRUD 비즈니스 로직 (중복 날짜 검사, 타임스탬프, 요약 캐시 무효화)."""
import time
from datetime import datetime, timezone
from typing import Optional

from app.core.errors import ConflictError, NotFoundError
from app.repositories.base import DataRepository
from app.schemas.data import DataCreate, DataUpdate

# 요약/챗봇은 전체 데이터를 자주 읽는다. Firestore 읽기 비용을 줄이기 위해
# 짧은 TTL 캐시를 두고, 쓰기(추가/수정/삭제)가 일어나면 즉시 비운다.
_CACHE_TTL = 60
_cache: dict = {"rows": None, "at": 0.0}


def invalidate_cache() -> None:
    _cache["rows"] = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_all_rows(repo: DataRepository) -> list[dict]:
    """날짜 오름차순 전체 데이터 (캐시 사용)."""
    if _cache["rows"] is None or time.time() - _cache["at"] > _CACHE_TTL:
        _cache["rows"] = repo.list()
        _cache["at"] = time.time()
    return _cache["rows"]


def list_data(repo: DataRepository, start: Optional[str], end: Optional[str],
              limit: Optional[int], desc: bool) -> list[dict]:
    return repo.list(start=start, end=end, limit=limit, desc=desc)


def create_data(repo: DataRepository, body: DataCreate) -> dict:
    date = body.date.isoformat()
    if repo.find_by_date(date):
        raise ConflictError(f"{date} 데이터가 이미 있습니다. 수정(PUT)을 사용하세요.")
    ts = now_iso()
    item = repo.create({"date": date, "value": body.value, "memo": body.memo,
                        "created_at": ts, "updated_at": ts})
    invalidate_cache()
    return item


def update_data(repo: DataRepository, item_id: str, body: DataUpdate) -> dict:
    changes = body.model_dump(exclude_none=True)
    if "date" in changes:
        changes["date"] = body.date.isoformat()
        dup = repo.find_by_date(changes["date"])
        if dup and dup["id"] != item_id:
            raise ConflictError(f"{changes['date']} 데이터가 이미 있습니다.")
    changes["updated_at"] = now_iso()
    item = repo.update(item_id, changes)
    if item is None:
        raise NotFoundError(f"데이터 {item_id} 를 찾을 수 없습니다.")
    invalidate_cache()
    return item


def delete_data(repo: DataRepository, item_id: str) -> None:
    if not repo.delete(item_id):
        raise NotFoundError(f"데이터 {item_id} 를 찾을 수 없습니다.")
    invalidate_cache()
