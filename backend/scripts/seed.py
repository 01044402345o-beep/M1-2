"""data/usd_krw.csv 를 Firestore 'data' 컬렉션에 업로드한다.

사용 (backend 폴더에서, .env 설정 후):
    python -m scripts.seed            # 이미 있는 날짜는 건너뜀
    python -m scripts.seed --reset    # data 컬렉션을 비우고 다시 업로드
"""
import argparse
import csv
from pathlib import Path

from app.core.firebase import get_firestore
from app.repositories.firestore import DATA
from app.services.data_service import now_iso

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "usd_krw.csv"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    db = get_firestore()
    col = db.collection(DATA)

    if args.reset:
        deleted = 0
        for snap in col.stream():
            snap.reference.delete()
            deleted += 1
        print(f"기존 문서 {deleted}개 삭제")

    existing = {s.get("date") for s in col.select(["date"]).stream()}
    with CSV_PATH.open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["date"] not in existing]

    batch, n = db.batch(), 0
    ts = now_iso()
    for r in rows:
        batch.set(col.document(), {
            "date": r["date"], "value": float(r["value"]),
            "memo": r.get("memo", ""),
            "created_at": ts, "updated_at": ts,
        })
        n += 1
        if n % 400 == 0:  # Firestore 배치 한도 500
            batch.commit()
            batch = db.batch()
    batch.commit()
    print(f"{n}개 업로드 완료 (건너뜀: {len(existing)}개)")


if __name__ == "__main__":
    main()
