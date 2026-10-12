"""Firestore 클라이언트 초기화.

서비스 계정 키는 두 방식 중 하나로만 받는다(코드에 하드코딩 금지).
1) FIREBASE_SERVICE_ACCOUNT_JSON : JSON 전체를 한 줄 문자열로 (Render 권장)
2) FIREBASE_SERVICE_ACCOUNT_PATH : 키 파일 경로 (로컬 개발용)
"""
import json
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, firestore

from app.core.config import settings


class FirebaseConfigError(RuntimeError):
    pass


def _load_credentials() -> credentials.Certificate:
    if settings.firebase_service_account_json:
        try:
            info = json.loads(settings.firebase_service_account_json)
        except json.JSONDecodeError as e:
            raise FirebaseConfigError("FIREBASE_SERVICE_ACCOUNT_JSON 이 올바른 JSON이 아닙니다.") from e
        # 환경 변수에 넣을 때 개행이 '\n' 문자열로 들어오는 경우 복원
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\n", "\n")
        return credentials.Certificate(info)
    if settings.firebase_service_account_path:
        return credentials.Certificate(settings.firebase_service_account_path)
    raise FirebaseConfigError(
        "Firebase 자격 증명이 없습니다. FIREBASE_SERVICE_ACCOUNT_JSON 또는 "
        "FIREBASE_SERVICE_ACCOUNT_PATH 환경 변수를 설정하세요."
    )


@lru_cache
def get_firestore():
    if not firebase_admin._apps:
        firebase_admin.initialize_app(_load_credentials())
    return firestore.client()
