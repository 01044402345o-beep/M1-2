"""FastAPI 앱 진입점: 앱 초기화, CORS, 예외 처리, 라우터 등록.

실행: uvicorn main:app --reload
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.errors import AppError
from app.core.firebase import FirebaseConfigError
from app.routers import chat, conversations, data

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="My Data AI Assistant API",
    description="원/달러 환율 시계열 데이터를 분석하고, 요약을 GPT 시스템 프롬프트에 주입해 "
                "'내 데이터를 아는' 답변을 제공하는 API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    # 와일드카드(*) 대신 배포된 프론트 도메인만 명시적으로 허용한다 (ALLOWED_ORIGINS, 쉼표 구분).
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message, "code": exc.code})


@app.exception_handler(FirebaseConfigError)
async def firebase_config_handler(_: Request, exc: FirebaseConfigError):
    return JSONResponse(status_code=503, content={"detail": str(exc), "code": "db_not_configured"})


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception):
    # 내부 오류 상세(스택, 키 등)는 응답에 노출하지 않고 로그로만 남긴다.
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "서버 내부 오류가 발생했습니다.", "code": "internal_error"})


@app.get("/", tags=["health"], summary="서비스 정보")
def root():
    return {"service": app.title, "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["health"], summary="헬스 체크 (콜드 스타트 깨우기용)")
def health():
    return {"status": "ok"}


app.include_router(data.router)
app.include_router(conversations.router)
app.include_router(chat.router)
