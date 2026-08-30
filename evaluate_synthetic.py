"""Reproducible synthetic evaluation for the bounded OpenCV 5 spike."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import cv2
import numpy as np

from evidence_locker import analyze_frames, plan_review, seal_report


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    expected_event: bool
    detected_event: bool
    expected_action: str
    actual_action: str


def evaluate() -> dict[str, object]:
    black = np.zeros((100, 160, 3), dtype=np.uint8)

    localized = black.copy()
    cv2.rectangle(localized, (20, 30), (59, 59), (255, 255, 255), thickness=-1)

    full = np.full_like(black, 255)

    rng = np.random.default_rng(20260831)
    low_noise = rng.integers(0, 4, size=black.shape, dtype=np.uint8)

    scenarios = (
        ("no_change", black.copy(), False, "complete_no_material_change"),
        ("localized_change", localized, True, "seal_evidence_for_agent_summary"),
        ("full_frame_change", full, True, "request_human_approval"),
        ("low_amplitude_noise", low_noise, False, "complete_no_material_change"),
    )

    results: list[ScenarioResult] = []
    for name, current, expected_event, expected_action in scenarios:
        cards = analyze_frames([black, current], fps=10, event_threshold=0.02)
        plan = plan_review(cards)
        results.append(
            ScenarioResult(
                name=name,
                expected_event=expected_event,
                detected_event=bool(cards),
                expected_action=expected_action,
                actual_action=plan.action,
            )
        )

    true_positive = sum(item.expected_event and item.detected_event for item in results)
    true_negative = sum(not item.expected_event and not item.detected_event for item in results)
    false_positive = sum(not item.expected_event and item.detected_event for item in results)
    false_negative = sum(item.expected_event and not item.detected_event for item in results)
    action_matches = sum(item.expected_action == item.actual_action for item in results)

    report: dict[str, object] = {
        "schema_version": 1,
        "seed": 20260831,
        "scenario_count": len(results),
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "action_accuracy": action_matches / len(results),
        "scenarios": [asdict(item) for item in results],
    }
    report["receipt_sha256"] = seal_report(report)
    return report


def main() -> None:
    print(json.dumps(evaluate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
