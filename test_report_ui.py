import unittest

from report_ui import render_report_html


def sample_report() -> dict[str, object]:
    return {
        "source": "sample.mp4",
        "opencv_version": "5.0.0",
        "receipt_sha256": "a" * 64,
        "review_plan": {
            "action": "request_human_approval",
            "reason": "Material visual transition.",
            "triggering_frames": [3],
        },
        "explanation": {
            "summary": "One cited visual transition.",
            "cited_frame_indices": [3],
            "recommended_action": "request_human_approval",
            "explanation_sha256": "e" * 64,
        },
        "evidence_cards": [
            {
                "frame_index": 3,
                "timestamp_ms": 300,
                "change_score": 0.5,
                "changed_regions": [[1, 2, 3, 4]],
                "previous_sha256": "b" * 64,
                "frame_sha256": "c" * 64,
            }
        ],
        "overlays": [
            {
                "frame_index": 3,
                "filename": "frame-000003.png",
                "sha256": "d" * 64,
            }
        ],
    }


class ReportUiTest(unittest.TestCase):
    def test_renders_decision_receipt_hashes_and_overlay(self) -> None:
        rendered = render_report_html(sample_report())
        self.assertIn("request_human_approval", rendered)
        self.assertIn("Material visual transition.", rendered)
        self.assertIn("One cited visual transition.", rendered)
        self.assertIn("frame-000003.png", rendered)
        self.assertIn("a" * 64, rendered)
        self.assertIn("b" * 64, rendered)
        self.assertIn("c" * 64, rendered)

    def test_escapes_untrusted_report_text(self) -> None:
        report = sample_report()
        report["source"] = '<script>alert("x")</script>'
        report["review_plan"]["reason"] = "<img src=x onerror=alert(1)>"
        rendered = render_report_html(report)
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("<img src=x", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("&lt;img", rendered)

    def test_rejects_missing_receipt(self) -> None:
        report = sample_report()
        report.pop("receipt_sha256")
        with self.assertRaisesRegex(ValueError, "receipt"):
            render_report_html(report)


if __name__ == "__main__":
    unittest.main()
