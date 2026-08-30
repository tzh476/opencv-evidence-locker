import unittest

from evidence_locker import EvidenceCard, ReviewPlan
from explanation_agent import explain, validate_explanation


def card(frame_index: int = 2) -> EvidenceCard:
    return EvidenceCard(
        frame_index=frame_index,
        timestamp_ms=200,
        change_score=0.125,
        changed_regions=((1, 2, 10, 12),),
        previous_sha256="a" * 64,
        frame_sha256="b" * 64,
    )


def plan(action: str = "seal_evidence_for_agent_summary") -> ReviewPlan:
    return ReviewPlan(action=action, reason="Bounded policy.", triggering_frames=(2,))


class ExplanationAgentTest(unittest.TestCase):
    def test_deterministic_explanation_cites_evidence(self) -> None:
        first = explain([card()], plan())
        second = explain([card()], plan())
        self.assertEqual(first, second)
        self.assertEqual(first.cited_frame_indices, (2,))
        self.assertEqual(first.recommended_action, "seal_evidence_for_agent_summary")
        self.assertRegex(first.explanation_sha256, r"^[0-9a-f]{64}$")

    def test_unknown_frame_claim_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown frames"):
            validate_explanation(
                [card()],
                plan(),
                summary="Invented frame claim.",
                cited_frame_indices=[999],
                recommended_action="seal_evidence_for_agent_summary",
            )

    def test_unbounded_action_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "bounded review plan"):
            validate_explanation(
                [card()],
                plan(),
                summary="Attempt to bypass policy.",
                cited_frame_indices=[2],
                recommended_action="auto_publish_and_delete_source",
            )

    def test_no_change_explanation_has_no_citations(self) -> None:
        no_change_plan = ReviewPlan(
            action="complete_no_material_change",
            reason="No event.",
            triggering_frames=(),
        )
        result = explain([], no_change_plan)
        self.assertEqual(result.cited_frame_indices, ())
        self.assertIn("No OpenCV transition", result.summary)


if __name__ == "__main__":
    unittest.main()
