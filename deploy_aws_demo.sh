#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--confirm-create-resources" ]]; then
  echo "Refusing to create AWS resources without --confirm-create-resources" >&2
  exit 2
fi

AWS_REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="${AWS_STACK_NAME:-opencv-evidence-locker-demo}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export AWS_REGION
export SAM_CLI_TELEMETRY=0
cd "$SCRIPT_DIR"

aws sts get-caller-identity >/dev/null
docker info >/dev/null
"$PYTHON_BIN" -c 'import cv2' >/dev/null
sam validate --lint --template-file template.yaml
sam build --template-file template.yaml
sam deploy \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION" \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --resolve-image-repos \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  --parameter-overrides ArtifactRetentionDays=1

stack_output() {
  aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue | [0]" \
    --output text
}

input_bucket="$(stack_output InputBucketName)"
evidence_bucket="$(stack_output EvidenceBucketName)"
function_name="$(stack_output EvidenceFunctionName)"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/opencv-evidence-locker-aws.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT
demo_video="$work_dir/demo.mp4"
demo_report="$work_dir/evidence.json"
demo_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
source_key="incoming/demo-$demo_id.mp4"

"$PYTHON_BIN" generate_demo_video.py "$demo_video" >/dev/null
aws s3 cp "$demo_video" "s3://$input_bucket/$source_key" \
  --sse AES256 \
  --only-show-errors

source_etag="$(aws s3api head-object \
  --bucket "$input_bucket" \
  --key "$source_key" \
  --query ETag \
  --output text | tr -d '"')"
report_key="$("$PYTHON_BIN" - "$input_bucket" "$source_key" "$source_etag" <<'PY'
import hashlib
import json
import sys

identity = json.dumps(sys.argv[1:4], separators=(",", ":")).encode()
print(f"reports/{hashlib.sha256(identity).hexdigest()}.json")
PY
)"
job_id="$("$PYTHON_BIN" - "$input_bucket" "$source_key" "$source_etag" <<'PY'
import hashlib
import sys

print(hashlib.sha256("\0".join(sys.argv[1:4]).encode()).hexdigest())
PY
)"
for _ in {1..24}; do
  if aws s3api head-object \
    --bucket "$evidence_bucket" \
    --key "$report_key" >/dev/null 2>&1; then
    break
  fi
  sleep 5
done
if ! aws s3api head-object \
  --bucket "$evidence_bucket" \
  --key "$report_key" >/dev/null 2>&1; then
  echo "No evidence report appeared within 120 seconds" >&2
  exit 1
fi

aws s3 cp "s3://$evidence_bucket/$report_key" "$demo_report" --only-show-errors
"$PYTHON_BIN" - "$demo_report" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text())
if report.get("opencv_version") != "5.0.0":
    raise SystemExit("AWS report did not use OpenCV 5.0.0")
if not report.get("evidence_cards"):
    raise SystemExit("AWS report contains no evidence cards")
print(json.dumps({
    "evidence_card_count": len(report["evidence_cards"]),
    "opencv_version": report["opencv_version"],
    "receipt_sha256": report["receipt_sha256"],
    "storage_receipt_sha256": report["storage_receipt_sha256"],
}, indent=2, sort_keys=True))
PY

log_lines=""
for _ in {1..12}; do
  log_lines="$(aws logs tail "/aws/lambda/$function_name" \
    --since 10m \
    --format short 2>/dev/null || true)"
  if grep -F "$job_id" <<<"$log_lines" | grep -q 'analysis_completed'; then
    break
  fi
  sleep 5
done
matching_logs="$(grep -F "$job_id" <<<"$log_lines" || true)"
if ! grep -q 'analysis_completed' <<<"$matching_logs"; then
  echo "No structured completion log appeared within 60 seconds" >&2
  exit 1
fi
grep -E 'analysis_(started|completed|failed)' <<<"$matching_logs" | tail -10

echo "AWS smoke run completed. Stack: $STACK_NAME. Region: $AWS_REGION."
