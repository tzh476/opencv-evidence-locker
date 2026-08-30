import unittest

import cv2
import numpy as np

from evidence_locker import EvidenceCard, analyze_frames, changed_regions, frame_sha256, plan_review, seal_report
from evaluate_synthetic import evaluate


class EvidenceLockerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.black = np.zeros((100, 160, 3), dtype=np.uint8)

    def test_unchanged_frames_create_no_event(self) -> None:
        cards = analyze_frames([self.black, self.black.copy()], fps=10)
        self.assertEqual(cards, [])

    def test_changed_region_creates_deterministic_evidence(self) -> None:
        changed = self.black.copy()
        cv2.rectangle(changed, (20, 30), (79, 69), (255, 255, 255), thickness=-1)

        first = analyze_frames([self.black, changed], fps=10, event_threshold=0.01)
        second = analyze_frames([self.black, changed], fps=10, event_threshold=0.01)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].frame_index, 1)
        self.assertEqual(first[0].timestamp_ms, 100)
        self.assertEqual(first[0].changed_regions, ((20, 30, 60, 40),))
        self.assertEqual(first[0].frame_sha256, frame_sha256(changed))
        self.assertNotEqual(first[0].previous_sha256, first[0].frame_sha256)

    def test_multiple_regions_are_sorted_for_stable_output(self) -> None:
        changed = self.black.copy()
        cv2.rectangle(changed, (100, 60), (129, 79), (255, 255, 255), thickness=-1)
        cv2.rectangle(changed, (10, 10), (29, 29), (255, 255, 255), thickness=-1)
        self.assertEqual(changed_regions(self.black, changed), ((10, 10, 20, 20), (100, 60, 30, 20)))

    def test_shape_mismatch_is_rejected(self) -> None:
        other = np.zeros((80, 160, 3), dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, "identical shapes"):
            analyze_frames([self.black, other], fps=10)

    def test_invalid_dtype_is_rejected(self) -> None:
        invalid = self.black.astype(np.float32)
        with self.assertRaisesRegex(ValueError, "dtype"):
            frame_sha256(invalid)

    def test_no_change_plan_completes_without_escalation(self) -> None:
        plan = plan_review([])
        self.assertEqual(plan.action, "complete_no_material_change")
        self.assertEqual(plan.triggering_frames, ())

    def test_material_change_plan_requests_human_approval(self) -> None:
        changed = self.black.copy()
        changed[:] = 255
        cards = analyze_frames([self.black, changed], fps=10)
        plan = plan_review(cards)
        self.assertEqual(plan.action, "request_human_approval")
        self.assertEqual(plan.triggering_frames, (1,))

    def test_regionless_event_fails_closed_into_rerun(self) -> None:
        card = EvidenceCard(
            frame_index=4,
            timestamp_ms=400,
            change_score=0.1,
            changed_regions=(),
            previous_sha256="a" * 64,
            frame_sha256="b" * 64,
        )
        plan = plan_review([card])
        self.assertEqual(plan.action, "rerun_region_extraction_then_review")
        self.assertEqual(plan.triggering_frames, (4,))

    def test_report_seal_is_order_independent(self) -> None:
        self.assertEqual(seal_report({"b": 2, "a": 1}), seal_report({"a": 1, "b": 2}))

    def test_synthetic_evaluation_has_no_fp_or_fn(self) -> None:
        report = evaluate()
        self.assertEqual(report["false_positive"], 0)
        self.assertEqual(report["false_negative"], 0)
        self.assertEqual(report["action_accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
