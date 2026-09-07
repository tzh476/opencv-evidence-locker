# Evidence Locker — Agentic Vision with OpenCV 5

[![Verify Evidence Locker](https://github.com/tzh476/opencv-evidence-locker/actions/workflows/verify.yml/badge.svg)](https://github.com/tzh476/opencv-evidence-locker/actions/workflows/verify.yml)

This repository is the reproducible source package for the **Evidence Locker**
OpenCV AI Competition 2026 project. It turns a video into deterministic evidence
cards containing the changed frame, timestamp, changed bounding boxes, and
hashes of the exact before/after frames. A bounded review planner then changes
its next action based on those cards: complete, rerun extraction, seal localized
evidence, or request human approval. The canonical report is sealed with a
separate SHA-256 receipt.

The implemented explanation layer may cite only extracted frame evidence and the
policy-selected action; it must not invent visual facts that OpenCV did not
extract. Local, container, and one bounded live AWS smoke run are verified below.
No persistent AWS endpoint, contest award, or payment is claimed.

- [Three-minute competition demo](https://youtu.be/K-sKVB3lXqg)
- [Source-video release asset](https://github.com/tzh476/opencv-evidence-locker/releases/download/demo-v1/opencv-evidence-locker.mp4)
- [Live judge endpoint](https://tzh476.github.io/opencv-evidence-locker/)
- [Real-video evaluation: all 36 probes and failures](https://tzh476.github.io/opencv-evidence-locker/evaluation/)
- [Canonical demo evidence JSON](https://tzh476.github.io/opencv-evidence-locker/evidence.json)
- [Technical report](Evidence-Locker-Technical-Report.pdf)
- [Bounded AWS architecture](architecture.svg)

## Real-video evaluation — 2026-09-07

The detector was frozen at `d09d968` before evaluating 36 previously unused frame
pairs from 12 DAVIS 2017 validation sequences. The selection and reference-label
rules were committed first in [the protocol](evaluation/PROTOCOL.md).
Human-drawn foreground masks provide an independent **foreground-change proxy**.

| Separate cohort | Result | Interpretation |
| --- | --- | --- |
| 36 real frame pairs | 34 detected, 2 missed; recall 94.4% | All 36 references are positive; real false-positive rate is unknown. |
| 12 exact-repeat controls | 0 nuisance triggers | Constructed controls, not real static-video coverage. |
| 12 ±2 intensity-noise controls | 0 nuisance triggers | Bounded perturbations only. |
| 12 +40 brightness controls | 12 nuisance triggers | Illumination is a measured weakness under the foreground proxy. |

Both misses are in `drift-chicane`, frames 0→5 and 20→25. No threshold was tuned
after seeing these results. Pairs from a sequence are correlated, and pair probes
reset hysteresis. These are neither production accuracy nor official DAVIS
segmentation scores. The public explorer includes every outcome, independent
annotation diagrams, exact detector actions, and source hashes; original camera
frames remain local. Annotation reuse and attribution are documented in the
protocol. Future tuning requires a fresh holdout.

```bash
.venv/bin/python fetch_evaluation_data.py --output-dir /tmp/davis-probes
.venv/bin/python evaluate_heldout.py --data-dir /tmp/davis-probes --output-dir /tmp/heldout-results
.venv/bin/python build_evaluation_page.py --results /tmp/heldout-results/results.json
```

The downloader requests only the 144 selected JPEG/mask files from the official
archive, checks its ETag and byte range, and records each file's SHA-256. The
evaluator verifies all files before predicting. Two full local runs produced
identical reports and annotation diagrams. The original synthetic demo receipt
is unchanged. The local suite now passes **38 tests**; the two hosted-artifact
tests are intentionally excluded from the smaller Lambda runtime image.

## Local verification

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest -v
```

Build and test the Lambda-compatible arm64 container locally without pushing it:

```bash
docker build --platform linux/arm64 -t agentic-vision-evidence-locker:spike .
docker run --rm --platform linux/arm64 --entrypoint python agentic-vision-evidence-locker:spike -m unittest -v
```

Validate the bounded AWS SAM template locally (this creates no AWS resources):

```bash
.venv/bin/python -m unittest -v test_infrastructure.py
SAM_CLI_TELEMETRY=0 sam validate --lint --template-file template.yaml
```

`template.yaml` creates two private AES-256-encrypted S3 buckets, an arm64
container Lambda, a single `incoming/*.mp4` event boundary, optional 1-2 reserved
concurrent executions, fourteen-day logs, and configurable 1-30 day object
retention (seven days by default). Reserved concurrency defaults to unset so the
stack also works in new low-quota AWS accounts; set `ReservedConcurrency=1` or
`2` only when the account has sufficient unreserved concurrency. The template
alone is not deployment evidence; the dated smoke evidence below records the
separate live verification.

Analyze a local video without uploading it:

```bash
.venv/bin/python evidence_locker.py input.mp4 --output evidence.json --overlay-dir overlays
```

Run the deterministic four-scenario evaluation:

```bash
.venv/bin/python evaluate_synthetic.py
```

Build the deterministic read-only demo used by the public project endpoint:

```bash
.venv/bin/python build_static_demo.py --output-dir docs
```

After the AWS account owner has signed in and explicitly approved creating the
bounded private resources, run the one-input cloud smoke path:

```bash
AWS_REGION=us-east-1 ./deploy_aws_demo.sh --confirm-create-resources
```

The script validates and builds the SAM application, deploys one private
S3-triggered arm64 Lambda stack with one-day artifact retention, generates a
right-cleared synthetic MP4, uploads it once, verifies the returned OpenCV 5
receipt, and prints only the structured CloudWatch evidence lines. It has no
public write endpoint and refuses to run without the explicit flag. It requires
authenticated AWS CLI credentials, a running Docker daemon, AWS SAM CLI, and a
Python interpreter with OpenCV (override it with `PYTHON_BIN` if needed).

Render a standalone human-review page next to the generated overlays:

```bash
.venv/bin/python report_ui.py evidence.json --output overlays/review.html
```

## Spike acceptance criteria

- Runs against `opencv-python==5.0.0.93`.
- Emits no event for identical frames and completes without escalation.
- Detects and deterministically orders multiple changed regions.
- Uses hysteresis: an event must fall below a reset threshold before another
  evidence card can fire, preventing continuous-motion event floods.
- Hashes the exact frame shape, dtype, and bytes.
- Rejects shape and dtype mismatches instead of silently normalizing evidence.
- Fails closed into a rerun when a frame-level event has no reviewable region.
- Requests human approval for a material transition and seals the report.
- Renders hash-addressed review overlays without modifying source frames.
- Escapes report data and renders a standalone decision-and-evidence review page.
- Constrains the explanation layer to known frame ids and the bounded OpenCV
  review action; unknown claims or unapproved actions fail closed.
- Local verification commands perform no network, cloud, account, billing, or
  external write; only the separately confirmed deployment script does so.

## AWS live smoke — 2026-09-04

The bounded SAM stack was deployed in `us-east-2` and exercised with one locally
generated synthetic MP4. A private S3 upload triggered the arm64 Lambda, which
reported OpenCV `5.0.0`, produced one evidence card and a 1,681-byte encrypted
JSON report, and emitted structured start/completion logs. The analysis step took
`3004.288 ms`; the successful invocation was billed for `3791 ms` and used
`160 MB` peak memory out of the configured `2048 MB`.

The canonical report receipt was
`5c189c2ab35a37032e798cee3098ce0f315f37730c55997761de6ec2161b4d90`;
the storage receipt was
`116b0b09bab3f1aa9195d90ad2d6b1809b9ecb27c7bc6e56b6729a282db230ed`.
The first cold initialization attempt reached Lambda's initialization timeout;
AWS retried and the event completed successfully. This is a measured cold-start
limitation, not a production reliability claim.

After evidence capture, the input/report objects, application stack, companion
ECR stack, SAM bootstrap stack, buckets, image repository, function, log group,
and role were deleted. A final account query returned zero remaining buckets,
functions, ECR repositories, active CloudFormation stacks, matching log groups,
and matching IAM roles. There is intentionally no persistent API Gateway or live
write endpoint; the public judge page remains a deterministic read-only artifact.

![Bounded AWS architecture](architecture.svg)

## Verified result — 2026-08-31

The isolated environment reported OpenCV `5.0.0`; all thirty-two tests passed
from a clean install. A 20-frame, 10 FPS synthetic black-to-white video produced
exactly one evidence card at frame 10 / 1,000 ms, with a `0.992157` normalized change score,
one `(0, 0, 160, 100)` region, and distinct SHA-256 hashes for the previous and
current frames. The planner selected `request_human_approval`, and the canonical
report receipt was `7fa0a95b5df55085182e0663c5968a38e8b1d647fef5e031308d278e82976d9c`.
The generated synthetic video and JSON remained under `/tmp`; the repository
records the deterministic assertions and receipt rather than temporary output.

The seeded four-scenario evaluation covers no change, localized change,
full-frame change, and low-amplitude noise. It currently reports two true
positives, two true negatives, zero false positives, zero false negatives, and
100% action selection accuracy. This is a smoke-sized synthetic evaluation, not
evidence of production accuracy; licensed real-world samples are still needed.

A read-only run against OpenCV's public `opencv_extra` Big Buck Bunny MP4 test
sample exposed event flooding in the first implementation: 56 cards across 125
frames. Hysteresis and two regression tests reduced that to one card without
disabling re-arming after a quiet frame. The corrected report receipt is
`13a3d89482c0ea6f6ccd2082c1268fb46c383c8f1100565e7bddf7ad57c6c61c`.
This single public sample proves the regression fix, not general accuracy.

The first review overlay still contained many tiny contour boxes. An adaptive
minimum area (`max(16px, 0.2% of the frame)`) and a tiny-speck regression test
reduced that sample from dozens of boxes to four reviewable regions while
preserving the main subject. The corrected overlay SHA-256 is
`5acece4631ad46ccf4bca97d125a9ae1c26e6fc1d9577af85e822418c5e75ef9`.

Three public `opencv_extra/5.x` videos with different sizes and metadata were
then processed under OpenCV 5 without crashes or uploads:

| Sample source SHA-256 | Frames | Events | Action |
|---|---:|---:|---|
| `4e28622467284da93f7575189c84f0e762b170bb7cf19667ca52929f93dcc238` | 125 | 1 | seal evidence |
| `c433da3c2354a19324f606300753be7942cf3970e879e081bca749bd9041445c` | 15 | 1 | seal evidence |
| `fbf61d51ea8a2d1218c4fb898c6b31acf661d578040dd964447532b1f66a6c77` | 54 | 2 | seal evidence |

Repeating the 15-frame H.264 sample produced identical evidence cards and the
same report receipt (`39584d0272d96679c591d87f1836fbe44e0635adc6e835b35b030a0686dc5ced`).
The samples remain in `/tmp`; this repository records hashes and bounded results,
not the media.

The cloud deployment gate is: all tests pass; the seeded
positive/negative set has zero FP/FN; repeated input yields the same receipt;
each public sample completes; and event density stays below 10% of frames. These
are engineering gates for the spike, not claims of real-world precision or recall.

The standalone review HTML was rendered in headless Chrome at 1280 x 1200 and
visually checked. It showed the decision reason, four-region overlay, exact frame
hashes, and report receipt without clipping. The screenshot remained in `/tmp`.

The bounded explanation layer was integrated into the sealed report. On the
15-frame H.264 sample it cited only frame 1, summarized three extracted regions
and a `0.174708` maximum change, and preserved the policy-selected
`seal_evidence_for_agent_summary` action. Tests reject unknown frame citations
and any recommendation that differs from the bounded plan.

The Lambda-compatible image was then built locally from
`public.ecr.aws/lambda/python:3.13-arm64`. Inside that image, Python reported
`aarch64`, OpenCV reported `5.0.0`, and all twenty-six runtime tests passed again;
the five SAM-template tests run on the host. The
architecture SVG was rendered to a 1,200 x 620 PNG in headless Chrome and
visually checked. The later dated AWS smoke above supersedes the earlier
local-only boundary while preserving the same container and template tests.
