"""Render a sealed evidence report into a standalone human-review HTML file."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


def _text(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_report_html(report: dict[str, Any]) -> str:
    receipt = report.get("receipt_sha256")
    plan = report.get("review_plan")
    explanation = report.get("explanation")
    cards = report.get("evidence_cards")
    overlays = report.get("overlays", [])
    if not isinstance(receipt, str) or len(receipt) != 64:
        raise ValueError("report receipt_sha256 is required")
    if (
        not isinstance(plan, dict)
        or not isinstance(explanation, dict)
        or not isinstance(cards, list)
        or not isinstance(overlays, list)
    ):
        raise ValueError("report must include review_plan, explanation, evidence_cards, and overlays")

    overlay_by_frame = {
        item.get("frame_index"): item
        for item in overlays
        if isinstance(item, dict) and isinstance(item.get("filename"), str)
    }
    card_sections: list[str] = []
    for card in cards:
        if not isinstance(card, dict):
            raise ValueError("evidence card must be an object")
        frame_index = card.get("frame_index")
        overlay = overlay_by_frame.get(frame_index)
        overlay_html = ""
        if overlay:
            overlay_html = (
                f'<img src="{_text(overlay["filename"])}" '
                f'alt="Review overlay for frame {_text(frame_index)}">'
            )
        regions = card.get("changed_regions", [])
        card_sections.append(
            "<article class=\"card\">"
            f"<h3>Frame {_text(frame_index)}</h3>"
            f"<p>Timestamp: {_text(card.get('timestamp_ms'))} ms · "
            f"Change: {_text(card.get('change_score'))} · Regions: {_text(len(regions))}</p>"
            f"{overlay_html}"
            f"<code>previous {_text(card.get('previous_sha256'))}</code>"
            f"<code>current {_text(card.get('frame_sha256'))}</code>"
            "</article>"
        )

    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agentic Vision Evidence Review</title>
<style>
body{{font:16px system-ui;margin:0;background:#0b1020;color:#e8eefc}}
main{{max-width:960px;margin:auto;padding:32px}}
.decision,.card{{background:#151d33;border:1px solid #344260;border-radius:12px;padding:20px;margin:16px 0}}
.decision{{border-color:#f4b942}} code{{display:block;overflow-wrap:anywhere;color:#9dc5ff;margin-top:8px}}
img{{display:block;max-width:100%;height:auto;border-radius:8px;margin:12px 0}}
.receipt{{font-family:ui-monospace,monospace;overflow-wrap:anywhere}}
</style>
<main>
<h1>Agentic Vision Evidence Review</h1>
<p>Source: <strong>{_text(report.get('source', 'unknown'))}</strong> · OpenCV {_text(report.get('opencv_version'))}</p>
<section class="decision">
<h2>{_text(plan.get('action'))}</h2>
<p>{_text(plan.get('reason'))}</p>
<p>Triggering frames: {_text(plan.get('triggering_frames', []))}</p>
<h3>Bounded explanation</h3>
<p>{_text(explanation.get('summary'))}</p>
<p>Cited frames: {_text(explanation.get('cited_frame_indices', []))}</p>
<code>explanation {_text(explanation.get('explanation_sha256'))}</code>
</section>
<section>{''.join(card_sections) or '<p>No material change evidence.</p>'}</section>
<p class="receipt">Report receipt: {_text(receipt)}</p>
</main>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    args.output.write_text(render_report_html(report))


if __name__ == "__main__":
    main()
