# 💱 환율 AI 비서: 내 데이터를 아는 AI

일반적인 ChatGPT에게 "요즘 환율 어때?"라고 물으면 학습 시점의 일반론만 돌아옵니다.
이 서비스는 **내가 저장·관리하는 원/달러(USD/KRW) 일별 환율 데이터**를 분석해 요약을 만들고, 그 요약을 GPT의 **시스템 프롬프트에 주입**합니다. 그래서 AI가 *내 데이터의 숫자*를 근거로 답합니다.

> 사용자: "요즘 환율 추세가 어때?"
> AI: "최근 30영업일 평균은 1,355.63원으로, 직전 30영업일보다 4.82% 낮아요. 7월 1일 최고점(1,558.09원) 이후 하락세가 이어지고 있어요."

| 구분 | URL |
|---|---|
| 프론트엔드 (Vercel) | `https://<your-project>.vercel.app` ← 배포 후 기입 |
| 백엔드 API (Render) | `https://<your-service>.onrender.com` ← 배포 후 기입 |
| Swagger UI | `https://<your-service>.onrender.com/docs` |

> ⏳ Render 무료 티어는 15분 동안 요청이 없으면 잠듭니다. 첫 접속은 최대 1분 정도 걸릴 수 있습니다. 프론트는 접속하자마자 `/health`를 호출해 서버를 깨우고, 4초 넘게 응답이 없으면 "서버를 깨우는 중" 배너를 띄웁니다.

---

## 주요 기능

| 기능 | 내용 |
|---|---|
| **데이터 기반 AI 채팅** | 질문 → 데이터 요약을 시스템 프롬프트에 주입 → GPT 답변. 로딩 표시와 추천 질문 칩 제공. 대화는 자동 저장 |
| **데이터 관리 (CRUD)** | `(date, value, memo)` 추가/수정/삭제, 기간 필터, 전일 대비 표시, 저장 결과 메시지 |
| **대화 기록** | 목록 조회, 불러오기(이어서 대화 가능), 삭제 |
| **데이터 요약** | 기간, 개수, 최근값, 평균, 최고/최저, 표준편차, 추세(상승/하락/보합) 카드 |
| ⭐ 보너스: 시각화 | Chart.js로 일별 값과 7일/30일 이동평균 그래프 |
| ⭐ 보너스: 추가 지표 | `/api/data/statistics`: 이동평균, 일간 변동성, 최대 상승/하락일, 전월 대비 변화율 |
| ⭐ 보너스: 내보내기 | CSV(엑셀 한글 호환 BOM 포함) / JSON 다운로드 |
| ⭐ 보너스: 다크 모드 | 토글 + OS 설정 자동 반영, 선택값 저장 |
| ⭐ 보너스: Function Calling | GPT가 필요할 때 `get_data_by_range` 등 4개 도구를 스스로 호출 |
| ⭐ 보너스: MCP Server | 같은 기능을 Claude Desktop 같은 외부 MCP 클라이언트에서 도구로 사용 |

## 기술 스택

| 영역 | 기술 |
|---|---|
| Backend | Python 3.12, **FastAPI**, Uvicorn, **Pydantic v2** |
| Database | **Firebase Firestore** (`firebase-admin`) |
| AI | **OpenAI Chat Completions API** (기본 `gpt-4o-mini`), Function Calling |
| Frontend | **HTML / CSS / Vanilla JavaScript** (프레임워크 없음), Chart.js (CDN) |
| 배포 | **Render** (백엔드), **Vercel** (프론트엔드) |
| 기타 | MCP Python SDK (보너스), pytest |

## 데이터

