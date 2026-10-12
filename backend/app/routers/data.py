from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import get_data_repo
from app.schemas.data import DataCreate, DataItem, DataList, DataUpdate, Statistics, Summary
from app.services import data_service, summary_service

router = APIRouter(prefix="/api/data", tags=["data"])


# 주의: /summary, /statistics 는 /{item_id} 보다 먼저 선언해야 경로가 가로채이지 않는다.
@router.get("/summary", response_model=Summary, summary="데이터 요약 (프롬프트 주입용)")
def get_summary(repo=Depends(get_data_repo)):
    return summary_service.build_summary(data_service.get_all_rows(repo))


@router.get("/statistics", response_model=Statistics, summary="확장 통계 + 그래프용 시계열 (보너스)")
def get_statistics(repo=Depends(get_data_repo)):
    return summary_service.build_statistics(data_service.get_all_rows(repo))


@router.get("", response_model=DataList, summary="데이터 목록 조회")
def list_data(
    start: Optional[date] = Query(None, description="시작일 (YYYY-MM-DD)"),
    end: Optional[date] = Query(None, description="종료일 (YYYY-MM-DD)"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="최대 개수"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="날짜 정렬"),
    repo=Depends(get_data_repo),
):
    items = data_service.list_data(repo, start and start.isoformat(), end and end.isoformat(),
                                   limit, desc=(order == "desc"))
    return {"count": len(items), "items": items}


@router.post("", response_model=DataItem, status_code=status.HTTP_201_CREATED, summary="새 데이터 추가")
def create_data(body: DataCreate, repo=Depends(get_data_repo)):
    return data_service.create_data(repo, body)


@router.put("/{item_id}", response_model=DataItem, summary="데이터 수정")
def update_data(item_id: str, body: DataUpdate, repo=Depends(get_data_repo)):
    return data_service.update_data(repo, item_id, body)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="데이터 삭제")
def delete_data(item_id: str, repo=Depends(get_data_repo)):
    data_service.delete_data(repo, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
