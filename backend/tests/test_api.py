"""Firebase/OpenAI 키 없이 API 흐름을 검증한다 (메모리 저장소 + 가짜 LLM)."""
import csv
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_conversation_repo, get_data_repo
from app.repositories.memory import MemoryConversationRepository, MemoryDataRepository
from app.services import data_service
from app.services.llm import get_llm
from main import app

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "usd_krw.csv"


class FakeLLM:
    """첫 호출에서 get_data_by_range 도구를 요청하고, 두 번째 호출에서 답한다."""

    def __init__(self, use_tool=False):
        self.use_tool = use_tool
        self.calls = []

    def complete(self, messages, tools):
        self.calls.append(messages)
        if self.use_tool and not any(m["role"] == "tool" for m in messages):
            fn = SimpleNamespace(name="get_data_by_range",
                                 arguments='{"start_date": "2026-03-02", "end_date": "2026-03-06"}')
            return SimpleNamespace(content=None, tool_calls=[SimpleNamespace(id="call_1", function=fn)])
        return SimpleNamespace(content="최근 환율은 상승 추세예요.", tool_calls=None)


@pytest.fixture
def env():
    data_repo, conv_repo, llm = MemoryDataRepository(), MemoryConversationRepository(), FakeLLM()
    with CSV_PATH.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            data_repo.create({"date": r["date"], "value": float(r["value"]), "memo": ""})
    data_service.invalidate_cache()
    app.dependency_overrides[get_data_repo] = lambda: data_repo
    app.dependency_overrides[get_conversation_repo] = lambda: conv_repo
    app.dependency_overrides[get_llm] = lambda: llm
    yield SimpleNamespace(client=TestClient(app), data=data_repo, conv=conv_repo, llm=llm)
    app.dependency_overrides.clear()
    data_service.invalidate_cache()


def test_dataset_has_at_least_100_points(env):
    assert len(env.data.items) >= 100


def test_summary(env):
    r = env.client.get("/api/data/summary")
    assert r.status_code == 200
    s = r.json()
    assert s["count"] == len(env.data.items)
    assert " ~ " in s["period"]
    assert s["metrics"]["min"] <= s["metrics"]["average"] <= s["metrics"]["max"]
    assert s["trend_direction"] in {"up", "down", "flat"}
    assert len(s["recent"]) == 7


def test_statistics(env):
    r = env.client.get("/api/data/statistics")
    assert r.status_code == 200
    st = r.json()
    assert st["ma7"] and st["ma30"] and st["volatility"] is not None
    assert len(st["series"]) == st["count"]


def test_data_crud(env):
    c = env.client
    r = c.post("/api/data", json={"date": "2024-01-02", "value": 1300.5, "memo": " 테스트 "})
    assert r.status_code == 201
    item = r.json()
    assert item["memo"] == "테스트"

    # 중복 날짜 -> 409
    assert c.post("/api/data", json={"date": "2024-01-02", "value": 1301}).status_code == 409

    r = c.get("/api/data", params={"start": "2024-01-01", "end": "2024-01-31"})
    assert r.json()["count"] == 1

    r = c.put(f"/api/data/{item['id']}", json={"value": 1310})
    assert r.status_code == 200 and r.json()["value"] == 1310

    # 요약 캐시가 쓰기 후 갱신되는지
    assert c.get("/api/data/summary").json()["period"].startswith("2024-01-02")

    assert c.delete(f"/api/data/{item['id']}").status_code == 204
    assert c.delete(f"/api/data/{item['id']}").status_code == 404
    assert c.put("/api/data/nope", json={"value": 1310}).status_code == 404


@pytest.mark.parametrize("body", [
    {"date": "2024-13-01", "value": 1300},           # 잘못된 날짜
    {"date": "2024-01-02", "value": 14000},          # 범위 초과
    {"date": "2024-01-02", "value": "abc"},          # 숫자 아님
    {"date": "2999-01-01", "value": 1300},           # 미래 날짜
    {"date": "2024-01-02", "value": 1300, "memo": "x" * 201},
    {"value": 1300},                                 # 날짜 누락
])
def test_data_validation(env, body):
    assert env.client.post("/api/data", json=body).status_code == 422


def test_update_requires_a_field(env):
    item_id = next(iter(env.data.items))
    assert env.client.put(f"/api/data/{item_id}", json={}).status_code == 422


def test_conversations_crud(env):
    c = env.client
    r = c.post("/api/conversations", json={"messages": [
        {"role": "user", "content": "안녕"}, {"role": "assistant", "content": "안녕하세요"}]})
    assert r.status_code == 201
    conv = r.json()
    assert conv["title"] == "안녕" and conv["message_count"] == 2

    lst = c.get("/api/conversations").json()
    assert lst["count"] == 1 and "messages" not in lst["items"][0]

    detail = c.get(f"/api/conversations/{conv['id']}").json()
    assert [m["content"] for m in detail["messages"]] == ["안녕", "안녕하세요"]

    assert c.post("/api/conversations", json={"messages": [{"role": "system", "content": "x"}]}).status_code == 422
    assert c.delete(f"/api/conversations/{conv['id']}").status_code == 204
    assert c.get(f"/api/conversations/{conv['id']}").status_code == 404


def test_chat_injects_summary_and_saves(env):
    c = env.client
    r = c.post("/api/chat", json={"message": "요즘 환율 어때?"})
    assert r.status_code == 200
    body = r.json()
    system = env.llm.calls[0][0]
    assert system["role"] == "system" and "[사용자 데이터 요약]" in system["content"]
    assert body["summary_period"] in system["content"]

    # 자동 저장 확인
    conv = c.get(f"/api/conversations/{body['conversation_id']}").json()
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant"]

    # 이어서 대화: 이전 메시지가 함께 전달되고 같은 대화에 추가된다
    r = c.post("/api/chat", json={"message": "최고점은?", "conversation_id": body["conversation_id"]})
    assert r.json()["conversation_id"] == body["conversation_id"]
    assert [m["role"] for m in env.llm.calls[1]] == ["system", "user", "assistant", "user"]
    assert c.get(f"/api/conversations/{body['conversation_id']}").json()["message_count"] == 4


def test_chat_tool_calling(env):
    env.llm.use_tool = True
    r = env.client.post("/api/chat", json={"message": "3월 첫째 주 환율 알려줘"})
    assert r.status_code == 200
    assert r.json()["tool_calls"][0]["name"] == "get_data_by_range"
    tool_msg = next(m for m in env.llm.calls[1] if m["role"] == "tool")
    assert '"count": 5' in tool_msg["content"]


def test_chat_validation_and_unknown_conversation(env):
    assert env.client.post("/api/chat", json={"message": ""}).status_code == 422
    assert env.client.post("/api/chat", json={"message": "hi", "conversation_id": "nope"}).status_code == 404
    assert env.llm.calls == []  # 404 는 GPT 호출 전에 걸러진다


def test_missing_firebase_config_returns_503(monkeypatch):
    from app.core import firebase
    firebase.get_firestore.cache_clear()
    monkeypatch.setattr(firebase, "settings", SimpleNamespace(
        firebase_service_account_json="", firebase_service_account_path=""))
    app.dependency_overrides.clear()
    data_service.invalidate_cache()
    r = TestClient(app).get("/api/data/summary")
    assert r.status_code == 503 and r.json()["code"] == "db_not_configured"
