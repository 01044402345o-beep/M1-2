"""시계열 분석: 요약(프롬프트 주입용)과 확장 통계(그래프/인사이트용)."""
from collections import defaultdict
from statistics import mean, pstdev
from typing import Optional

from app.core.config import settings

TREND_WINDOW = 30      # 최근 N개 vs 직전 N개 평균 비교
FLAT_THRESHOLD = 0.5   # |변화율| < 0.5% 면 '보합'


def _r(x: float, n: int = 2) -> float:
    return round(x, n)


def _trend(values: list[float]) -> tuple[str, str]:
    if len(values) < 4:
        return "판단 불가 (데이터 부족)", "unknown"
    w = min(TREND_WINDOW, len(values) // 2)
    recent, prev = mean(values[-w:]), mean(values[-2 * w:-w])
    pct = (recent - prev) / prev * 100
    desc = f"최근 {w}영업일 평균 {recent:,.2f}, 직전 {w}영업일 평균 대비 {pct:+.2f}%"
    if pct >= FLAT_THRESHOLD:
        return f"상승 ({desc})", "up"
    if pct <= -FLAT_THRESHOLD:
        return f"하락 ({desc})", "down"
    return f"보합 ({desc})", "flat"


def _monthly(rows: list[dict]) -> list[dict]:
    groups: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        groups[r["date"][:7]].append(r["value"])
    return [
        {"month": m, "average": _r(mean(v)), "max": max(v), "min": min(v), "count": len(v)}
        for m, v in sorted(groups.items())
    ]


def build_summary(rows: list[dict]) -> dict:
    """rows 는 날짜 오름차순."""
    if not rows:
        return {"label": settings.data_label, "period": "데이터 없음", "count": 0,
                "metrics": None, "trend": "판단 불가 (데이터 없음)", "trend_direction": "unknown",
                "recent": [], "monthly": []}
    values = [r["value"] for r in rows]
    hi = max(rows, key=lambda r: r["value"])
    lo = min(rows, key=lambda r: r["value"])
    first, last = rows[0], rows[-1]
    trend, direction = _trend(values)
    return {
        "label": settings.data_label,
        "period": f"{first['date']} ~ {last['date']}",
        "count": len(rows),
        "metrics": {
            "average": _r(mean(values)),
            "max": hi["value"], "max_date": hi["date"],
            "min": lo["value"], "min_date": lo["date"],
            "latest": last["value"], "latest_date": last["date"],
            "first": first["value"],
            "change": _r(last["value"] - first["value"]),
            "change_pct": _r((last["value"] - first["value"]) / first["value"] * 100),
            "std": _r(pstdev(values)),
        },
        "trend": trend,
        "trend_direction": direction,
        "recent": rows[-7:][::-1],
        "monthly": _monthly(rows)[-24:],
    }


def _moving_avg(values: list[float], i: int, n: int) -> Optional[float]:
    return _r(mean(values[i - n + 1:i + 1])) if i + 1 >= n else None


def build_statistics(rows: list[dict]) -> dict:
    """보너스: 이동평균, 변동성, 최대 상승/하락일, 전월 대비 변화율 + 그래프용 시계열."""
    if not rows:
        return {"count": 0, "series": []}
    values = [r["value"] for r in rows]
    series = [
        {"date": r["date"], "value": r["value"],
         "ma7": _moving_avg(values, i, 7), "ma30": _moving_avg(values, i, 30)}
        for i, r in enumerate(rows)
    ]
    changes = [
        {"date": rows[i]["date"], "change": _r(values[i] - values[i - 1]),
         "change_pct": _r((values[i] - values[i - 1]) / values[i - 1] * 100)}
        for i in range(1, len(rows))
    ]
    monthly = _monthly(rows)
    mom = None
    if len(monthly) >= 2:
        mom = _r((monthly[-1]["average"] - monthly[-2]["average"]) / monthly[-2]["average"] * 100)
    return {
        "count": len(rows),
        "ma7": series[-1]["ma7"],
        "ma30": series[-1]["ma30"],
        "volatility": _r(pstdev([c["change_pct"] for c in changes]), 3) if len(changes) > 1 else None,
        "biggest_rise": max(changes, key=lambda c: c["change"]) if changes else None,
        "biggest_drop": min(changes, key=lambda c: c["change"]) if changes else None,
        "mom_change_pct": mom,
        "series": series,
    }


def summary_to_prompt(summary: dict) -> str:
    """요약 dict -> 시스템 프롬프트에 넣을 텍스트 (컨텍스트 주입)."""
    m = summary.get("metrics")
    if not m:
        return "- 저장된 데이터가 없습니다."
    monthly = "\n".join(
        f"  - {x['month']}: 평균 {x['average']:,.2f} / 최고 {x['max']:,.2f} / 최저 {x['min']:,.2f} ({x['count']}일)"
        for x in summary["monthly"]
    )
    recent = "\n".join(
        f"  - {x['date']}: {x['value']:,.2f}" + (f" ({x['memo']})" if x.get("memo") else "")
        for x in summary["recent"]
    )
    return (
        f"- 데이터 종류: {summary['label']}\n"
        f"- 데이터 기간: {summary['period']}\n"
        f"- 총 레코드: {summary['count']}개\n"
        f"- 주요 지표: 평균 {m['average']:,.2f}, 최고 {m['max']:,.2f}({m['max_date']}), "
        f"최저 {m['min']:,.2f}({m['min_date']}), 최근 {m['latest']:,.2f}({m['latest_date']}), "
        f"기간 변화 {m['change']:+,.2f} ({m['change_pct']:+.2f}%), 표준편차 {m['std']:,.2f}\n"
        f"- 최근 트렌드: {summary['trend']}\n"
        f"- 월별 통계:\n{monthly}\n"
        f"- 최근 7개 데이터:\n{recent}"
    )