- **주제**: 원/달러 환율 (1달러당 원화, 일별)
- **출처**: [Frankfurter API](https://frankfurter.dev): 유럽중앙은행(ECB) 기준환율, 영업일 기준
- **기간 / 개수**: 2025-10-01 ~ 2026-10-09, **262개** (`backend/data/usd_krw.csv`)
- 수집 스크립트: `python scripts/fetch_data.py --start 2025-10-01 --end 2026-10-09`

### 분석 → 요약 흐름

```
CSV 수집 ─▶ Firestore(data) 저장 ─▶ 전체 조회(날짜 오름차순, 60초 캐시)
                                        │
                     ┌──────────────────┴──────────────────┐
              build_summary()                      build_statistics()
   기간·개수·평균·최고/최저·표준편차          이동평균(7/30일)·변동성·최대 상승/하락
   추세(최근 30 vs 직전 30 영업일 평균)        전월 대비 변화율·그래프용 시계열
   월별 통계·최근 7개                                  │
              │                                 GET /api/data/statistics
   GET /api/data/summary ──▶ 시스템 프롬프트 주입 ──▶ GPT
```

- **추세 판정**: 최근 30영업일 평균과 직전 30영업일 평균의 변화율이 +0.5% 이상이면 "상승", -0.5% 이하이면 "하락", 그 사이면 "보합"입니다.
- 데이터가 추가/수정/삭제되면 캐시를 즉시 비워서, 다음 요약과 채팅에 바로 반영됩니다.

#### 요약 API 응답 예시 (`GET /api/data/summary`, 일부)

```json
{
  "label": "원/달러 환율 (USD/KRW, 원)",
  "period": "2025-10-01 ~ 2026-10-09",
  "count": 262,
  "metrics": {
    "average": 1455.25, "max": 1558.09, "max_date": "2026-07-01",
    "min": 1336.2, "min_date": "2026-09-09", "latest": 1341.49, "latest_date": "2026-10-09",
    "first": 1405.25, "change": -63.76, "change_pct": -4.54, "std": 50.36
  },
  "trend": "하락 (최근 30영업일 평균 1,355.63, 직전 30영업일 평균 대비 -4.82%)",
  "trend_direction": "down",
  "recent": [ { "date": "2026-10-09", "value": 1341.49, "...": "..." } ],
  "monthly": [ { "month": "2026-09", "average": 1358.41, "max": 1388.1, "min": 1336.2, "count": 22 } ]
}
```

---

## 아키텍처

```
┌──────────── Vercel ────────────┐        ┌──────────────── Render ────────────────┐
│ index.html / style.css / app.js│  HTTPS │ FastAPI (main.py: CORS, 예외 처리)      │
│ config.js ← API_BASE_URL (빌드)│ ─────▶ │  routers/   HTTP 입출력·검증            │
└────────────────────────────────┘  CORS  │  services/  비즈니스 로직               │
                                          │  repositories/  Firestore 접근          │
┌── MCP 클라이언트 (보너스) ──┐            └──────┬─────────────────────┬────────────┘
│ Claude Desktop 등           │──▶ mcp_server ──▶ │ (REST)              │
└─────────────────────────────┘                   ▼                     ▼
                                          Firebase Firestore      OpenAI API
                                          data / conversations
```

### 폴더 구조

```
M1-2/
├── backend/
│   ├── main.py                    # 앱 초기화, CORS, 예외 핸들러, 라우터 등록, /health
│   ├── app/
│   │   ├── core/                  # config(환경변수), firebase(클라이언트), deps(DI), errors
│   │   ├── schemas/               # Pydantic 요청/응답 모델 (data, conversation, chat)
│   │   ├── routers/               # data.py, conversations.py, chat.py
│   │   ├── services/              # data / summary / conversation / chat / tools / llm
│   │   └── repositories/          # firestore.py(운영), memory.py(테스트), base.py(인터페이스)
│   ├── scripts/                   # fetch_data.py, seed.py, key_to_env.py
│   ├── data/usd_krw.csv           # 분석 데이터 262개
│   ├── tests/test_api.py          # API 테스트 16개 (키 없이 실행)
│   └── requirements.txt
├── frontend/                      # index.html, style.css, app.js, generate-config.js, vercel.json
├── mcp_server/server.py           # 보너스: MCP Server
├── render.yaml                    # Render Blueprint
└── README.md
```

### 계층을 나눈 기준

| 계층 | 책임 | 하지 않는 것 |
|---|---|---|
| `routers/` | URL, HTTP 메서드, 상태 코드, 요청 모델 바인딩, 의존성 주입 | 계산·DB 접근 |
| `services/` | 중복 날짜 검사, 요약/통계 계산, 프롬프트 구성, GPT 호출 루프, 대화 자동 저장 | HTTP 세부사항 |
| `repositories/` | Firestore 쿼리 (컬렉션·정렬·필터) | 비즈니스 규칙 |
| `schemas/` | Pydantic 입력 검증과 응답 형태 정의 (Swagger 문서 자동 생성) | 로직 |

라우터는 `Depends(get_data_repo)`로 저장소를 주입받습니다. 테스트에서는 `app.dependency_overrides`로 메모리 저장소와 가짜 LLM을 끼워 넣기 때문에, **Firebase/OpenAI 키 없이도 전체 API 흐름을 검증**할 수 있습니다.

---

## API

Swagger UI(`/docs`)에서 모든 엔드포인트를 직접 실행해 볼 수 있습니다.

### 데이터 (`data` 컬렉션)

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/data` | 새 데이터 추가 (같은 날짜가 있으면 409) |
| GET | `/api/data` | 목록 조회 (`start`, `end`, `limit`, `order=asc\|desc`) |
| PUT | `/api/data/{id}` | 수정 (보낸 필드만 부분 수정) |
| DELETE | `/api/data/{id}` | 삭제 (204) |
| GET | `/api/data/summary` | **데이터 요약 (프롬프트 주입용)** |
| GET | `/api/data/statistics` | ⭐ 확장 통계 + 그래프용 시계열 |

> `/summary`, `/statistics`는 `/{id}`보다 **먼저** 선언했습니다. 순서가 바뀌면 `"summary"`가 id로 해석됩니다.

### 대화 기록 (`conversations` 컬렉션)

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/conversations` | 대화 저장 (title 생략 시 첫 질문으로 자동 생성) |
| GET | `/api/conversations` | 목록 조회. **messages는 포함하지 않음** (id, title, message_count, last_message, 시각만) |
| GET | `/api/conversations/{id}` | **(A) 방식**: 특정 대화의 전체 messages 조회 → "불러오기" |
| DELETE | `/api/conversations/{id}` | 대화 삭제 |

### AI 채팅

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/chat` | `{ message, conversation_id? }` → `{ conversation_id, reply, tool_calls, summary_period }` |
| GET | `/health` | 헬스 체크 (콜드 스타트 깨우기) |

### Firestore 컬렉션 구조

```
data/{autoId}
  date: "2026-10-09"      # YYYY-MM-DD 문자열 (사전순 = 날짜순이라 범위 쿼리/정렬 가능)
  value: 1341.49
  memo: ""
  created_at, updated_at: ISO 8601 (UTC)

conversations/{autoId}
  title: "요즘 환율 추세가 어때?"
  messages: [ { role: "user"|"assistant", content, created_at }, ... ]
  message_count: 4         # 목록 조회 시 messages를 읽지 않도록 비정규화
  last_message: "..."
  created_at, updated_at
```

목록 API는 Firestore `select()`로 메타 필드만 읽습니다. 대화가 길어져도 목록 응답은 가볍게 유지됩니다.

### 입력 검증 (Pydantic)과 예외 처리

| 대상 | 규칙 | 실패 시 |
|---|---|---|
| `date` | 실제 존재하는 날짜(`2024-13-01` ✕), 미래 날짜 금지(KST 기준) | 422 |
| `value` | 숫자, 500 < value < 3000 (환율 오타 방지, 예: 14050) | 422 |
| `memo` | 최대 200자, 앞뒤 공백 제거 | 422 |
| PUT body | 최소 1개 필드 필요 | 422 |
| `message` (chat) | 1~1000자 | 422 |
| `messages[].role` | `user` / `assistant`만 허용 | 422 |
| 같은 날짜 중복 추가 | 서비스 계층에서 검사 | 409 |
| 없는 id | | 404 (GPT 호출 전에 차단해 비용 절약) |
| Firebase 키 미설정 | | 503 `db_not_configured` |
| OpenAI 오류/키 미설정 | | 502 `external_service_error` |
| 그 외 예외 | 내부 정보는 로그에만 남김 | 500 (상세 숨김) |

입력 검증을 Pydantic으로 한 이유: 타입 변환·검증·에러 메시지를 선언형으로 한곳에 모을 수 있고, 같은 모델이 Swagger 문서와 예시로도 쓰입니다. 잘못된 값은 서비스 로직이나 DB에 닿기 전에 막힙니다. 프론트는 422 응답의 `detail` 배열을 읽어 "value: Input should be less than 3000"처럼 필드별 메시지로 보여줍니다.

---

## 컨텍스트 주입 원리

GPT는 내 Firestore 데이터를 직접 볼 수 없습니다. 그래서 **매 요청마다** 서버가 데이터를 요약해 **시스템 프롬프트**에 텍스트로 넣어 줍니다. 모델 입장에서는 "이미 알고 있는 사실"이 되고, 답변이 그 숫자를 근거로 만들어집니다.

```
POST /api/chat
  1) build_summary(get_all_rows())          ← GET /api/data/summary 와 같은 함수
  2) SYSTEM_PROMPT.format(summary=...)      ← 요약 주입
  3) messages = [system, (이전 대화 최대 10개), user]
     GPT 호출 → tool_calls 있으면 도구 실행 → 결과를 role=tool 로 전달 → 재호출 (최대 3회)
  4) user/assistant 메시지를 conversations 에 자동 저장 (새 대화 생성 또는 기존 대화에 추가)
