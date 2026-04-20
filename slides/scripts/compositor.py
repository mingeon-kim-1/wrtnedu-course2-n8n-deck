"""Phase 4 Screenshot Compositor.

Produces:
  slides/assets/annotated/<slot>.png     for the 5 real Phase-3 captures (03_gemini_api)
  slides/assets/annotated/45_workflow_build_execute_all_green.png   (reused from phase_1)
  slides/assets/annotated/54_workflow_build_final_diagram_7nodes.png (reused from phase_1)
  slides/assets/placeholders/<slot>.png  for every PLAN.md §3 slot without a raw capture
  slides/assets/manifest.json            catalogue of every referenced image

Annotation spec: PLAN.md §3.3
  - crop top 40 logical px (= 80 px at 2x) to remove Chrome MCP orange debug banner
  - red rectangles (#E53935, 4px) around UI targets
  - numbered circles (40px dia, #E53935 fill, white 24pt bold digit) at click-order
  - optional callout (#FFF8E1 fill, #FBC02D border 2px, 8px radius, padding 8px, <=12 chars)
  - redaction masks over API-key regions ("🔒 [API 키]")
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(
    "/Users/gunnerkim/Documents/multi-agent-creations/agentic-secretary/edu-slides/소상공인-n8n"
)
SHOT_DIR = ROOT / "screenshots" / "phase_3"
PHASE1 = ROOT / "screenshots" / "phase_1_execution.png"
ANN_DIR = ROOT / "slides" / "assets" / "annotated"
PH_DIR = ROOT / "slides" / "assets" / "placeholders"
MANIFEST = ROOT / "slides" / "assets" / "manifest.json"

RED = "#E53935"
CALL_FILL = "#FFF8E1"
CALL_BORDER = "#FBC02D"
FONT_KR = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

# Slot catalogue - mirrors PLAN.md §3.4.* exactly.
SLOTS: list[dict] = []

# 3.4.1 n8n_signup (3, pending-cloud-capture)
for nm in [
    "01_n8n_signup_cloud_signup_form.png",
    "02_n8n_signup_cloud_workspace_ready.png",
    "03_n8n_signup_cloud_empty_dashboard.png",
]:
    SLOTS.append({"section": "01_n8n_signup", "name": nm, "kind": "pending-cloud-capture"})

# 3.4.3 gemini_api (8, 5 real + 3 missing)
for nm in [
    "01_gemini_api_aistudio_home.png",
    "02_gemini_api_google_login.png",
    "03_gemini_api_create_key_btn.png",
    "04_gemini_api_project_select.png",
    "05_gemini_api_key_copy.png",
    "06_gemini_api_key_copied_toast.png",
    "07_gemini_api_key_list.png",
    "08_gemini_api_model_gemini_25_flash.png",
]:
    SLOTS.append({"section": "03_gemini_api", "name": nm, "kind": "real-or-missing"})

# 3.4.4 sheets_gmail (3, pending-cloud-capture)
for nm in [
    "01_sheets_gmail_signin_popup.png",
    "02_sheets_gmail_consent_allow.png",
    "03_sheets_gmail_credential_connected_badge.png",
]:
    SLOTS.append({"section": "04_sheets_gmail", "name": nm, "kind": "pending-cloud-capture"})

# 3.4.5 workflow_build (52 slots - excluding DELETED 32/34/38)
wf = [
    "01_workflow_build_create_workflow.png",
    "02_workflow_build_empty_canvas.png",
    "03_workflow_build_rename.png",
    "04_workflow_build_schedule_trigger_added.png",
    "05_workflow_build_add_http_request.png",
    "06_workflow_build_search_http.png",
    "07_workflow_build_select_http.png",
    "08_workflow_build_method_get.png",
    "09_workflow_build_url_pasted.png",
    "10_workflow_build_url_filled.png",
    "11_workflow_build_response_text.png",
    "12_workflow_build_execute_http.png",
    "13_workflow_build_http_result.png",
    "14_workflow_build_add_code_node.png",
    "15_workflow_build_code_lang_js.png",
    "16_workflow_build_code_pasted.png",
    "17_workflow_build_execute_code.png",
    "18_workflow_build_code_result.png",
    "19_workflow_build_back_to_n8n.png",
    "20_workflow_build_attach_gemini_model.png",
    "21_workflow_build_create_gemini_cred.png",
    "22_workflow_build_paste_key_save.png",
    "23_workflow_build_model_gemini_25_flash.png",
    "24_workflow_build_add_chain_llm.png",
    "25_workflow_build_prompt_pasted.png",
    "26_workflow_build_execute_gemini.png",
    "27_workflow_build_gemini_result.png",
    "28_workflow_build_add_if_node.png",
    "29_workflow_build_if_condition.png",
    "30_workflow_build_sheet_id_copy.png",
    "31_workflow_build_add_sheets_node.png",
    # 32 DELETED
    "33_workflow_build_sheets_oauth_popup.png",
    # 34 DELETED
    "35_workflow_build_sheet_mapping.png",
    "36_workflow_build_sheet_row_appended.png",
    "37_workflow_build_add_gmail_node.png",
    # 38 DELETED
    "39_workflow_build_gmail_resource_send.png",
    "40_workflow_build_gmail_body.png",
    "41_workflow_build_gmail_html.png",
    "42_workflow_build_inbox_received.png",
    "43_workflow_build_final_email_example.png",
    "44_workflow_build_demo_email_still.png",
    "45_workflow_build_execute_all_green.png",  # reuse phase_1
    "46_workflow_build_active_toggle.png",
    "47_workflow_build_empty_editor_canvas.png",
    "48_workflow_build_empty_editor_nodes_panel.png",
    "49_workflow_build_empty_editor_run_button.png",
    "50_workflow_build_save_toast.png",
    "51_workflow_build_credential_connected_badge.png",
    "52_workflow_build_link_submodel.png",
    "53_workflow_build_if_two_branches.png",
    "54_workflow_build_final_diagram_7nodes.png",  # reuse phase_1
    "55_workflow_build_time_saved_counter.png",
]
for nm in wf:
    SLOTS.append({"section": "05_workflow_build", "name": nm, "kind": "workflow"})

# 3.4.6 errors (9 active; drop 01, 02, 09; PDF-only 08)
errs = [
    "03_errors_setup_password_invalid.png",
    "04_errors_phase_3_http_400.png",
    "05_errors_code_node_quote_smart.png",
    "06_errors_gemini_429_quota.png",
    "07_errors_gemini_api_key_invalid.png",
    "08_errors_oauth_unverified_app.png",
    "10_errors_sheets_header_missing.png",
    "11_errors_gmail_encoding_broken.png",
    "cloud_email_verification.png",
    "sign_in_popup_blocked.png",
]
for nm in errs:
    SLOTS.append({"section": "errors", "name": nm, "kind": "error"})

# PLAN §3.4.4 note: 08_new_sheet_headers.png stays in sheets_gmail folder (localhost OK)
SLOTS.append({"section": "04_sheets_gmail", "name": "08_new_sheet_headers.png", "kind": "localhost-ok"})

# Post-janitor composites: only 86.5 consolidated (26c) survives; topology renamed NN_ → 32_
SLOTS.append({"section": "05_workflow_build", "name": "32_workflow_build_topology_correct_vs_orphan.png", "kind": "composite"})
SLOTS.append({"section": "05_workflow_build", "name": "26c_set_output.png", "kind": "workflow"})

# Filename guard (PLAN.md §3.2): ASCII + underscores only, 2-digit NN or short lowercase
def ok_filename(name: str) -> bool:
    stem = name.removesuffix(".png")
    return all(c.isascii() and (c.isalnum() or c in "_") for c in stem)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_KR
    return ImageFont.truetype(path, size)


def crop_top_banner(img: Image.Image) -> Image.Image:
    """Remove ~40 logical px = 80 physical px on retina 2x."""
    scale = max(1, img.width // 1728)
    cut = 40 * scale
    return img.crop((0, cut, img.width, img.height))


def draw_rect(d: ImageDraw.ImageDraw, box, scale: int) -> None:
    d.rectangle(box, outline=RED, width=4 * scale)


def draw_circle(d: ImageDraw.ImageDraw, cx: int, cy: int, digit: str, scale: int) -> None:
    r = 20 * scale
    d.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=RED)
    try:
        f = font(24 * scale, bold=True)
    except OSError:
        f = ImageFont.load_default()
    tw = f.getlength(digit)
    d.text((cx - tw / 2, cy - 14 * scale), digit, fill="white", font=f)


def draw_callout(d: ImageDraw.ImageDraw, x: int, y: int, text: str, scale: int) -> None:
    f = font(18 * scale)
    tw = f.getlength(text)
    pad = 8 * scale
    box = [(x, y), (x + tw + pad * 2, y + 24 * scale + pad * 2)]
    d.rounded_rectangle(box, radius=8 * scale, fill=CALL_FILL, outline=CALL_BORDER, width=2 * scale)
    d.text((x + pad, y + pad), text, fill="#333333", font=f)


def draw_mask(d: ImageDraw.ImageDraw, box, scale: int) -> None:
    d.rectangle(box, fill="#111111")
    f = font(16 * scale, bold=True)
    x1, y1, x2, y2 = box[0][0], box[0][1], box[1][0], box[1][1]
    txt = "[API 키]"
    tw = f.getlength(txt)
    d.text(((x1 + x2) / 2 - tw / 2, (y1 + y2) / 2 - 12 * scale), txt, fill="white", font=f)


# Per-slot annotation recipes for the 5 real captures.
# Coordinates are rough logical (scaled to physical via `scale`).
ANN_RECIPES = {
    "01_gemini_api_aistudio_home.png": [
        ("rect", (50, 260, 340, 320)),
        ("circle", (60, 290, "1")),
    ],
    "02_gemini_api_google_login.png": [
        ("rect", (500, 340, 1200, 520)),
        ("circle", (510, 360, "1")),
    ],
    "03_gemini_api_create_key_btn.png": [
        ("rect", (1380, 180, 1700, 250)),
        ("circle", (1390, 200, "1")),
        ("callout", (1390, 260, "여기 클릭")),
    ],
    "04_gemini_api_project_select.png": [
        ("rect", (500, 400, 1200, 560)),
        ("circle", (510, 420, "1")),
        ("circle", (510, 540, "2")),
    ],
    "05_gemini_api_key_copy.png": [
        ("rect", (480, 360, 1220, 480)),
        ("mask", (620, 380, 1140, 440)),
        ("circle", (1150, 380, "1")),
        ("callout", (480, 500, "안전 보관")),
    ],
    "07_gemini_api_key_list.png": [
        ("rect", (380, 420, 1320, 540)),
        ("callout", (380, 560, "재접근 불가")),
    ],
}

# Normalize: accept 4-tuple form ("circle", x, y, d) OR 2-tuple form ("circle", (x, y, d))
def _normalize(rs):
    out = []
    for op in rs:
        if op[0] in ("rect", "mask"):
            out.append(op)
        elif op[0] in ("circle", "callout"):
            if len(op) == 4:
                out.append((op[0], (op[1], op[2], op[3])))
            else:
                out.append(op)
    return out

for _k, _v in list(ANN_RECIPES.items()):
    ANN_RECIPES[_k] = _normalize(_v)


def annotate_one(src: Path, dst: Path, recipe: list[tuple]) -> None:
    img = Image.open(src).convert("RGB")
    img = crop_top_banner(img)
    scale = max(1, img.width // 1728)
    d = ImageDraw.Draw(img)
    for op in recipe:
        if op[0] == "rect":
            x1, y1, x2, y2 = op[1]
            draw_rect(d, [(x1 * scale, y1 * scale), (x2 * scale, y2 * scale)], scale)
        elif op[0] == "circle":
            cx, cy, digit = op[1]
            draw_circle(d, cx * scale, cy * scale, digit, scale)
        elif op[0] == "callout":
            x, y, txt = op[1]
            draw_callout(d, x * scale, y * scale, txt, scale)
        elif op[0] == "mask":
            x1, y1, x2, y2 = op[1]
            draw_mask(d, [(x1 * scale, y1 * scale), (x2 * scale, y2 * scale)], scale)
    img.save(dst, "PNG")


def make_placeholder(name: str, dst: Path, kind: str) -> None:
    """Generate a visually distinct 1600x900 placeholder PNG."""
    W, H = 1600, 900
    img = Image.new("RGB", (W, H), "#F5F5F5")
    d = ImageDraw.Draw(img)
    # dashed border to distinguish from real captures
    dash = 24
    gap = 16
    stroke = 6
    x = 0
    border = "#BDBDBD"
    while x < W:
        d.rectangle([(x, 0), (min(x + dash, W), stroke)], fill=border)
        d.rectangle([(x, H - stroke), (min(x + dash, W), H)], fill=border)
        x += dash + gap
    y = 0
    while y < H:
        d.rectangle([(0, y), (stroke, min(y + dash, H))], fill=border)
        d.rectangle([(W - stroke, y), (W, min(y + dash, H))], fill=border)
        y += dash + gap
    label_kr = "Cloud 캡처 예정 — 수업 당일 반영" if kind == "pending-cloud-capture" else "캡처 예정"
    sub_kr = "Phase 3 원본 미확보 (placeholder)" if kind != "pending-cloud-capture" else "별도 Cloud 세션에서 캡처"
    try:
        f_main = ImageFont.truetype(FONT_KR, 56)
        f_sub = ImageFont.truetype(FONT_KR, 32)
        f_foot = ImageFont.truetype(FONT_KR, 24)
    except OSError:
        f_main = ImageFont.load_default()
        f_sub = f_main
        f_foot = f_main
    tw = f_main.getlength(label_kr)
    d.text(((W - tw) / 2, H / 2 - 90), label_kr, fill="#424242", font=f_main)
    tw = f_sub.getlength(sub_kr)
    d.text(((W - tw) / 2, H / 2 - 10), sub_kr, fill="#757575", font=f_sub)
    tw = f_foot.getlength(name)
    d.text(((W - tw) / 2, H - 70), name, fill="#9E9E9E", font=f_foot)
    img.save(dst, "PNG")


def load_active_filenames() -> set[str]:
    """Return the set of filenames referenced by any slot_ref in the final content.jsonl.
    Used to prune orphaned placeholders/manifest entries after janitor trims the deck."""
    jsonl = ROOT / "slides" / "content.jsonl"
    names: set[str] = set()
    if not jsonl.exists():
        return names
    with open(jsonl, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            for ref in row.get("slot_refs", []):
                names.add(ref.split("/")[-1])
    return names


def make_text_only_sentinel(dst: Path) -> None:
    """Shared placeholder for text-only slides (janitor-introduced sentinel).
    Distinct from per-slot placeholders — just a neutral gray card with a label."""
    W, H = 1600, 900
    img = Image.new("RGB", (W, H), "#FAFAFA")
    d = ImageDraw.Draw(img)
    try:
        f_main = ImageFont.truetype(FONT_KR, 36)
    except OSError:
        f_main = ImageFont.load_default()
    txt = "텍스트 전용 슬라이드"
    tw = f_main.getlength(txt)
    d.text(((W - tw) / 2, H / 2 - 20), txt, fill="#BDBDBD", font=f_main)
    img.save(dst, "PNG")


def prune_orphans(keep: set[str]) -> tuple[int, int]:
    """Remove any annotated/placeholder PNGs whose filename is NOT in `keep`.
    Returns (deleted_annotated, deleted_placeholder) counts."""
    da = dp = 0
    for p in ANN_DIR.glob("*.png"):
        if p.name not in keep:
            p.unlink()
            da += 1
    for p in PH_DIR.glob("*.png"):
        if p.name not in keep:
            p.unlink()
            dp += 1
    return da, dp


def run() -> None:
    ANN_DIR.mkdir(parents=True, exist_ok=True)
    PH_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    bad_names: list[str] = []
    active = load_active_filenames()
    # Filter SLOTS down to only those still referenced in content.jsonl.
    # Keep the full slot table as the "plan" but produce assets only for active ones.
    active_slots = [s for s in SLOTS if s["name"] in active] if active else SLOTS

    for slot in active_slots:
        section = slot["section"]
        name = slot["name"]
        if not ok_filename(name):
            bad_names.append(name)
            continue

        raw = SHOT_DIR / section / name
        ann_dst = ANN_DIR / name
        ph_dst = PH_DIR / name

        status = "missing"

        # Special reuse: slot 45 and 54 in workflow_build come from phase_1_execution.png
        if section == "05_workflow_build" and name in {
            "45_workflow_build_execute_all_green.png",
            "54_workflow_build_final_diagram_7nodes.png",
        } and PHASE1.exists():
            callout_text = "모두 초록" if name.startswith("45") else "완성 흐름"
            recipe = _normalize([
                ("rect", (40, 180, 1680, 1060)),
                ("callout", 60, 1080, callout_text),
            ])
            annotate_one(PHASE1, ann_dst, recipe)
            status = "reused_from_phase_1"
        elif raw.exists() and name in ANN_RECIPES:
            annotate_one(raw, ann_dst, ANN_RECIPES[name])
            status = "annotated"
        elif raw.exists():
            annotate_one(raw, ann_dst, [])  # no recipe yet - just cropped
            status = "annotated"
        else:
            make_placeholder(name, ph_dst, slot["kind"])
            status = "placeholder"

        manifest.append(
            {
                "section": section,
                "filename": name,
                "status": status,
                "annotated_path": (
                    str(ann_dst.relative_to(ROOT))
                    if status in {"annotated", "reused_from_phase_1"}
                    else None
                ),
                "placeholder_path": (
                    str(ph_dst.relative_to(ROOT)) if status == "placeholder" else None
                ),
                "raw_path": (
                    str(raw.relative_to(ROOT))
                    if raw.exists() and section != "_reused"
                    else None
                ),
                "kind": slot["kind"],
            }
        )

    # Shared text-only sentinel (janitor-introduced): slides/assets/placeholder_text_only.png
    sentinel = ROOT / "slides" / "assets" / "placeholder_text_only.png"
    if "placeholder_text_only.png" in active:
        make_text_only_sentinel(sentinel)
        manifest.append({
            "section": "_shared",
            "filename": "placeholder_text_only.png",
            "status": "placeholder",
            "annotated_path": None,
            "placeholder_path": str(sentinel.relative_to(ROOT)),
            "raw_path": None,
            "kind": "text-only-sentinel",
        })

    # Prune orphaned PNGs on disk (files that aren't referenced by any slot_ref)
    keep = {m["filename"] for m in manifest}
    deleted_a, deleted_p = prune_orphans(keep)

    MANIFEST.write_text(json.dumps({"slots": manifest, "bad_names": bad_names}, ensure_ascii=False, indent=2))
    counts: dict[str, int] = {}
    for m in manifest:
        counts[m["status"]] = counts.get(m["status"], 0) + 1
    print("Manifest written:", MANIFEST)
    print("Totals:", counts)
    print(f"Orphans pruned: annotated={deleted_a}, placeholders={deleted_p}")
    print(f"Active slot_refs from content.jsonl: {len(active)}")
    if bad_names:
        print("REJECTED filenames:", bad_names)


if __name__ == "__main__":
    run()
