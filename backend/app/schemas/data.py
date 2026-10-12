from datetime import date as Date
from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# 원/달러 환율 범위를 넉넉히 잡아 오타(예: 14050)를 걸러낸다.
VALUE_MIN, VALUE_MAX = 500, 3000
KST = timezone(timedelta(hours=9))


def today_kst() -> Date:
    # Render 서버는 UTC 기준이라, 한국 오전에 '오늘' 날짜가 미래로 판정되지 않도록 KST 로 비교한다.
    return datetime.now(KST).date()


class DataCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"date": "2026-10-12", "value": 1432.5, "memo": "FOMC 의사록 발표"}}
    )

    date: Date = Field(..., description="기준 날짜 (YYYY-MM-DD)")
    value: float = Field(..., gt=VALUE_MIN, lt=VALUE_MAX, description="1달러당 원화 환율")
    memo: str = Field("", max_length=200, description="메모 (이벤트 등)")

    @model_validator(mode="after")
    def _no_future(self):
        if self.date > today_kst():
            raise ValueError("미래 날짜는 입력할 수 없습니다.")
        self.memo = self.memo.strip()
        return self


class DataUpdate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"value": 1435.0, "memo": "수정됨"}})

    date: Optional[Date] = None
    value: Optional[float] = Field(None, gt=VALUE_MIN, lt=VALUE_MAX)
    memo: Optional[str] = Field(None, max_length=200)

    @model_validator(mode="after")
    def _at_least_one(self):
        if self.date is None and self.value is None and self.memo is None:
            raise ValueError("수정할 필드(date, value, memo)를 하나 이상 보내야 합니다.")
        if self.date and self.date > today_kst():
            raise ValueError("미래 날짜는 입력할 수 없습니다.")
        if self.memo is not None:
            self.memo = self.memo.strip()
        return self


class DataItem(BaseModel):
    id: str
    date: str
    value: float
    memo: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DataList(BaseModel):
    count: int
    items: list[DataItem]


class Metrics(BaseModel):
    average: float
    max: float
    max_date: str
    min: float
    min_date: str
    latest: float
    latest_date: str
    first: float
    change: float = Field(description="기간 첫 값 대비 최근 값 변화량")
    change_pct: float = Field(description="기간 첫 값 대비 최근 값 변화율(%)")
    std: float = Field(description="표준편차 (변동성)")


class MonthlyStat(BaseModel):
    month: str
    average: float
    max: float
    min: float
    count: int


class Summary(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "label": "원/달러 환율 (USD/KRW, 원)",
                "period": "2025-10-01 ~ 2026-10-09",
                "count": 262,
                "metrics": {"average": 1420.1, "max": 1480.2, "max_date": "2026-03-02"},
                "trend": "상승 (최근 30영업일 평균이 직전 30영업일 대비 +1.2%)",
            }
        }
    )

    label: str
    period: str
    count: int
    metrics: Optional[Metrics] = None
    trend: str
    trend_direction: str = Field(description="up | down | flat | unknown")
    recent: list[DataItem] = Field(default_factory=list, description="최근 7개 데이터")
    monthly: list[MonthlyStat] = Field(default_factory=list, description="월별 통계 (최근 24개월)")


class SeriesPoint(BaseModel):
    date: str
    value: float
    ma7: Optional[float] = None
    ma30: Optional[float] = None


class Statistics(BaseModel):
    count: int
    ma7: Optional[float] = Field(None, description="최근 7일 이동평균")
    ma30: Optional[float] = Field(None, description="최근 30일 이동평균")
    volatility: Optional[float] = Field(None, description="일간 변화율의 표준편차(%)")
    biggest_rise: Optional[dict] = Field(None, description="전일 대비 최대 상승일")
    biggest_drop: Optional[dict] = Field(None, description="전일 대비 최대 하락일")
    mom_change_pct: Optional[float] = Field(None, description="직전 월 평균 대비 이번 월 평균 변화율(%)")
    series: list[SeriesPoint] = Field(default_factory=list, description="그래프용 시계열 (이동평균 포함)")