```

실제로 주입되는 시스템 프롬프트 (일부):

```
당신은 사용자의 시계열 데이터를 분석해 주는 데이터 분석 비서입니다.
오늘 날짜: 2026-10-12

[사용자 데이터 요약]
- 데이터 종류: 원/달러 환율 (USD/KRW, 원)
- 데이터 기간: 2025-10-01 ~ 2026-10-09
- 총 레코드: 262개
- 주요 지표: 평균 1,455.25, 최고 1,558.09(2026-07-01), 최저 1,336.20(2026-09-09), 최근 1,341.49(2026-10-09), 기간 변화 -63.76 (-4.54%), 표준편차 50.36
- 최근 트렌드: 하락 (최근 30영업일 평균 1,355.63, 직전 30영업일 평균 대비 -4.82%)
- 월별 통계:
  - 2026-06: 평균 1,530.14 / 최고 1,550.89 / 최저 1,508.64 (22일)
  - ...
- 최근 7개 데이터: ...

규칙
- 위 데이터를 근거로 구체적인 숫자(날짜, 값, 변화율)를 들어 한국어로 간결하게 답하세요.
- 요약에 없는 특정 날짜/기간 값이나 이동평균·변동성이 필요하면 제공된 도구를 호출하세요.
- 데이터에 없는 내용은 추측하지 말고 "데이터에 없다"고 말하세요. 투자 권유는 하지 마세요.
```

**전체 원본(262행)이 아니라 요약을 넣는 이유**: 토큰 비용과 응답 속도를 줄이고, 모델이 계산 실수를 하지 않도록 통계는 서버가 정확히 계산해서 넘깁니다. 요약에 없는 세부 값은 아래 도구 호출로 보완합니다.

---

## ⭐ 보너스: Function Calling + MCP

### 도구 목록과 호출 근거

| 도구 | 호출하는 경우 (GPT 판단 근거) | 내부 동작 |
|---|---|---|
| `get_data_by_range(start_date, end_date)` | "3월 첫째 주 환율", "10월 2일 값"처럼 **요약에 없는 특정 날짜/구간**을 물을 때 | `GET /api/data?start&end`와 같은 서비스 함수 |
| `get_statistics()` | **이동평균, 변동성, 급등/급락일** 질문 | `build_statistics()` (시계열 제외) |
| `get_data_summary()` | 사용자가 방금 데이터를 수정했다며 **최신 요약**을 요구할 때 | `build_summary()` |
| `list_conversations(limit)` | "예전에 내가 뭘 물어봤지?"처럼 **과거 대화**를 물을 때 | 대화 목록 조회 |

판단 근거는 도구의 `description`과 시스템 프롬프트의 규칙("요약에 없는 값이 필요하면 도구를 호출하라")입니다. 일반적인 추세 질문은 이미 주입된 요약으로 답할 수 있어서 도구를 호출하지 않습니다. 호출된 도구는 응답의 `tool_calls`에 기록되고, 채팅 화면에 `🔧 get_data_by_range` 태그로 표시됩니다.

### 호출 흐름 예시: "2026년 3월 첫째 주 환율 알려줘"

```
사용자 ─▶ POST /api/chat
            │ system(요약 주입) + user
            ▼
          GPT ── 요약엔 월별 값만 있음 → tool_call: get_data_by_range("2026-03-02","2026-03-06")
            │
          서버 ── run_tool() → Firestore 조회 → {"count":5,"items":[...]} 를 role=tool 로 전달
            ▼
          GPT ── 5일치 값을 근거로 최종 답변 생성
            │
          서버 ── conversations 에 저장 → { reply, tool_calls:[{name:"get_data_by_range",...}] }
