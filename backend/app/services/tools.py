"""보너스: GPT Function Calling 도구 정의와 실행기.

요약은 항상 시스템 프롬프트에 주입되지만, 요약에 없는 세부 정보(특정 날짜/구간 값,
이동평균·변동성, 과거 대화)가 필요할 때 GPT가 스스로 아래 도구를 호출한다.
"""
import json
from datetime import date

from app.repositories.base import ConversationRepository, DataRepository
from app.services import conversation_service, data_service, summary_service

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_data_by_range",
            "description": "특정 날짜 또는 기간의 일별 환율 원본 데이터를 조회한다. "
                           "'3월 15일 환율', '지난주 값들'처럼 요약에 없는 구체적인 날짜가 필요할 때 사용.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "시작일 YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "종료일 YYYY-MM-DD (하루만 조회하면 start_date와 동일)"},
                },
                "required": ["start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_statistics",
            "description": "7일/30일 이동평균, 일간 변동성, 전일 대비 최대 상승·하락일, 전월 대비 변화율을 조회한다. "
                           "변동성, 이동평균, 급등/급락 질문에 사용.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_summary",
            "description": "전체 데이터 요약(기간, 개수, 평균/최고/최저, 추세, 월별 통계)을 최신 상태로 다시 조회한다. "
                           "사용자가 방금 데이터를 수정했다고 말하는 등 최신 요약이 필요할 때 사용.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_conversations",
            "description": "이전에 저장된 대화 목록(제목, 마지막 메시지)을 조회한다. '예전에 내가 뭘 물어봤지?' 같은 질문에 사용.",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "description": "최대 개수 (기본 5)"}},
            },
        },
    },
]

MAX_RANGE_ROWS = 120


def _valid_date(s: str) -> str:
    return date.fromisoformat(s).isoformat()


def run_tool(name: str, args: dict, data_repo: DataRepository,
             conv_repo: ConversationRepository) -> str:
    """도구를 실행하고 결과를 JSON 문자열로 돌려준다. 오류도 JSON으로 돌려 GPT가 스스로 수습하게 한다."""
    try:
        if name == "get_data_by_range":
            start, end = _valid_date(args["start_date"]), _valid_date(args["end_date"])
            rows = data_service.list_data(data_repo, start, end, MAX_RANGE_ROWS, desc=False)
            result = {
                "count": len(rows),
                "items": [{"date": r["date"], "value": r["value"], "memo": r.get("memo", "")} for r in rows],
                "note": "해당 기간에 데이터가 없습니다 (주말/공휴일은 고시 환율이 없음)." if not rows else "",
            }
        elif name == "get_statistics":
            stats = summary_service.build_statistics(data_service.get_all_rows(data_repo))
            stats.pop("series", None)
            result = stats
        elif name == "get_data_summary":
            result = summary_service.build_summary(data_service.get_all_rows(data_repo))
        elif name == "list_conversations":
            limit = max(1, min(int(args.get("limit", 5)), 20))
            result = conversation_service.list_meta(conv_repo, limit)
        else:
            result = {"error": f"알 수 없는 도구: {name}"}
    except (KeyError, ValueError, TypeError) as e:
        result = {"error": f"잘못된 인자: {e}"}
    return json.dumps(result, ensure_ascii=False, default=str)
