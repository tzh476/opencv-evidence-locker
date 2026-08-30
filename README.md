# Agentic Vision Evidence Locker — bounded spike

This local prototype tests one narrow OpenCV 5 premise for the OpenCV AI
Competition 2026. It turns a video into deterministic evidence cards containing
the changed frame, timestamp, changed bounding boxes, and hashes of the exact
before/after frames. A bounded review planner then changes its next action based
on those cards: complete, rerun extraction, seal localized evidence, or request
human approval. The canonical report is sealed with a separate SHA-256 receipt.

It is not a contest entry, AWS deployment, agent implementation, registration,
award, or income. The future agent layer would interpret evidence cards and ask
for human review; it must not invent visual facts that OpenCV did not extract.

## Verify

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest -v
```

Analyze a local video without uploading it:

```bash
.venv/bin/python evidence_locker.py input.mp4 --output evidence.json
```

Run the deterministic four-scenario evaluation:

```bash
.venv/bin/python evaluate_synthetic.py
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
- Performs no network, cloud, account, billing, or external write.

## Next technical boundary

If the spike passes, the smallest credible competition project needs a fresh
human-review UI, an agent that explains only extracted evidence, an evaluation
set with false-positive/false-negative measurements, and a meaningful bounded
AWS component. Those pieces are not implemented or claimed here.

`lambda_handler.py` now provides a locally tested boundary for the proposed AWS
path: one S3 object event downloads a video, runs the same OpenCV evidence
pipeline, and writes an AES-256 server-side-encrypted JSON report to a separate
S3 prefix. It rejects batches and output-recursion events. The adapter has not
been deployed, connected to API Gateway, or exercised against a real AWS account.

## Verified result — 2026-08-31

The isolated spike environment reported OpenCV `5.0.0`; all sixteen unit tests
passed. A 20-frame, 10 FPS synthetic black-to-white video produced exactly one
evidence card at frame 10 / 1,000 ms, with a `0.992157` normalized change score,
one `(0, 0, 160, 100)` region, and distinct SHA-256 hashes for the previous and
current frames. The planner selected `request_human_approval`, and the canonical
report receipt was `7fa0a95b5df55085182e0663c5968a38e8b1d647fef5e031308d278e82976d9c`.
The generated video and JSON remained under `/tmp` and are not contest assets or
external evidence.

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