```

### MCP Server (외부 채널)

`mcp_server/server.py`는 배포된 REST API를 감싸서 같은 기능(`get_data_summary`, `get_data_by_range`, `get_statistics`, `list_conversations`, `get_conversation`)을 **MCP 도구**로 노출합니다. Claude Desktop 같은 MCP 클라이언트에서 웹 프론트 없이도 같은 데이터로 대화할 수 있습니다.

```bash
cd mcp_server
pip install -r requirements.txt
API_BASE_URL=https://<your-service>.onrender.com python server.py   # stdio
```

Claude Desktop 설정(`claude_desktop_config.json`) 예시:

```json
{
  "mcpServers": {
    "usd-krw-data": {
      "command": "python",
      "args": ["C:/path/to/M1-2/mcp_server/server.py"],
      "env": { "API_BASE_URL": "https://<your-service>.onrender.com" }
    }
  }
}
```

호출 흐름: `MCP 클라이언트 → (stdio) mcp_server → (HTTPS) Render FastAPI → Firestore`

---

## 로컬 실행 방법

### 0. 사전 준비

1. **Firebase**: [콘솔](https://console.firebase.google.com)에서 프로젝트 생성 → *Firestore Database* 만들기(프로덕션 모드, 리전 `asia-northeast3`) → *프로젝트 설정 > 서비스 계정 > 새 비공개 키 생성*으로 JSON 다운로드 → `backend/serviceAccountKey.json`으로 저장합니다. (`.gitignore`로 제외됨)
2. **OpenAI**: [API 키](https://platform.openai.com/api-keys) 발급. 결제 한도(Usage limits)를 낮게 설정해 두는 것을 권장합니다.

### 1. 백엔드

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   /   macOS·Linux: source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env            # 값 채우기 (OPENAI_API_KEY, FIREBASE_SERVICE_ACCOUNT_PATH)
python -m scripts.seed          # CSV 262개를 Firestore 'data' 컬렉션에 업로드 (중복 날짜 건너뜀)
uvicorn main:app --reload       # http://localhost:8000/docs
```

