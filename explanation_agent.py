"""Fail-closed explanation boundary over OpenCV evidence cards."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Iterable

from evidence_locker import EvidenceCard, ReviewPlan


@dataclass(frozen=True)
class EvidenceExplanation:
    summary: str
    cited_frame_indices: tuple[int, ...]
    recommended_action: str
    explanation_sha256: str


def _seal(summary: str, cited_frame_indices: tuple[int, ...], recommended_action: str) -> str:
    body = {
        "summary": summary,
        "cited_frame_indices": cited_frame_indices,
        "recommended_action": recommended_action,
    }
    return hashlib.sha256(json.dumps(body, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def validate_explanation(
    cards: Iterable[EvidenceCard],
    plan: ReviewPlan,
    *,
    summary: str,
    cited_frame_indices: Iterable[int],
    recommended_action: str,
) -> EvidenceExplanation:
    evidence = tuple(cards)
    citations = tuple(cited_frame_indices)
    known_frames = {card.frame_index for card in evidence}
    unknown = tuple(frame for frame in citations if frame not in known_frames)
    if unknown:
        raise ValueError(f"explanation cites unknown frames: {unknown}")
    if evidence and not citations:
        raise ValueError("explanation must cite at least one evidence frame")
    if not evidence and citations:
        raise ValueError("no-change explanation cannot cite a frame")
    if recommended_action != plan.action:
        raise ValueError("explanation action must match the bounded review plan")
    if not summary.strip():
        raise ValueError("explanation summary is required")
    return EvidenceExplanation(
        summary=summary.strip(),
        cited_frame_indices=citations,
        recommended_action=recommended_action,
        explanation_sha256=_seal(summary.strip(), citations, recommended_action),
    )


def explain(cards: Iterable[EvidenceCard], plan: ReviewPlan) -> EvidenceExplanation:
    evidence = tuple(cards)
    if not evidence:
        summary = "No OpenCV transition crossed the configured event threshold."
        citations: tuple[int, ...] = ()
    else:
        citations = tuple(card.frame_index for card in evidence)
        max_change = max(card.change_score for card in evidence)
        region_count = sum(len(card.changed_regions) for card in evidence)
        summary = (
            f"OpenCV produced {len(evidence)} evidence card(s) with "
            f"{region_count} review region(s); maximum normalized change was {max_change:.6f}."
        )
    return validate_explanation(
        evidence,
        plan,
        summary=summary,
        cited_frame_indices=citations,
        recommended_action=plan.action,
    )


def as_report_block(explanation: EvidenceExplanation) -> dict[str, object]:
    return asdict(explanation)
