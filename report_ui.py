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
<title>Evidence Locker · Agentic Vision Review</title>
<style>
:root{{color-scheme:dark;--bg:#07101c;--panel:#111d2d;--line:#263950;--ink:#eef6ff;--muted:#9eb0c4;--mint:#68f6c3;--amber:#ffcb69}}
*{{box-sizing:border-box}}
body{{font:16px/1.6 Inter,ui-sans-serif,system-ui,sans-serif;margin:0;background:radial-gradient(circle at 15% 0,#15304a 0,transparent 36rem),var(--bg);color:var(--ink)}}
main{{max-width:1120px;margin:auto;padding:64px 28px 80px}}
.hero{{padding:32px 0 40px}}
.eyebrow{{color:var(--mint);font-size:.78rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase}}
h1{{font-size:clamp(2.8rem,7vw,5.8rem);line-height:.95;letter-spacing:-.055em;margin:.2em 0}}
h2,h3{{line-height:1.15}} .lede{{max-width:760px;color:var(--muted);font-size:1.12rem}} .source{{color:var(--muted)}}
.badges{{display:flex;flex-wrap:wrap;gap:8px;margin-top:22px}} .badges span{{border:1px solid var(--line);border-radius:999px;padding:5px 11px;color:var(--muted);font-size:.82rem}}
.decision,.card{{background:linear-gradient(145deg,rgba(25,42,64,.96),rgba(13,25,40,.96));border:1px solid var(--line);border-radius:18px;padding:26px;margin:18px 0;box-shadow:0 18px 50px rgba(0,0,0,.18)}}
.decision{{border-color:#8b713c}} .decision h2{{color:var(--amber);font-family:ui-monospace,monospace;font-size:clamp(1.1rem,3vw,1.65rem)}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px}}
.card{{margin:0}} code{{display:block;overflow-wrap:anywhere;color:#9dc5ff;margin-top:8px;font-size:.75rem}}
img{{display:block;width:100%;height:auto;border-radius:12px;margin:18px 0;border:1px solid var(--line)}}
.receipt{{font-family:ui-monospace,monospace;overflow-wrap:anywhere;color:var(--muted);margin:28px 0}} a{{color:var(--mint)}}
@media(max-width:600px){{main{{padding:32px 18px 56px}}.decision,.card{{padding:20px}}}}
</style>
<main>
<header class="hero">
<p class="eyebrow">OpenCV 5 · bounded agentic vision</p>
<h1>Evidence Locker</h1>
<p class="lede">Deterministic visual-change evidence controls what the agent may do next. Every decision remains inspectable, hash-addressed, and bounded by human review.</p>
<p class="source">Source: <strong>{_text(report.get('source', 'unknown'))}</strong></p>
<div class="badges"><span>OpenCV {_text(report.get('opencv_version'))}</span><span>{_text(report.get('frame_count', 'unknown'))} frames</span><span>{_text(len(cards))} evidence card(s)</span><span>sealed receipt</span></div>
</header>
<section class="decision">
<h2>{_text(plan.get('action'))}</h2>
<p>{_text(plan.get('reason'))}</p>
<p>Triggering frames: {_text(plan.get('triggering_frames', []))}</p>
<h3>Bounded explanation</h3>
<p>{_text(explanation.get('summary'))}</p>
<p>Cited frames: {_text(explanation.get('cited_frame_indices', []))}</p>
<code>explanation {_text(explanation.get('explanation_sha256'))}</code>
</section>
<section class="cards">{''.join(card_sections) or '<p>No material change evidence.</p>'}</section>
<p class="receipt">Report receipt · {_text(receipt)}</p>
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