테스트 (키 없이 실행됨):

```bash
pytest -q        # 16 passed
```

### 2. 프론트엔드

```bash
cd frontend
node generate-config.js                     # (선택) API_BASE_URL=http://localhost:8000 이 기본값
python -m http.server 5500                  # http://localhost:5500
```

`ALLOWED_ORIGINS`에 `http://localhost:5500`이 포함되어 있어야 합니다(기본값에 포함).

---

## 배포

### 백엔드: Render

1. GitHub에 푸시 → Render *New > Blueprint* → 이 저장소 선택 (`render.yaml` 자동 인식).
   또는 *New > Web Service*로 직접 만듭니다: Root Directory `backend`, Build `pip install -r requirements.txt`, Start `uvicorn main:app --host 0.0.0.0 --port $PORT`.
2. 환경 변수 입력:
   - `OPENAI_API_KEY`
   - `FIREBASE_SERVICE_ACCOUNT_JSON`: 키 파일을 한 줄로 바꿔 붙여넣습니다.
     `python scripts/key_to_env.py serviceAccountKey.json`
   - `ALLOWED_ORIGINS`: `https://<your-project>.vercel.app` (Vercel 배포 후 입력, 끝에 `/` 없이)
3. `https://<your-service>.onrender.com/docs`에서 Swagger UI가 뜨는지 확인합니다.

