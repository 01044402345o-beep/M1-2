"""환경 변수 로딩. 키/비밀 값은 코드가 아니라 .env 또는 배포 환경 변수로만 주입한다."""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str) -> list[str]:
    return [v.strip().rstrip("/") for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_max_tokens: int = int(os.getenv("OPENAI_MAX_TOKENS", "500"))
    firebase_service_account_json: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
    firebase_service_account_path: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "")
    allowed_origins: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv("ALLOWED_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500")
        )
    )
    data_label: str = os.getenv("DATA_LABEL", "원/달러 환율 (USD/KRW, 원)")


settings = Settings()
