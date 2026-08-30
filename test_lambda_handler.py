import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lambda_handler import _output_key, _source_from_event, handler


class FakeS3:
    def __init__(self, source: Path) -> None:
        self.source = source
        self.uploaded: tuple[str, str, str, dict[str, str]] | None = None

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        self.downloaded = (bucket, key)
        Path(filename).write_bytes(self.source.read_bytes())

    def upload_file(
        self,
        filename: str,
        bucket: str,
        key: str,
        ExtraArgs: dict[str, str],
    ) -> None:
        self.uploaded_body = json.loads(Path(filename).read_text())
        self.uploaded = (filename, bucket, key, ExtraArgs)


def s3_event(bucket: str = "input-bucket", key: str = "incoming/demo.mp4") -> dict[str, object]:
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": key, "eTag": "abc123"},
                }
            }
        ]
    }


class LambdaHandlerTest(unittest.TestCase):
    def test_event_requires_exactly_one_record(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly one"):
            _source_from_event({"Records": []})

    def test_output_key_is_deterministic_and_namespaced(self) -> None:
        first = _output_key("bucket", "incoming/a.mp4", "etag")
        second = _output_key("bucket", "incoming/a.mp4", "etag")
        self.assertEqual(first, second)
        self.assertRegex(first, r"^reports/[0-9a-f]{64}\.json$")

    def test_generated_report_event_is_rejected(self) -> None:
        with patch.dict(os.environ, {"EVIDENCE_OUTPUT_BUCKET": "evidence"}, clear=True):
            with self.assertRaisesRegex(ValueError, "generated report"):
                handler(s3_event(bucket="evidence", key="reports/a.json"), None, s3_client=object())

    def test_handler_downloads_analyzes_and_uploads_encrypted_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            source.write_bytes(b"bounded fixture")
            fake_s3 = FakeS3(source)
            fake_report = {"receipt_sha256": "f" * 64, "evidence_cards": []}
            with patch.dict(os.environ, {"EVIDENCE_OUTPUT_BUCKET": "evidence"}, clear=True):
                with patch("lambda_handler.analyze_video", return_value=fake_report):
                    result = handler(s3_event(key="incoming%2Fdemo.mp4"), None, s3_client=fake_s3)

            self.assertEqual(fake_s3.downloaded, ("input-bucket", "incoming/demo.mp4"))
            self.assertEqual(result["status"], "report_written")
            self.assertEqual(result["report_receipt_sha256"], "f" * 64)
            self.assertRegex(result["storage_receipt_sha256"], r"^[0-9a-f]{64}$")
            assert fake_s3.uploaded is not None
            _, bucket, key, extra = fake_s3.uploaded
            self.assertEqual(bucket, "evidence")
            self.assertRegex(key, r"^reports/[0-9a-f]{64}\.json$")
            self.assertEqual(extra["ContentType"], "application/json")
            self.assertEqual(extra["ServerSideEncryption"], "AES256")
            self.assertEqual(fake_s3.uploaded_body["source_s3"]["key"], "incoming/demo.mp4")
            self.assertEqual(
                fake_s3.uploaded_body["storage_receipt_sha256"],
                result["storage_receipt_sha256"],
            )


if __name__ == "__main__":
    unittest.main()
