"""보너스: MCP Server — 배포된 백엔드 API를 Claude Desktop / Cursor 등 외부 MCP 클라이언트의 '도구'로 노출한다.

백엔드의 GPT Function Calling 과 같은 기능(요약, 기간 조회, 통계, 대화 조회)을 제공하므로
웹 프론트가 아닌 다른 채널에서도 같은 데이터를 근거로 대화할 수 있다.

실행:  API_BASE_URL=https://<render-app>.onrender.com python server.py   (stdio 전송)
"""
import os

import httpx
from mcp.server.mcpserver import MCPServer

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 75  # Render 무료 티어 콜드 스타트 고려

mcp = MCPServer("usd-krw-data")


def _get(path: str, params: dict | None = None):
    r = httpx.get(f"{API_BASE_URL}{path}", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def get_data_summary() -> dict:
    """원/달러 환율 데이터 전체 요약(기간, 개수, 평균/최고/최저, 추세, 월별 통계)을 조회한다."""
    return _get("/api/data/summary")


@mcp.tool()
def get_data_by_range(start_date: str, end_date: str) -> dict:
    """특정 기간(YYYY-MM-DD ~ YYYY-MM-DD)의 일별 환율 데이터를 조회한다."""
    return _get("/api/data", {"start": start_date, "end": end_date, "order": "asc", "limit": 120})


@mcp.tool()
def get_statistics() -> dict:
    """7일/30일 이동평균, 일간 변동성, 최대 상승/하락일, 전월 대비 변화율을 조회한다."""
    stats = _get("/api/data/statistics")
    stats.pop("series", None)  # 그래프용 시계열은 토큰 절약을 위해 제외
    return stats


@mcp.tool()
def list_conversations(limit: int = 10) -> dict:
    """웹 서비스에 저장된 이전 대화 목록(제목, 마지막 메시지)을 조회한다."""
    return _get("/api/conversations", {"limit": limit})


@mcp.tool()
def get_conversation(conversation_id: str) -> dict:
    """저장된 대화 하나의 전체 메시지를 조회한다."""
    return _get(f"/api/conversations/{conversation_id}")


if __name__ == "__main__":
    mcp.run()
