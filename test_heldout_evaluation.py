import hashlib
import json
import unittest
from pathlib import Path

import numpy as np

from build_evaluation_page import render
from evaluate_heldout import confusion, foreground, metrics, reference_label
from evidence_locker import seal_report

ROOT = Path(__file__).parent


class EvaluationTest(unittest.TestCase):
    def test_undefined_metrics_are_not_perfect_scores(self):
        result = metrics([{"outcome": "TN"}, {"outcome": "ambiguous"}])
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["recall"])
        self.assertEqual(result["scored"], 1)
        self.assertEqual(result["ambiguous"], 1)

    def test_confusion_counts_keep_errors_and_ambiguous_separate(self):
        rows = [{"outcome": confusion(expected, detected)} for expected, detected in
                ((True, True), (True, False), (False, True), (False, False), (None, True))]
        result = metrics(rows)
        self.assertEqual([result[key] for key in ("TP", "FN", "FP", "TN", "ambiguous")], [1]*5)
        self.assertEqual(result["recall"], .5)
        self.assertEqual(result["precision"], .5)

    def test_reference_boundaries_and_id_change(self):
        protocol = {"positive_mask_xor_fraction": .005, "negative_mask_xor_fraction": .001}
        before = np.zeros((100, 100), np.uint8)
        for count, expected in ((10, False), (11, None), (49, None), (50, True)):
            after = before.copy()
            after.flat[:count] = 1
            label, _ = reference_label(before, after, protocol)
            self.assertIs(label, expected)
        before[:20] = 1
        after = before.copy()
        after[:20] = 2
        self.assertEqual(reference_label(before, after, protocol), (False, 0))

    def test_color_annotations_keep_foreground_without_id_semantics(self):
        mask = np.zeros((2, 2, 3), np.uint8)
        mask[0, 1] = [0, 128, 0]
        self.assertEqual(foreground(mask).tolist(), [[False, True], [False, False]])
        with self.assertRaisesRegex(ValueError, "shapes"):
            reference_label(mask, np.zeros((3, 3), np.uint8), {})

    @unittest.skipUnless((ROOT / "docs/evaluation/results.json").exists(), "hosted evaluation assets are not in the runtime image")
    def test_published_artifact_receipt_counts_and_source_binding(self):
        report = json.loads((ROOT / "docs/evaluation/results.json").read_text())
        receipt = report.pop("receipt_sha256")
        self.assertEqual(seal_report(report), receipt)
        self.assertEqual(report["real_pairs"], metrics(report["real_results"]))
        self.assertEqual(report["controls"], metrics(report["control_results"]))
        self.assertEqual(len(report["source_manifest"]["files"]), 144)
        self.assertEqual(report["protocol_sha256"], hashlib.sha256((ROOT / "evaluation/protocol.json").read_bytes()).hexdigest())
        self.assertEqual(report["detector_sha256"], hashlib.sha256((ROOT / "evidence_locker.py").read_bytes()).hexdigest())
        self.assertEqual(len(report["real_results"]), 36)
        self.assertEqual(len(report["control_results"]), 36)
        for row in report["real_results"]:
            self.assertEqual(row["annotation_preview_sha256"], hashlib.sha256((ROOT / "docs/evaluation" / row["annotation_preview"]).read_bytes()).hexdigest())

    @unittest.skipUnless((ROOT / "docs/evaluation/results.json").exists(), "hosted evaluation assets are not in the runtime image")
    def test_page_escapes_evidence_and_refuses_tampering(self):
        report = json.loads((ROOT / "docs/evaluation/results.json").read_text())
        self.assertIn("real-video false-positive rate cannot be estimated", render(report))
        report["real_results"][0]["review_plan"]["reason"] = '<img src=x onerror="alert(1)">'
        with self.assertRaisesRegex(ValueError, "receipt"):
            render(report)
        report.pop("receipt_sha256")
        report["receipt_sha256"] = seal_report(report)
        page = render(report)
        self.assertNotIn('<img src=x onerror=', page)
        self.assertIn('&lt;img src=x', page)


if __name__ == "__main__":
    unittest.main()
