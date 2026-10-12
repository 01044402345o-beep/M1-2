"""서비스 계정 키 파일(JSON)을 Render 환경 변수에 붙여넣을 한 줄 문자열로 변환해 출력한다.

사용: python scripts/key_to_env.py serviceAccountKey.json
"""
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    print(json.dumps(json.load(f), separators=(",", ":")))
