"""Build the judge-facing Evidence Locker technical report PDF."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, Table, TableStyle


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "Evidence-Locker-Technical-Report.pdf"
PAGE_W, PAGE_H = A4

INK = colors.HexColor("#0B1020")
PANEL = colors.HexColor("#141B2E")
PANEL_2 = colors.HexColor("#1B243A")
MINT = colors.HexColor("#69F0C4")
BLUE = colors.HexColor("#65C8FF")
AMBER = colors.HexColor("#FFCF66")
ORANGE = colors.HexColor("#FF9F69")
WHITE = colors.HexColor("#F4F7FF")
MUTED = colors.HexColor("#A8B1C5")
GRID = colors.HexColor("#28334E")


def register_fonts() -> tuple[str, str]:
    regular_candidates = (
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    )
    bold_candidates = (
        "/System/Library/Fonts/SFNSDisplay-Bold.otf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    )
    regular = next((item for item in regular_candidates if Path(item).exists()), None)
    bold = next((item for item in bold_candidates if Path(item).exists()), None)
    if regular and bold:
        pdfmetrics.registerFont(TTFont("ReportRegular", regular))
        pdfmetrics.registerFont(TTFont("ReportBold", bold))
        return "ReportRegular", "ReportBold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = register_fonts()


def para_style(size: float = 10, color=MUTED, leading: float | None = None, bold: bool = False) -> ParagraphStyle:
    return ParagraphStyle(
        "body",
        fontName=FONT_BOLD if bold else FONT,
        fontSize=size,
        leading=leading or size * 1.42,
        textColor=color,
        alignment=TA_LEFT,
    )


def paragraph(canvas: Canvas, text: str, x: float, y_top: float, width: float, *, size: float = 10, color=MUTED, leading: float | None = None, bold: bool = False) -> float:
    item = Paragraph(text, para_style(size=size, color=color, leading=leading, bold=bold))
    _, height = item.wrap(width, PAGE_H)
    item.drawOn(canvas, x, y_top - height)
    return y_top - height


def page_base(canvas: Canvas, page: int, label: str, accent=MINT) -> None:
    canvas.setFillColor(INK)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setStrokeColor(colors.Color(accent.red, accent.green, accent.blue, alpha=0.08))
    canvas.setLineWidth(0.35)
    for x in range(0, int(PAGE_W), 18):
        canvas.line(x, 0, x, PAGE_H)
    for y in range(0, int(PAGE_H), 18):
        canvas.line(0, y, PAGE_W, y)

    canvas.setFillColor(accent)
    canvas.roundRect(18 * mm, PAGE_H - 23 * mm, 10 * mm, 10 * mm, 2.5 * mm, fill=1, stroke=0)
    canvas.setFillColor(INK)
    canvas.setFont(FONT_BOLD, 9)
    canvas.drawCentredString(23 * mm, PAGE_H - 17 * mm, "EL")
    canvas.setFillColor(WHITE)
    canvas.setFont(FONT_BOLD, 9)
    canvas.drawString(32 * mm, PAGE_H - 18 * mm, "EVIDENCE LOCKER")
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT, 7)
    canvas.drawRightString(PAGE_W - 18 * mm, PAGE_H - 18 * mm, label.upper())

    canvas.setStrokeColor(GRID)
    canvas.line(18 * mm, 15 * mm, PAGE_W - 18 * mm, 15 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT, 6.5)
    canvas.drawString(18 * mm, 10 * mm, "OpenCV 5 · deterministic evidence · bounded agent action")
    canvas.drawRightString(PAGE_W - 18 * mm, 10 * mm, f"{page:02d} / 07")


def heading(canvas: Canvas, eyebrow: str, title: str, *, accent=MINT, y: float = PAGE_H - 42 * mm) -> float:
    canvas.setFillColor(accent)
    canvas.setFont(FONT_BOLD, 8)
    canvas.drawString(18 * mm, y, eyebrow.upper())
    y -= 9 * mm
    canvas.setFillColor(WHITE)
    canvas.setFont(FONT_BOLD, 27)
    for line in title.split("\n"):
        canvas.drawString(18 * mm, y, line)
        y -= 11 * mm
    return y - 2 * mm


def card(canvas: Canvas, x: float, y: float, width: float, height: float, *, stroke=GRID, fill=PANEL) -> None:
    canvas.setFillColor(fill)
    canvas.setStrokeColor(stroke)
    canvas.setLineWidth(0.8)
    canvas.roundRect(x, y, width, height, 4 * mm, fill=1, stroke=1)


def metric(canvas: Canvas, x: float, y: float, value: str, label: str, *, accent=MINT) -> None:
    canvas.setFillColor(accent)
    canvas.setFont(FONT_BOLD, 22)
    canvas.drawString(x, y, value)
    paragraph(canvas, label, x, y - 7 * mm, 55 * mm, size=7.5)


def draw_cover(canvas: Canvas) -> None:
    page_base(canvas, 1, "Technical report · September 2026", MINT)
    y = PAGE_H - 48 * mm
    canvas.setFillColor(MINT)
    canvas.setFont(FONT_BOLD, 9)
    canvas.drawString(18 * mm, y, "OPEN CV 5 · AGENTIC VISION")
    y -= 18 * mm
    canvas.setFillColor(WHITE)
    canvas.setFont(FONT_BOLD, 35)
    canvas.drawString(18 * mm, y, "Evidence before")
    y -= 14 * mm
    canvas.drawString(18 * mm, y, "explanation.")
    y -= 15 * mm
    y = paragraph(
        canvas,
        "A reproducible OpenCV 5 pipeline that turns visual changes into sealed evidence, then lets a bounded agent rerun, seal, complete, or request human approval.",
        18 * mm,
        y,
        128 * mm,
        size=13,
        leading=18,
        color=MUTED,
    )

    top = 72 * mm
    card(canvas, 18 * mm, top, 174 * mm, 42 * mm, stroke=MINT)
    metric(canvas, 25 * mm, top + 25 * mm, "32 / 32", "local tests passed", accent=MINT)
    metric(canvas, 78 * mm, top + 25 * mm, "2 TP · 2 TN", "seeded smoke evaluation", accent=BLUE)
    metric(canvas, 139 * mm, top + 25 * mm, "SHA-256", "canonical evidence receipt", accent=colors.HexColor("#C39BFF"))

    canvas.setFillColor(AMBER)
    canvas.roundRect(18 * mm, 29 * mm, 174 * mm, 13 * mm, 3 * mm, fill=1, stroke=0)
    canvas.setFillColor(INK)
    canvas.setFont(FONT_BOLD, 8)
    canvas.drawString(24 * mm, 34 * mm, "STATUS")
    canvas.drawRightString(PAGE_W - 24 * mm, 34 * mm, "LOCAL + CONTAINER VERIFIED · AWS LIVE RUN PENDING")


def draw_system(canvas: Canvas) -> None:
    page_base(canvas, 2, "System overview", BLUE)
    y = heading(canvas, "ONE EVIDENCE PATH", "From video bytes\nto bounded action.", accent=BLUE)
    paragraph(canvas, "Observation, interpretation, and action are separate stages. The agent never substitutes prose for visual evidence.", 18 * mm, y, 165 * mm, size=11)

    stages = [
        ("01", "VIDEO", "OpenCV decodes frames + FPS"),
        ("02", "CHANGE", "absdiff + threshold + regions"),
        ("03", "EVIDENCE", "hashes + immutable overlay"),
        ("04", "POLICY", "one of four bounded actions"),
    ]
    x = 18 * mm
    y_box = 116 * mm
    for index, (number, label, detail) in enumerate(stages):
        width = 39 * mm
        card(canvas, x, y_box, width, 51 * mm, stroke=BLUE if index < 3 else AMBER)
        canvas.setFillColor(BLUE if index < 3 else AMBER)
        canvas.setFont(FONT_BOLD, 8)
        canvas.drawString(x + 5 * mm, y_box + 39 * mm, number)
        canvas.setFillColor(WHITE)
        canvas.setFont(FONT_BOLD, 12)
        canvas.drawString(x + 5 * mm, y_box + 25 * mm, label)
        paragraph(canvas, detail, x + 5 * mm, y_box + 18 * mm, width - 10 * mm, size=7.2)
        if index < len(stages) - 1:
            canvas.setFillColor(BLUE)
            canvas.setFont(FONT_BOLD, 14)
            canvas.drawString(x + width + 2 * mm, y_box + 24 * mm, "→")
        x += 44 * mm

    card(canvas, 18 * mm, 55 * mm, 174 * mm, 45 * mm, fill=PANEL_2)
    canvas.setFillColor(MINT)
    canvas.setFont(FONT_BOLD, 9)
    canvas.drawString(25 * mm, 88 * mm, "CORE INVARIANT")
    paragraph(canvas, "A later explanation may cite only known frame IDs and must preserve the action selected by the OpenCV evidence policy. Unknown citations or unapproved recommendations fail closed.", 25 * mm, 80 * mm, 155 * mm, size=11, color=WHITE)


def draw_opencv(canvas: Canvas) -> None:
    page_base(canvas, 3, "OpenCV 5 implementation", BLUE)
    y = heading(canvas, "SUBSTANTIVE VISION PIPELINE", "Decode. Compare.\nLocalize. Seal.", accent=BLUE)
    paragraph(canvas, "OpenCV 5.0.0.93 is pinned and used across decoding, comparison, localization, and review rendering.", 18 * mm, y, 165 * mm, size=11)

    rows = [
        ("1", "Decode", "VideoCapture reads frames and frame rate."),
        ("2", "Preview", "Grayscale + INTER_AREA downsampling."),
        ("3", "Compare", "Normalized absdiff produces a change score."),
        ("4", "Localize", "Threshold, morphology-close, contours, rectangles."),
        ("5", "Stabilize", "Hysteresis suppresses continuous-motion floods."),
        ("6", "Review", "Separate overlay; source frames stay unchanged."),
    ]
    start_y = 174 * mm
    for index, (number, name, detail) in enumerate(rows):
        row_y = start_y - index * 25 * mm
        card(canvas, 18 * mm, row_y, 174 * mm, 19 * mm, fill=PANEL)
        canvas.setFillColor(BLUE)
        canvas.circle(28 * mm, row_y + 9.5 * mm, 5 * mm, fill=1, stroke=0)
        canvas.setFillColor(INK)
        canvas.setFont(FONT_BOLD, 8)
        canvas.drawCentredString(28 * mm, row_y + 7.2 * mm, number)
        canvas.setFillColor(WHITE)
        canvas.setFont(FONT_BOLD, 10)
        canvas.drawString(39 * mm, row_y + 10.8 * mm, name)
        canvas.setFillColor(MUTED)
        canvas.setFont(FONT, 8)
        canvas.drawString(73 * mm, row_y + 10.8 * mm, detail)

    canvas.setFillColor(AMBER)
    canvas.setFont(FONT_BOLD, 8)
    canvas.drawString(18 * mm, 31 * mm, "ADVERSARIAL FIX")
    paragraph(canvas, "One public 125-frame clip initially produced 56 cards. Hysteresis reduced that to one without disabling re-arming after a quiet frame.", 18 * mm, 27 * mm, 174 * mm, size=8.8, color=WHITE)


def draw_policy(canvas: Canvas) -> None:
    page_base(canvas, 4, "Agentic decision boundary", AMBER)
    y = heading(canvas, "EVIDENCE CHANGES THE ACTION", "Four actions.\nNo invented fifth.", accent=AMBER)
    paragraph(canvas, "The planner is deterministic and fail-closed. Material transitions remain human-owned.", 18 * mm, y, 165 * mm, size=11)

    data = [
        ["OpenCV evidence", "Permitted action", "Reason"],
        ["No card over threshold", "complete_no_material_change", "No visual transition was extracted."],
        ["Card has no region", "rerun_region_extraction_then_review", "Do not summarize unlocalized evidence."],
        ["Localized card", "seal_evidence_for_agent_summary", "A later summary may cite the card."],
        ["Score ≥ 0.25", "request_human_approval", "A material transition requires a person."],
    ]
    table = Table(data, colWidths=[45 * mm, 68 * mm, 61 * mm], rowHeights=[13 * mm, 25 * mm, 25 * mm, 25 * mm, 25 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AMBER),
        ("TEXTCOLOR", (0, 0), (-1, 0), INK),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), PANEL),
        ("TEXTCOLOR", (0, 1), (-1, -1), WHITE),
        ("FONTNAME", (0, 1), (-1, -1), FONT),
        ("FONTSIZE", (0, 1), (-1, -1), 7.2),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    table.wrapOn(canvas, 174 * mm, PAGE_H)
    table.drawOn(canvas, 18 * mm, 79 * mm)

    card(canvas, 18 * mm, 32 * mm, 174 * mm, 31 * mm, stroke=colors.HexColor("#FF6C7A"), fill=PANEL_2)
    canvas.setFillColor(colors.HexColor("#FF7D88"))
    canvas.setFont(FONT_BOLD, 9)
    canvas.drawString(25 * mm, 52 * mm, "FAIL-CLOSED CHECK")
    paragraph(canvas, "The explanation module rejects unknown frame citations and recommendations that do not exactly match the bounded plan.", 25 * mm, 46 * mm, 155 * mm, size=9, color=WHITE)


def draw_evaluation(canvas: Canvas) -> None:
    page_base(canvas, 5, "Evaluation and reproducibility", MINT)
    y = heading(canvas, "SEEDED ENGINEERING SMOKE TEST", "Small test.\nExplicit limits.", accent=MINT)
    paragraph(canvas, "Four deterministic scenarios assert both event detection and the selected policy action.", 18 * mm, y, 165 * mm, size=11)

    data = [
        ["Scenario", "Expected event", "Detected", "Action"],
        ["No change", "No", "No (TN)", "complete"],
        ["Localized change", "Yes", "Yes (TP)", "seal"],
        ["Full-frame change", "Yes", "Yes (TP)", "human approval"],
        ["Low-amplitude noise", "No", "No (TN)", "complete"],
    ]
    table = Table(data, colWidths=[54 * mm, 38 * mm, 38 * mm, 44 * mm], rowHeights=[12 * mm] + [17 * mm] * 4)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), MINT),
        ("TEXTCOLOR", (0, 0), (-1, 0), INK),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("BACKGROUND", (0, 1), (-1, -1), PANEL),
        ("TEXTCOLOR", (0, 1), (-1, -1), WHITE),
        ("FONTNAME", (0, 1), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    table.wrapOn(canvas, 174 * mm, PAGE_H)
    table.drawOn(canvas, 18 * mm, 126 * mm)

    metric(canvas, 18 * mm, 111 * mm, "2 TP · 2 TN", "0 false positives · 0 false negatives", accent=MINT)
    metric(canvas, 93 * mm, 111 * mm, "4 / 4", "expected actions matched", accent=BLUE)

    canvas.setFillColor(WHITE)
    canvas.setFont(FONT_BOLD, 10)
    canvas.drawString(18 * mm, 79 * mm, "Public-sample checks")
    sample_data = [
        ["Frames", "Events", "Action"],
        ["125", "1", "seal evidence"],
        ["15", "1", "seal evidence"],
        ["54", "2", "seal evidence"],
    ]
    sample = Table(sample_data, colWidths=[42 * mm, 42 * mm, 90 * mm], rowHeights=[10 * mm] * 4)
    sample.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PANEL_2),
        ("TEXTCOLOR", (0, 0), (-1, 0), MINT),
        ("BACKGROUND", (0, 1), (-1, -1), PANEL),
        ("TEXTCOLOR", (0, 1), (-1, -1), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    sample.wrapOn(canvas, 174 * mm, PAGE_H)
    sample.drawOn(canvas, 18 * mm, 34 * mm)
    paragraph(canvas, "Limit: these are engineering gates and public-format checks, not a held-out real-world benchmark or production accuracy claim.", 18 * mm, 29 * mm, 174 * mm, size=7.7, color=AMBER)


def draw_aws(canvas: Canvas) -> None:
    page_base(canvas, 6, "Prepared AWS component", ORANGE)
    y = heading(canvas, "BOUNDED CLOUD DELIVERY", "Private input.\nEncrypted evidence.", accent=ORANGE)
    paragraph(canvas, "The SAM template and Lambda-compatible arm64 container are locally verified. A live AWS deployment remains pending.", 18 * mm, y, 165 * mm, size=11)

    items = [
        ("01", "PRIVATE S3", "incoming/*.mp4 only\nAES-256 at rest"),
        ("02", "ARM64 LAMBDA", "OpenCV 5 container\nreserved concurrency: 2"),
        ("03", "EVIDENCE S3", "canonical JSON receipt\nseparate encrypted bucket"),
    ]
    x = 18 * mm
    y_box = 125 * mm
    for index, (number, label, detail) in enumerate(items):
        width = 52 * mm
        card(canvas, x, y_box, width, 58 * mm, stroke=ORANGE if index == 1 else GRID)
        canvas.setFillColor(ORANGE)
        canvas.setFont(FONT_BOLD, 8)
        canvas.drawCentredString(x + width / 2, y_box + 44 * mm, number)
        canvas.setFillColor(WHITE)
        canvas.setFont(FONT_BOLD, 11)
        canvas.drawCentredString(x + width / 2, y_box + 30 * mm, label)
        paragraph(canvas, detail.replace("\n", "<br/>"), x + 6 * mm, y_box + 22 * mm, width - 12 * mm, size=7.5, color=MUTED)
        if index < 2:
            canvas.setFillColor(ORANGE)
            canvas.setFont(FONT_BOLD, 15)
            canvas.drawString(x + width + 4 * mm, y_box + 28 * mm, "→")
        x += 61 * mm

    controls = [
        "Reject multiple S3 records and output-recursion events.",
        "Default object retention: 7 days; configurable 1–30 days.",
        "CloudWatch log retention: 14 days.",
        "No public buckets; report location returned by Lambda invocation.",
        "Right-cleared demo media only; deployment claims require live proof.",
    ]
    card(canvas, 18 * mm, 40 * mm, 174 * mm, 66 * mm, fill=PANEL_2)
    canvas.setFillColor(ORANGE)
    canvas.setFont(FONT_BOLD, 9)
    canvas.drawString(25 * mm, 94 * mm, "RESPONSIBLE OPERATING BOUNDARY")
    y_line = 82 * mm
    for item in controls:
        canvas.setFillColor(ORANGE)
        canvas.circle(28 * mm, y_line + 1.5 * mm, 1.2 * mm, fill=1, stroke=0)
        paragraph(canvas, item, 34 * mm, y_line + 4 * mm, 145 * mm, size=8.3, color=WHITE)
        y_line -= 10 * mm


def draw_close(canvas: Canvas) -> None:
    page_base(canvas, 7, "Limitations and reproducibility", MINT)
    y = heading(canvas, "RESPONSIBLE AGENTIC VISION", "See the change.\nVerify the action.", accent=MINT)
    paragraph(canvas, "Evidence Locker is designed for inspection and review workflows where source frames, changed regions, and the reason for a next action must remain auditable.", 18 * mm, y, 165 * mm, size=11)

    canvas.setFillColor(WHITE)
    canvas.setFont(FONT_BOLD, 11)
    canvas.drawString(18 * mm, 181 * mm, "Known limits")
    limits = [
        "Change detection is not object recognition, identity verification, intent inference, or a safety-critical anomaly detector.",
        "Thresholds are content-dependent; subtle changes can be missed and camera motion or illumination can trigger events.",
        "The four-case suite is deliberately smoke-sized. Production use needs a right-cleared, held-out evaluation set.",
        "Hashes prove byte-level integrity, not the real-world meaning of a scene.",
        "Material transitions route to human approval; the agent cannot authorize irreversible actions.",
    ]
    y_line = 171 * mm
    for item in limits:
        canvas.setFillColor(MINT)
        canvas.circle(21 * mm, y_line + 1.5 * mm, 1.2 * mm, fill=1, stroke=0)
        y_line = paragraph(canvas, item, 27 * mm, y_line + 4 * mm, 158 * mm, size=8.4, color=WHITE) - 4 * mm

    card(canvas, 18 * mm, 56 * mm, 174 * mm, 61 * mm, fill=PANEL_2)
    canvas.setFillColor(MINT)
    canvas.setFont(FONT_BOLD, 9)
    canvas.drawString(25 * mm, 104 * mm, "REPRODUCE")
    commands = [
        "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt",
        ".venv/bin/python -m unittest -v",
        ".venv/bin/python evaluate_synthetic.py",
        "docker build --platform linux/arm64 -t evidence-locker .",
    ]
    y_cmd = 92 * mm
    canvas.setFont("Courier", 7)
    canvas.setFillColor(WHITE)
    for command in commands:
        canvas.drawString(25 * mm, y_cmd, command)
        y_cmd -= 8 * mm

    canvas.setFillColor(WHITE)
    canvas.setFont(FONT_BOLD, 9)
    canvas.drawString(18 * mm, 43 * mm, "SOURCE")
    canvas.setFillColor(BLUE)
    canvas.setFont(FONT, 8)
    canvas.drawString(42 * mm, 43 * mm, "github.com/tzh476/opencv-evidence-locker")
    canvas.setFillColor(AMBER)
    canvas.setFont(FONT_BOLD, 7.5)
    canvas.drawString(18 * mm, 31 * mm, "NO AWARD OR PAYMENT CLAIMED · LIVE AWS EVIDENCE WILL BE ADDED ONLY AFTER VERIFICATION")


def build() -> Path:
    canvas = Canvas(str(OUT), pagesize=A4, pageCompression=1)
    canvas.setTitle("Evidence Locker — OpenCV 5 Agentic Vision Technical Report")
    canvas.setAuthor("tzh476")
    for draw in (draw_cover, draw_system, draw_opencv, draw_policy, draw_evaluation, draw_aws, draw_close):
        draw(canvas)
        canvas.showPage()
    canvas.save()
    return OUT


if __name__ == "__main__":
    print(build())
