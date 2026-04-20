"""Regenerate slides/index.html from content.jsonl + scripts/*.md + manifest.json.

Idempotent: always produces the same output for the same inputs.

Preserves the HTML wrapper (<head>, reveal.js init) by bisecting the existing
index.html at the markers `<div class="slides">` and `</div><!-- /.slides -->`.
Everything between those markers is regenerated from content.jsonl.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(
    "/Users/gunnerkim/Documents/multi-agent-creations/agentic-secretary/edu-slides/소상공인-n8n"
)
SLIDES = ROOT / "slides"
JSONL = SLIDES / "content.jsonl"
SCRIPT_DIR = SLIDES / "scripts"
INDEX = SLIDES / "index.html"
MANIFEST = SLIDES / "assets" / "manifest.json"

BLOCK_LABELS = {
    "A": "블록 A · 오프닝",
    "B": "블록 B · n8n 가입",
    "C": "블록 C · 휴식",
    "D": "블록 D · 실습 1 · 공고 API",
    "E": "블록 E · 휴식",
    "F": "블록 F · 실습 2 · AI 판단",
    "G": "블록 G · 휴식",
    "H": "블록 H · 실습 3 · 시트·메일",
    "I": "블록 I · 정리",
    "J": "블록 J · Q&A·마감",
}

BLOCK_BANNERS = {
    "A": "BLOCK A — 오프닝 (0:00–0:15, 15분)",
    "B": "BLOCK B — n8n Cloud 가입과 첫 워크스페이스 (0:15–0:50, 35분)",
    "C": "BLOCK C — 휴식 #1 (0:50–1:00, 10분)",
    "D": "BLOCK D — 실습 1: 정부 공고 API 불러오기 (1:00–1:45, 45분)",
    "E": "BLOCK E — 휴식 #2 (1:45–1:55, 10분)",
    "F": "BLOCK F — 실습 2: AI가 내 가게에 맞는지 판단 (1:55–2:40, 45분)",
    "G": "BLOCK G — 휴식 #3 (2:40–2:50, 10분)",
    "H": "BLOCK H — 실습 3: 시트 저장 + 메일 발송 (2:50–3:35, 45분)",
    "I": "BLOCK I — 정리와 유지보수 (3:35–3:55, 20분)",
    "J": "BLOCK J — Q&A 및 마감 (3:55–4:00, 5분)",
}


def detect_block(slide_no: str) -> str:
    """Classify slide_no into a block letter.
    Handles numeric, NN.5 (e.g. 36.5), NNa/NNb/NNc (e.g. 89a, 90c), B*-prefix, FB-prefix."""
    s = slide_no
    if s.startswith("B") and not s.startswith("FB"):
        return "B"
    if s.startswith("FB-B"):
        return "B"
    if s.startswith("FB-D"):
        return "D"
    if s.startswith("FB-F"):
        return "F"
    if s.startswith("FB-H"):
        return "H"
    if s.startswith("FB-I"):
        return "I"
    # Strip trailing letter suffix (e.g., 89a → 89, 90c → 90)
    stripped = s.rstrip("abcdefghijklmnopqrstuvwxyz")
    try:
        n = float(stripped)
    except ValueError:
        return "A"
    # Numeric ranges for the 73-slide v2 deck.
    if 1 <= n <= 8.9:
        return "A"
    if 9 <= n <= 14.9:
        return "B"
    if 15 <= n <= 15.9:
        return "C"
    if 16 <= n <= 30.9:
        return "D"
    if 31 <= n <= 31.9:
        return "E"
    if 32 <= n <= 41.9:
        return "F"
    if 42 <= n <= 42.9:
        return "G"
    if 43 <= n <= 60.9:
        return "H"
    if 61 <= n <= 70.9:
        return "I"
    if 71 <= n <= 73.9:
        return "J"
    return "A"


def load_manifest() -> dict[str, dict]:
    with open(MANIFEST, encoding="utf-8") as f:
        m = json.load(f)
    return {s["filename"]: s for s in m["slots"]}


def resolve_img(ref: str, mf: dict[str, dict]) -> str:
    """Map slot_ref (content.jsonl) to a path usable from slides/index.html.

    content.jsonl uses two ref shapes:
      - `assets/placeholder_text_only.png` → slides-dir relative
      - `screenshots/phase_3_cloud/<section>/<file>.png` → repo-root relative
    """
    fn = ref.split("/")[-1]

    # Placeholder slot (content.jsonl lists `assets/placeholder_text_only.png`).
    if fn == "placeholder_text_only.png":
        return "./assets/placeholder_text_only.png"

    # Phase 3 Cloud screenshots: walk up one level from slides/ to repo root.
    if ref.startswith("screenshots/"):
        real = ROOT / ref
        if real.exists():
            return f"../{ref}"

    # Manifest-resolved paths for legacy Phase-1 annotated/placeholder assets.
    entry = mf.get(fn)
    if entry and entry.get("section") == "_shared":
        return "./assets/placeholder_text_only.png"
    if entry and entry["status"] in ("annotated", "reused_from_phase_1"):
        return f"./assets/annotated/{fn}"
    if entry:
        return f"./assets/placeholders/{fn}"

    # Last resort: try annotated/, placeholders/ on disk before falling back.
    for sub in ("annotated", "placeholders"):
        if (SLIDES / "assets" / sub / fn).exists():
            return f"./assets/{sub}/{fn}"
    return "./assets/placeholder_text_only.png"


def find_script_body(slide_no: str) -> str:
    """Find scripts/<slide_no>_*.md and return the body (H1 title + * italic markers stripped).
    Content writer filenames use `_` instead of `.` for fractional slide_nos (e.g., 36.5 → 36_5)."""
    candidates = [slide_no, slide_no.replace(".", "_")]
    matches: list[Path] = []
    for cand in candidates:
        matches = list(SCRIPT_DIR.glob(f"{cand}_*.md"))
        if matches:
            break
    if not matches:
        return ""
    text = matches[0].read_text(encoding="utf-8")
    # Remove first H1 line
    lines = text.splitlines()
    body_lines = []
    seen_h1 = False
    for ln in lines:
        if not seen_h1 and ln.startswith("# "):
            seen_h1 = True
            continue
        body_lines.append(ln)
    body = "\n".join(body_lines).strip()
    # Strip surrounding *...* italic markers if whole body is one italic block
    if body.startswith("*") and body.endswith("*") and body.count("*") == 2:
        body = body[1:-1].strip()
    return body


def esc(s: str) -> str:
    return html.escape(s, quote=True)


BREAK_SLIDES = {"15", "31", "42"}
OPENER_SLIDES: set[str] = set()
REASSURE_SLIDES = {"25", "39", "55"}
CHECKPOINT_SLIDES = {"30", "58", "60", "69"}

STRUCTURAL_COVER = {"01"}
STRUCTURAL_BANNER = {"16", "32", "43"}
STRUCTURAL_RECAP = {"61", "62", "63", "64", "65"}
STRUCTURAL_BENEFIT = {"68"}
STRUCTURAL_CLOSING = {"71", "72", "73"}


def structural_layout(sn: str) -> str | None:
    """Return structural layout type if this slide uses a custom (non-tutorial) template."""
    if sn in STRUCTURAL_COVER:
        return "cover"
    if sn in STRUCTURAL_BANNER:
        return "banner"
    if sn in BREAK_SLIDES:
        return "break"
    if sn in STRUCTURAL_RECAP:
        return "recap"
    if sn in STRUCTURAL_BENEFIT:
        return "benefit"
    if sn in STRUCTURAL_CLOSING:
        return "closing"
    return None


def classify(sn: str) -> str | None:
    if sn in BREAK_SLIDES:
        return "break"
    if sn in OPENER_SLIDES:
        return "opener"
    if sn in REASSURE_SLIDES:
        return "reassure"
    if sn in CHECKPOINT_SLIDES:
        return "checkpoint"
    return None


# Banner metadata — parses slide_no → 실습 number + duration
BANNER_META = {
    "16": {"num": "1", "name": "정부지원사업 공고 가져오기", "duration": "45분", "window": "1:00–1:45"},
    "32": {"num": "2", "name": "Gemini가 공고를 골라주기", "duration": "45분", "window": "1:55–2:40"},
    "43": {"num": "3", "name": "시트에 쌓고 메일로 알림", "duration": "45분", "window": "2:50–3:35"},
}

BREAK_META = {
    "15": {"num": "1", "duration": "10분", "next": "실습 1 — 정부 공고 API 가져오기"},
    "31": {"num": "2", "duration": "10분", "next": "실습 2 — Gemini 맞춤도 판정"},
    "42": {"num": "3", "duration": "10분", "next": "실습 3 — Sheets + Gmail 발송"},
}

BENEFIT_TOOLS = [
    {"name": "n8n Cloud", "sub": "자동화 플랫폼", "price": "$20/월"},
    {"name": "Gemini", "sub": "Google AI", "price": "$20/월"},
    {"name": "CapCut Pro", "sub": "영상 편집", "price": "$19.99/월"},
    {"name": "Kling AI", "sub": "영상 생성", "price": "$6.99~/월"},
]


def _section_open(sn: str, block: str, block_tag: str, extra_classes: list[str], slide_type: str | None, is_fallback: bool) -> list[str]:
    attrs: list[str] = [f'data-slide="{esc(sn)}"', f'data-block="{block}"']
    if extra_classes:
        attrs.append(f'class="{" ".join(extra_classes)}"')
    if slide_type:
        attrs.append(f'data-slide-type="{slide_type}"')
    if is_fallback:
        attrs.append('data-visibility="uncounted"')
    return [
        f"<section {' '.join(attrs)}>",
        f'  <div class="slide-meta"><span class="chip">{esc(sn)}</span>'
        f'<span class="block-tag">{esc(block_tag)}</span></div>',
    ]


STALE_NOTE_TOKENS = (
    # ASCII v1 SMS/Aligo residue
    "sms",
    "aligo",
    "stretch_sms",
    # Aligo API response field names — SMS-only, safe to block
    "result_code",
    "msg_id",
    "success_cnt",
    "error_cnt",
    # Korean SMS flow jargon from v1 scripts (Korean is not lowercased, so these
    # tokens are checked against the raw note text, not .lower()). Scoped to
    # SMS-specific terms to avoid false positives on "문자열" / "문자 메시지 앱".
    "문자_발송",
    "문자 발송",
    "발신번호",
    "휴대폰 문자",
    "휴대폰으로 문자",
)


def _notes_block(notes: str) -> str:
    """Emit speaker notes only if they're not stale.

    v1 speaker scripts (in `slides/scripts/*.md`) were authored under the
    deprecated 101-slide plan that included an SMS-send stretch block. The v2
    73-slide deck dropped that block, so those scripts leak SMS/Aligo tokens
    into `index.html`. The guard substitutes `(script pending)` for any note
    containing a stale token.

    ASCII tokens are matched case-insensitively (handles `Aligo` / `aligo.in`).
    Korean tokens are matched against the raw text (case-folding is a no-op
    for Hangul) and are scoped to SMS-specific compounds to avoid filtering
    legitimate Korean content that happens to contain `문자`."""
    if not notes:
        return '  <aside class="notes">(script pending)</aside>'
    lower = notes.lower()
    for tok in STALE_NOTE_TOKENS:
        needle = tok if any(ord(c) > 127 for c in tok) else tok.lower()
        haystack = notes if any(ord(c) > 127 for c in tok) else lower
        if needle in haystack:
            return '  <aside class="notes">(script pending)</aside>'
    return f'  <aside class="notes">{esc(notes)}</aside>'


def render_cover(row: dict, block: str, block_tag: str, notes: str) -> str:
    sn = row["slide_no"]
    title = row.get("title", "")
    bullets = row.get("bullets", []) or []
    callout = row.get("callout")

    parts = _section_open(sn, block, block_tag, ["slide-cover"], None, False)
    # Cover has no meta chip visually — CSS hides .slide-meta inside .slide-cover.
    # Split title on em-dash into hero + subtitle where possible.
    if " — " in title:
        hero, subtitle = title.split(" — ", 1)
    else:
        hero, subtitle = title, ""
    parts.append(f'  <div class="cover-body">')
    parts.append(f'    <div class="cover-brand">WrtnEdu × 케미스트릿 강남역</div>')
    parts.append(f'    <h1 class="cover-hero">{esc(hero)}</h1>')
    if subtitle:
        parts.append(f'    <p class="cover-subtitle">{esc(subtitle)}</p>')
    # Hidden h2 to keep auditor regex + a11y structure consistent
    parts.append(f'    <h2 class="visually-hidden">{esc(title)}</h2>')
    if bullets:
        parts.append('    <ul class="cover-points">')
        for b in bullets:
            parts.append(f'      <li>{esc(b)}</li>')
        parts.append('    </ul>')
    if callout:
        parts.append(f'    <aside class="callout cover-callout">{esc(callout)}</aside>')
    parts.append('  </div>')
    parts.append(_notes_block(notes))
    parts.append("</section>")
    return "\n".join(parts)


def render_banner(row: dict, block: str, block_tag: str, notes: str) -> str:
    sn = row["slide_no"]
    title = row.get("title", "")
    bullets = row.get("bullets", []) or []
    analogy = row.get("analogy")
    callout = row.get("callout")
    meta = BANNER_META.get(sn, {"num": "?", "name": title, "duration": "", "window": ""})

    parts = _section_open(sn, block, block_tag, ["slide-banner"], None, False)
    parts.append('  <div class="banner-body">')
    parts.append(f'    <div class="banner-label">[실습 {esc(meta["num"])}]</div>')
    parts.append(f'    <h2 class="banner-title">{esc(meta["name"])}</h2>')
    parts.append('    <div class="banner-time">')
    if meta["window"]:
        parts.append(f'      <span class="banner-window">{esc(meta["window"])}</span>')
    if meta["duration"]:
        parts.append(f'      <span class="banner-duration">{esc(meta["duration"])}</span>')
    parts.append('    </div>')
    if bullets:
        parts.append('    <ul class="banner-objectives">')
        for b in bullets:
            parts.append(f'      <li>{esc(b)}</li>')
        parts.append('    </ul>')
    if analogy:
        parts.append(f'    <aside class="analogy-box banner-analogy">{esc(analogy)}</aside>')
    if callout:
        parts.append(f'    <aside class="callout banner-callout">{esc(callout)}</aside>')
    parts.append('  </div>')
    parts.append(_notes_block(notes))
    parts.append("</section>")
    return "\n".join(parts)


def render_break(row: dict, block: str, block_tag: str, notes: str) -> str:
    sn = row["slide_no"]
    title = row.get("title", "")
    bullets = row.get("bullets", []) or []
    callout = row.get("callout")
    meta = BREAK_META.get(sn, {"num": "?", "duration": "10분", "next": ""})

    parts = _section_open(sn, block, block_tag, ["slide-break"], "break", False)
    parts.append('  <div class="break-body">')
    parts.append('    <div class="break-icon" aria-hidden="true">⏱</div>')
    parts.append(f'    <h2 class="break-title">휴식 #{esc(meta["num"])} — {esc(meta["duration"])}</h2>')
    if meta["next"]:
        parts.append(f'    <p class="break-next">다음 → {esc(meta["next"])}</p>')
    if bullets:
        parts.append('    <ul class="break-notes">')
        for b in bullets:
            parts.append(f'      <li>{esc(b)}</li>')
        parts.append('    </ul>')
    if callout:
        parts.append(f'    <aside class="callout break-callout">{esc(callout)}</aside>')
    parts.append('  </div>')
    parts.append(_notes_block(notes))
    parts.append("</section>")
    return "\n".join(parts)


def render_recap(row: dict, block: str, block_tag: str, notes: str) -> str:
    sn = row["slide_no"]
    title = row.get("title", "")
    bullets = row.get("bullets", []) or []
    analogy = row.get("analogy")
    explanation = row.get("explanation")
    callout = row.get("callout")

    parts = _section_open(sn, block, block_tag, ["slide-recap-card"], None, False)
    parts.append('  <div class="recap-body">')
    parts.append(f'    <h2 class="recap-title">{esc(title)}</h2>')
    if explanation:
        parts.append(f'    <p class="explanation recap-explanation">{esc(explanation)}</p>')
    if bullets:
        # 2-column grid of recap cards
        parts.append('    <div class="recap-grid">')
        for i, b in enumerate(bullets, 1):
            parts.append(f'      <div class="recap-card"><span class="recap-card-num">{i:02d}</span><span class="recap-card-text">{esc(b)}</span></div>')
        parts.append('    </div>')
    if analogy:
        parts.append(f'    <aside class="analogy-box recap-analogy">{esc(analogy)}</aside>')
    if callout:
        parts.append(f'    <aside class="callout recap-callout">{esc(callout)}</aside>')
    parts.append('  </div>')
    parts.append(_notes_block(notes))
    parts.append("</section>")
    return "\n".join(parts)


def render_benefit(row: dict, block: str, block_tag: str, notes: str) -> str:
    sn = row["slide_no"]
    title = row.get("title", "")
    bullets = row.get("bullets", []) or []
    callout = row.get("callout")

    parts = _section_open(sn, block, block_tag, ["slide-benefit"], None, False)
    parts.append('  <div class="benefit-body">')
    parts.append(f'    <h2 class="benefit-title">{esc(title)}</h2>')
    parts.append('    <div class="benefit-tools">')
    for t in BENEFIT_TOOLS:
        parts.append(
            '      <div class="benefit-tool">'
            f'<span class="benefit-tool-name">{esc(t["name"])}</span>'
            f'<span class="benefit-tool-sub">{esc(t["sub"])}</span>'
            f'<span class="benefit-tool-price">{esc(t["price"])}</span>'
            '</div>'
        )
    parts.append('    </div>')
    parts.append('    <div class="benefit-formula">2개 도구 × 3개월 = 최대 <strong>20만원</strong> 상당</div>')
    if bullets:
        parts.append('    <ul class="benefit-notes">')
        for b in bullets:
            parts.append(f'      <li>{esc(b)}</li>')
        parts.append('    </ul>')
    if callout:
        parts.append(f'    <aside class="callout benefit-callout">{esc(callout)}</aside>')
    parts.append('  </div>')
    parts.append(_notes_block(notes))
    parts.append("</section>")
    return "\n".join(parts)


def render_closing(row: dict, block: str, block_tag: str, notes: str) -> str:
    sn = row["slide_no"]
    title = row.get("title", "")
    bullets = row.get("bullets", []) or []
    callout = row.get("callout")

    # Icon selector per closing slide
    icon = {"71": "💬", "72": "❓", "73": "🎓"}.get(sn, "🎓")

    parts = _section_open(sn, block, block_tag, ["slide-closing"], None, False)
    parts.append('  <div class="closing-body">')
    parts.append(f'    <div class="closing-icon" aria-hidden="true">{icon}</div>')
    parts.append(f'    <h2 class="closing-title">{esc(title)}</h2>')
    if bullets:
        parts.append('    <ul class="closing-points">')
        for b in bullets:
            parts.append(f'      <li>{esc(b)}</li>')
        parts.append('    </ul>')
    if sn == "71":
        parts.append('    <div class="closing-qr" aria-label="QR 코드 자리"><span>QR</span><small>연락처 · 카톡</small></div>')
    if sn == "73":
        parts.append('    <div class="closing-qr" aria-label="피드백 설문 QR"><span>QR</span><small>피드백 설문</small></div>')
    if callout:
        parts.append(f'    <aside class="callout closing-callout">{esc(callout)}</aside>')
    parts.append('  </div>')
    parts.append(_notes_block(notes))
    parts.append("</section>")
    return "\n".join(parts)


def render_tutorial(row: dict, mf: dict[str, dict], block: str, block_tag: str, slide_type: str | None, is_fallback: bool, notes: str) -> str:
    """Original 2-column tutorial renderer for the 63 non-structural slides."""
    sn = row["slide_no"]
    title = row.get("title", "")
    bullets = row.get("bullets", []) or []
    analogy = row.get("analogy")
    explanation = row.get("explanation")
    callout = row.get("callout")
    figcaption_override = row.get("figcaption_override")
    refs = row.get("slot_refs", []) or []
    pending = bool(row.get("pending_cloud_capture"))

    parts = _section_open(sn, block, block_tag, [], slide_type, is_fallback)
    parts.append(f"  <h2>{esc(title)}</h2>")
    if explanation:
        parts.append(f'  <p class="explanation">{esc(explanation)}</p>')
    if bullets:
        parts.append("  <ul>")
        for b in bullets:
            parts.append(f"    <li>{esc(b)}</li>")
        parts.append("  </ul>")
    if analogy:
        parts.append(f'  <aside class="analogy-box">{esc(analogy)}</aside>')
    for ref in refs:
        src = resolve_img(ref, mf)
        fn = ref.split("/")[-1]
        alt = esc(f"{title} — {fn}")
        parts.append(f"  <figure>")
        parts.append(f'    <img src="{src}" alt="{alt}">')
        if figcaption_override:
            parts.append(f'    <figcaption class="figcaption-override">{esc(figcaption_override)}</figcaption>')
        parts.append(f"  </figure>")
    if pending:
        parts.append('  <span class="pending-flag">pending cloud capture</span>')
    if callout:
        parts.append(f'  <aside class="callout">{esc(callout)}</aside>')
    parts.append(_notes_block(notes))
    parts.append("</section>")
    return "\n".join(parts)


def render_slide(row: dict, mf: dict[str, dict]) -> str:
    sn = row["slide_no"]
    block = detect_block(sn)
    block_tag = BLOCK_LABELS.get(block, f"블록 {block}")
    notes = find_script_body(sn)
    slide_type = classify(sn)
    is_fallback = sn.startswith("FB-")

    layout = structural_layout(sn)
    if layout == "cover":
        return render_cover(row, block, block_tag, notes)
    if layout == "banner":
        return render_banner(row, block, block_tag, notes)
    if layout == "break":
        return render_break(row, block, block_tag, notes)
    if layout == "recap":
        return render_recap(row, block, block_tag, notes)
    if layout == "benefit":
        return render_benefit(row, block, block_tag, notes)
    if layout == "closing":
        return render_closing(row, block, block_tag, notes)
    return render_tutorial(row, mf, block, block_tag, slide_type, is_fallback, notes)


def render_all() -> str:
    mf = load_manifest()
    rows: list[dict] = []
    with open(JSONL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    # Group by block while preserving JSONL order
    groups: dict[str, list[dict]] = {k: [] for k in BLOCK_BANNERS}
    for row in rows:
        b = detect_block(row["slide_no"])
        groups.setdefault(b, []).append(row)

    out_parts: list[str] = []
    for block in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
        slides_in_block = groups.get(block, [])
        if not slides_in_block:
            continue
        banner = BLOCK_BANNERS[block]
        slide_nos = " ".join(r["slide_no"] for r in slides_in_block)
        out_parts.append(
            "<!-- =====================================================================\n"
            f"     {banner}\n"
            f"     slides: {slide_nos}  ({len(slides_in_block)} slides)\n"
            "     ===================================================================== -->\n"
        )
        for row in slides_in_block:
            out_parts.append(render_slide(row, mf))
            out_parts.append("")

    return "\n".join(out_parts)


WRAPPER_TOP = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>소상공인 n8n — 정부지원금 자동알림 4시간 워크숍</title>

  <!-- Pretendard -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">

  <!-- Reveal.js 5.x core + white theme -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/theme/white.css">

  <!-- Course 2 custom theme -->
  <link rel="stylesheet" href="./style.css">

  <!-- Reveal print stylesheet — required for ?print-pdf export to apply slide layout -->
  <script>
    (function(){
      var href = window.location.search.match(/print-pdf/gi)
        ? 'https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/css/print/pdf.css'
        : 'https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/css/print/paper.css';
      var l = document.createElement('link');
      l.rel = 'stylesheet'; l.type = 'text/css'; l.href = href;
      document.getElementsByTagName('head')[0].appendChild(l);
    })();
  </script>
</head>
<body>
<div class="reveal">
<div class="slides">

"""

WRAPPER_BOTTOM = """
</div><!-- /.slides -->
</div><!-- /.reveal -->

<!-- Reveal.js core + plugins -->
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/plugin/markdown/markdown.js"></script>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/plugin/highlight/highlight.js"></script>
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/plugin/notes/notes.js"></script>

<script>
  Reveal.initialize({
    hash: true,
    slideNumber: 'c/t',
    progress: true,
    autoAnimate: true,
    transition: 'slide',
    width: 1600,
    height: 1000,
    margin: 0.04,
    minScale: 0.2,
    maxScale: 2.0,
    plugins: [RevealMarkdown, RevealHighlight, RevealNotes]
  });
</script>
</body>
</html>
"""


def main() -> None:
    body = render_all()
    INDEX.write_text(WRAPPER_TOP + body + WRAPPER_BOTTOM, encoding="utf-8")
    # Verify section count
    count = len(re.findall(r'<section[^>]*\sdata-slide=', INDEX.read_text(encoding="utf-8")))
    print(f"index.html written. <section data-slide> count: {count}")


if __name__ == "__main__":
    main()
