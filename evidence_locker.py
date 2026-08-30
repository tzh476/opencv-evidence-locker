"""Deterministic OpenCV evidence extraction for an agentic-vision spike."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


@dataclass(frozen=True)
class EvidenceCard:
    frame_index: int
    timestamp_ms: int
    change_score: float
    changed_regions: tuple[tuple[int, int, int, int], ...]
    previous_sha256: str
    frame_sha256: str


@dataclass(frozen=True)
class ReviewPlan:
    action: str
    reason: str
    triggering_frames: tuple[int, ...]


def frame_sha256(frame: np.ndarray) -> str:
    _validate_frame(frame)
    header = f"{frame.shape}:{frame.dtype.str}:".encode()
    return hashlib.sha256(header + frame.tobytes(order="C")).hexdigest()


def _validate_frame(frame: np.ndarray) -> None:
    if not isinstance(frame, np.ndarray):
        raise TypeError("frame must be a numpy array")
    if frame.dtype != np.uint8:
        raise ValueError("frame dtype must be uint8")
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("frame must have shape (height, width, 3)")
    if frame.shape[0] < 2 or frame.shape[1] < 2:
        raise ValueError("frame must be at least 2x2 pixels")


def _normalized_gray(frame: np.ndarray, size: tuple[int, int] = (160, 90)) -> np.ndarray:
    _validate_frame(frame)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, size, interpolation=cv2.INTER_AREA)


def change_score(previous: np.ndarray, current: np.ndarray) -> float:
    previous_gray = _normalized_gray(previous)
    current_gray = _normalized_gray(current)
    delta = cv2.absdiff(previous_gray, current_gray)
    return float(np.mean(delta) / 255.0)


def changed_regions(
    previous: np.ndarray,
    current: np.ndarray,
    *,
    pixel_threshold: int = 24,
    min_area: int = 16,
) -> tuple[tuple[int, int, int, int], ...]:
    _validate_frame(previous)
    _validate_frame(current)
    if previous.shape != current.shape:
        raise ValueError("frames must have identical shapes")
    if not 0 <= pixel_threshold <= 255:
        raise ValueError("pixel_threshold must be between 0 and 255")
    if min_area < 1:
        raise ValueError("min_area must be positive")

    previous_gray = cv2.cvtColor(previous, cv2.COLOR_BGR2GRAY)
    current_gray = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY)
    delta = cv2.absdiff(previous_gray, current_gray)
    _, mask = cv2.threshold(delta, pixel_threshold, 255, cv2.THRESH_BINARY)
    kernel = np.ones((3, 3), dtype=np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = [cv2.boundingRect(contour) for contour in contours if cv2.contourArea(contour) >= min_area]
    return tuple(sorted(regions, key=lambda box: (box[1], box[0], box[2], box[3])))


def analyze_frames(
    frames: Iterable[np.ndarray],
    *,
    fps: float,
    event_threshold: float = 0.02,
    reset_threshold: float | None = None,
) -> list[EvidenceCard]:
    if fps <= 0:
        raise ValueError("fps must be positive")
    if not 0 <= event_threshold <= 1:
        raise ValueError("event_threshold must be between 0 and 1")
    reset_threshold = event_threshold / 2 if reset_threshold is None else reset_threshold
    if not 0 <= reset_threshold < event_threshold:
        raise ValueError("reset_threshold must be non-negative and below event_threshold")

    iterator = iter(frames)
    try:
        previous = next(iterator)
    except StopIteration:
        return []
    _validate_frame(previous)

    cards: list[EvidenceCard] = []
    previous_hash = frame_sha256(previous)
    armed = True
    for frame_index, current in enumerate(iterator, start=1):
        _validate_frame(current)
        if previous.shape != current.shape:
            raise ValueError("all frames must have identical shapes")
        score = change_score(previous, current)
        current_hash = frame_sha256(current)
        if score < reset_threshold:
            armed = True
        if score >= event_threshold and armed:
            cards.append(
                EvidenceCard(
                    frame_index=frame_index,
                    timestamp_ms=round(frame_index * 1000 / fps),
                    change_score=round(score, 6),
                    changed_regions=changed_regions(previous, current),
                    previous_sha256=previous_hash,
                    frame_sha256=current_hash,
                )
            )
            armed = False
        previous = current
        previous_hash = current_hash
    return cards


def plan_review(cards: Iterable[EvidenceCard]) -> ReviewPlan:
    """Choose a bounded next action from OpenCV evidence only."""
    ordered = tuple(cards)
    if not ordered:
        return ReviewPlan(
            action="complete_no_material_change",
            reason="OpenCV found no frame transition above the configured threshold.",
            triggering_frames=(),
        )

    regionless = tuple(card.frame_index for card in ordered if not card.changed_regions)
    if regionless:
        return ReviewPlan(
            action="rerun_region_extraction_then_review",
            reason="Frame-level change crossed the event threshold but produced no reviewable region.",
            triggering_frames=regionless,
        )

    material = tuple(card.frame_index for card in ordered if card.change_score >= 0.25)
    if material:
        return ReviewPlan(
            action="request_human_approval",
            reason="At least one OpenCV transition changed 25% or more of normalized pixel intensity.",
            triggering_frames=material,
        )

    return ReviewPlan(
        action="seal_evidence_for_agent_summary",
        reason="OpenCV found localized changes that are reviewable without an immediate escalation.",
        triggering_frames=tuple(card.frame_index for card in ordered),
    )


def seal_report(report: dict[str, object]) -> str:
    canonical = json.dumps(report, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(canonical).hexdigest()


def analyze_video(
    path: Path,
    *,
    event_threshold: float = 0.02,
    reset_threshold: float | None = None,
) -> dict[str, object]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"unable to open video: {path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if fps <= 0:
        capture.release()
        raise ValueError("video reports no usable FPS")

    frames: list[np.ndarray] = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(frame)
    capture.release()

    effective_reset_threshold = event_threshold / 2 if reset_threshold is None else reset_threshold
    cards = analyze_frames(
        frames,
        fps=fps,
        event_threshold=event_threshold,
        reset_threshold=effective_reset_threshold,
    )
    plan = plan_review(cards)
    report: dict[str, object] = {
        "schema_version": 1,
        "opencv_version": cv2.__version__,
        "source": path.name,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "fps": fps,
        "frame_count": len(frames),
        "event_threshold": event_threshold,
        "reset_threshold": effective_reset_threshold,
        "evidence_cards": [asdict(card) for card in cards],
        "review_plan": asdict(plan),
    }
    report["receipt_sha256"] = seal_report(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--event-threshold", type=float, default=0.02)
    parser.add_argument("--reset-threshold", type=float)
    args = parser.parse_args()
    report = analyze_video(
        args.video,
        event_threshold=args.event_threshold,
        reset_threshold=args.reset_threshold,
    )
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
