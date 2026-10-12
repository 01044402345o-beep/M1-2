"""원/달러(USD/KRW) 일별 환율 데이터를 수집해 CSV로 저장한다.

출처: Frankfurter API (유럽중앙은행 ECB 기준환율, API 키 불필요)
사용: python scripts/fetch_data.py --start 2025-01-01 --end 2026-10-09
"""
import argparse
import csv
import json
import urllib.request
from datetime import date, timedelta
from pathlib import Path

API_URL = "https://api.frankfurter.app/{start}..{end}?from=USD&to=KRW"
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "usd_krw.csv"


def fetch(start: str, end: str) -> list[dict]:
    req = urllib.request.Request(
        API_URL.format(start=start, end=end), headers={"User-Agent": "m1-2-fetch"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    rows = [
        {"date": d, "value": round(r["KRW"], 2), "memo": ""}
        for d, r in sorted(payload["rates"].items())
    ]
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=(date.today() - timedelta(days=365)).isoformat())
    parser.add_argument("--end", default=date.today().isoformat())
    args = parser.parse_args()

    rows = fetch(args.start, args.end)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "value", "memo"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)}개 저장: {OUTPUT} ({rows[0]['date']} ~ {rows[-1]['date']})")


if __name__ == "__main__":
    main()
