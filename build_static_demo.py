"""Build a deterministic, read-only Evidence Locker demo for static hosting."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np

from evidence_locker import analyze_frames, frame_sha256, plan_review, render_overlay, seal_report
from explanation_agent import as_report_block, explain
from report_ui import render_report_html


def build_demo(output_dir: Path) -> dict[str, object]:
    """Write one deterministic synthetic review package and return its report."""
    output_dir.mkdir(parents=True, exist_ok=True)

    previous = np.zeros((540, 960, 3), dtype=np.uint8)
    current = previous.copy()
    cv2.rectangle(current, (180, 160), (499, 359), (255, 255, 255), thickness=-1)
    cv2.circle(current, (700, 270), 70, (120, 220, 255), thickness=-1)

    cards = analyze_frames([previous, current], fps=10, event_threshold=0.02)
    if len(cards) != 1:
        raise RuntimeError(f"expected one synthetic evidence card, got {len(cards)}")
    plan = plan_review(cards)
    explanation = explain(cards, plan)

    overlay_name = "evidence-frame-000001.png"
    overlay_path = output_dir / overlay_name
    if not cv2.imwrite(str(overlay_path), render_overlay(current, cards[0])):
        raise OSError(f"unable to write overlay: {overlay_path}")

    source_receipt = hashlib.sha256(
        (frame_sha256(previous) + frame_sha256(current)).encode()
    ).hexdigest()
    report: dict[str, object] = {
        "schema_version": 1,
        "opencv_version": cv2.__version__,
        "source": "deterministic synthetic transition",
        "source_sha256": source_receipt,
        "fps": 10.0,
        "frame_count": 2,
        "event_threshold": 0.02,
        "reset_threshold": 0.01,
        "evidence_cards": [asdict(card) for card in cards],
        "explanation": as_report_block(explanation),
        "overlays": [
            {
                "frame_index": cards[0].frame_index,
                "filename": overlay_name,
                "sha256": hashlib.sha256(overlay_path.read_bytes()).hexdigest(),
            }
        ],
        "review_plan": asdict(plan),
    }
    report["receipt_sha256"] = seal_report(report)

    (output_dir / "evidence.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    html = render_report_html(report).replace(
        "</main>",
        '<p><a href="evidence.json">Download the canonical evidence JSON</a>'
        ' · <a href="https://github.com/tzh476/opencv-evidence-locker">'
        "Source, tests, architecture, and technical report</a></p></main>",
    )
    (output_dir / "index.html").write_text(html)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("docs"))
    args = parser.parse_args()
    report = build_demo(args.output_dir)
    print(json.dumps({"receipt_sha256": report["receipt_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