### 프론트엔드: Vercel

1. Vercel *Add New > Project* → 이 저장소 import → **Root Directory: `frontend`**, Framework Preset: *Other*.
2. 환경 변수 `API_BASE_URL` = `https://<your-service>.onrender.com`
3. Deploy. 빌드 단계에서 `vercel.json`의 `node generate-config.js`가 실행되어 `config.js`에 API 주소가 들어갑니다.
4. 발급된 Vercel 도메인을 Render의 `ALLOWED_ORIGINS`에 넣고 Render를 재배포합니다.

> **왜 빌드 시점에 주입하나?** 정적 HTML/JS는 브라우저에서 실행되므로 서버 환경 변수를 직접 읽을 수 없습니다. 빌드할 때 `config.js` 파일을 만들어 값을 넣습니다. API 주소는 공개되어도 되는 값이고, **비밀 키(OpenAI·Firebase)는 프론트에 절대 두지 않고 백엔드 환경 변수에만** 둡니다.

## 환경 변수

| 변수 | 위치 | 필수 | 설명 |
|---|---|---|---|
| `OPENAI_API_KEY` | Render / backend `.env` | ✅ | OpenAI API 키 |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Render | ✅ (배포) | 서비스 계정 키 JSON 전체 (한 줄) |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | backend `.env` | ✅ (로컬) | 서비스 계정 키 파일 경로. JSON 변수가 있으면 그쪽이 우선 |
| `ALLOWED_ORIGINS` | Render / backend `.env` | ✅ | CORS 허용 도메인, 쉼표 구분 |
| `API_BASE_URL` | Vercel | ✅ | 프론트가 호출할 백엔드 주소 |
| `OPENAI_MODEL` | Render / `.env` | | 기본 `gpt-4o-mini` |
| `OPENAI_MAX_TOKENS` | Render / `.env` | | 응답 토큰 상한, 기본 `500` (비용 제한) |

### CORS / 환경 변수 / 키 관리가 필요한 이유

- **CORS**: 프론트(`*.vercel.app`)와 API(`*.onrender.com`)는 출처가 다르므로, 브라우저는 서버가 허용한 출처만 응답을 읽게 합니다. `*` 대신 내 프론트 도메인만 허용해야 다른 사이트가 사용자 브라우저로 내 API를 호출하는 것을 막을 수 있습니다.
- **환경 변수**: 같은 코드를 로컬/운영에서 설정만 바꿔 실행합니다(DB 키, 허용 도메인, API 주소).
- **키 관리**: 키가 GitHub에 올라가면 즉시 도용되어 과금이나 데이터 유출로 이어집니다. 키는 `.env`(gitignore)와 Render 환경 변수에만 두고, 코드에는 읽는 로직만 둡니다.

### 비용 관리

- `max_completion_tokens=500`으로 응답 길이를 제한하고, 저렴한 `gpt-4o-mini`를 기본 모델로 씁니다.
- 원본 전체 대신 **요약**만 주입하고, 이전 대화는 **최근 10개**만 함께 보냅니다.
- 도구 호출 루프는 최대 3회로 제한합니다.
- 없는 대화 id나 검증 실패는 GPT 호출 **전에** 차단합니다.
- 요약용 전체 조회는 60초 캐시를 사용합니다(쓰기 시 무효화). Firestore 읽기 횟수를 절약합니다.

---

## 제출 스크린샷

> 배포 후 직접 캡처해서 `docs/screenshots/`에 넣어 주세요.

| 화면 | 파일 |
|---|---|
| 데이터 요약이 보이는 채팅 화면 (질문 + 답변) | ![chat](docs/screenshots/chat.png) |
| 데이터 관리 화면 (추가/수정/삭제 중 1개 동작 결과 메시지 포함) | ![data](docs/screenshots/data.png) |
| 대화 기록 화면 (불러오기 동작) | ![history](docs/screenshots/history.png) |
| Swagger UI | ![swagger](docs/screenshots/swagger.png) |
