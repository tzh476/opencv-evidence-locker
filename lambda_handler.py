"""AWS Lambda adapter for S3-triggered OpenCV evidence reports."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import unquote_plus

from evidence_locker import analyze_video, seal_report


def _source_from_event(event: dict[str, Any]) -> tuple[str, str, str]:
    records = event.get("Records")
    if not isinstance(records, list) or len(records) != 1:
        raise ValueError("exactly one S3 record is required")
    try:
        s3 = records[0]["s3"]
        bucket = s3["bucket"]["name"]
        key = unquote_plus(s3["object"]["key"])
        etag = str(s3["object"].get("eTag", ""))
    except (KeyError, TypeError) as exc:
        raise ValueError("invalid S3 event structure") from exc
    if not isinstance(bucket, str) or not bucket:
        raise ValueError("source bucket is required")
    if not isinstance(key, str) or not key:
        raise ValueError("source key is required")
    return bucket, key, etag


def _output_key(bucket: str, key: str, etag: str) -> str:
    identity = json.dumps([bucket, key, etag], separators=(",", ":")).encode()
    return f"reports/{hashlib.sha256(identity).hexdigest()}.json"


def handler(
    event: dict[str, Any],
    context: Any,
    *,
    s3_client: Any | None = None,
) -> dict[str, object]:
    del context
    output_bucket = os.environ.get("EVIDENCE_OUTPUT_BUCKET")
    if not output_bucket:
        raise RuntimeError("EVIDENCE_OUTPUT_BUCKET is required")
    source_bucket, source_key, source_etag = _source_from_event(event)
    if source_bucket == output_bucket and source_key.startswith("reports/"):
        raise ValueError("refusing to process generated report objects")

    if s3_client is None:
        import boto3

        s3_client = boto3.client("s3")

    job_id = hashlib.sha256(f"{source_bucket}\0{source_key}\0{source_etag}".encode()).hexdigest()
    input_path = Path("/tmp") / f"{job_id}.video"
    report_path = Path("/tmp") / f"{job_id}.json"
    output_key = _output_key(source_bucket, source_key, source_etag)

    s3_client.download_file(source_bucket, source_key, str(input_path))
    report = analyze_video(input_path)
    source_report_receipt = report["receipt_sha256"]
    report["source_s3"] = {
        "bucket": source_bucket,
        "key": source_key,
        "etag": source_etag,
    }
    report["storage_receipt_sha256"] = seal_report(report)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    s3_client.upload_file(
        str(report_path),
        output_bucket,
        output_key,
        ExtraArgs={"ContentType": "application/json", "ServerSideEncryption": "AES256"},
    )
    return {
        "status": "report_written",
        "output_bucket": output_bucket,
        "output_key": output_key,
        "report_receipt_sha256": source_report_receipt,
        "storage_receipt_sha256": report["storage_receipt_sha256"],
    }
