"""One-shot: add UX-13 '목적' explanation subtitles to tutorial-step slides.

Skips slides that already have a non-empty explanation (bible slides from prior pass).
Run once, then deleted from the workflow — the edits live in content.jsonl.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(
    "/Users/gunnerkim/Documents/multi-agent-creations/agentic-secretary/edu-slides/소상공인-n8n"
)
JSONL = ROOT / "slides" / "content.jsonl"

EXPLANATIONS: dict[str, str] = {
    "29": "블록 목록에서 HTTP Request 찾기.",
    "30": "배달원 블록을 캔버스에 올리기.",
    "31": "\"자료 주세요\" 요청 방식 고정.",
    "32": "정부 공고 창구 주소를 블록에 입력.",
    "33": "주소가 제대로 들어갔는지 한 번 점검.",
    "34": "답변을 글자 덩어리로 받도록 설정.",
    "35": "이 블록만 한 번 실행해 답변 확인.",
    "41": "정리 직원이 쓸 언어를 기본값 그대로.",
    "42": "정리 방법이 적힌 코드 한 번에 투입.",
    "44": "이 블록만 돌려 정리 결과 미리 보기.",
    "52": "Gemini AI 출입증 번호 발급 창구 열기.",
    "53": "본인 Google 계정으로 발급자 확인.",
    "54": "새 출입증 번호 발급 요청 시작.",
    "55": "번호를 담을 프로젝트 고르거나 새로.",
    "56": "발급된 번호를 n8n에 옮길 준비.",
    "58": "발급받은 번호를 붙여넣으러 복귀.",
    "59": "AI 판단 블록 본체를 캔버스에 추가.",
    "60": "AI 본체에 Gemini 모델을 연결.",
    "61": "출입증 번호를 담을 저장함 생성.",
    "62": "발급받은 번호를 꾸러미에 저장.",
    "63": "안정적이고 빠른 모델로 고정.",
    "64": "AI에게 \"이렇게 판단하라\" 설명서 투입.",
    "65": "사장님 실제 가게 정보로 맞춤화.",
    "66": "한 건으로 판단 품질 미리 확인.",
    "84": "수업용 안전 모드 — 항상 참 통과.",
    "85": "Google Sheets 열쇠 복사 한 번 허락.",
    "86": "n8n↔Google 연결 완료 확인.",
    "86.5": "시트 칸에 맞춰 4칸으로 재포장.",
    "87": "어느 시트에 기록할지 지정 + 매핑.",
    "88": "한 줄이 실제로 쌓이는지 확인.",
    "89a": "Gmail 열쇠 복사 한 번 더 허락.",
    "89b": "메일 \"보내기\" 동작으로 고정.",
    "90": "테스트용 본인 주소로 우선 발송.",
    "90c": "표·링크가 살아있는 메일 본문 투입.",
    "91": "메일 1통으로 전체 흐름 성공 검증.",
    "93": "매주 월요일 자동 실행 스위치 ON.",
}

# Preferred field insertion order for readability in JSONL.
FIELD_ORDER = [
    "slide_no",
    "title",
    "bullets",
    "analogy",
    "explanation",
    "callout",
    "slot_refs",
    "pending_cloud_capture",
]


def reorder(row: dict) -> dict:
    ordered = {k: row[k] for k in FIELD_ORDER if k in row}
    # Preserve any unexpected keys at the end
    for k, v in row.items():
        if k not in ordered:
            ordered[k] = v
    return ordered


def main() -> None:
    rows: list[dict] = []
    with open(JSONL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    applied = 0
    skipped_existing: list[str] = []
    missing_target: list[str] = []

    targets = set(EXPLANATIONS.keys())
    found: set[str] = set()

    for row in rows:
        sn = row["slide_no"]
        if sn not in targets:
            continue
        found.add(sn)
        if row.get("explanation"):
            skipped_existing.append(sn)
            continue
        row["explanation"] = EXPLANATIONS[sn]
        applied += 1

    missing_target = sorted(targets - found)

    # Reorder fields for readable output; write one JSON per line.
    with open(JSONL, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(reorder(row), ensure_ascii=False) + "\n")

    print(f"applied: {applied}")
    print(f"skipped (explanation already present): {skipped_existing}")
    print(f"targets not found in content.jsonl: {missing_target}")


if __name__ == "__main__":
    main()
