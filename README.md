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

## Spike acceptance criteria

- Runs against `opencv-python==5.0.0.93`.
- Emits no event for identical frames and completes without escalation.
- Detects and deterministically orders multiple changed regions.
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

## Verified result — 2026-08-31

The isolated spike environment reported OpenCV `5.0.0`; all nine unit tests
passed. A 20-frame, 10 FPS synthetic black-to-white video produced exactly one
evidence card at frame 10 / 1,000 ms, with a `0.992157` normalized change score,
one `(0, 0, 160, 100)` region, and distinct SHA-256 hashes for the previous and
current frames. The planner selected `request_human_approval`, and the canonical
report receipt was `7fa0a95b5df55085182e0663c5968a38e8b1d647fef5e031308d278e82976d9c`.
The generated video and JSON remained under `/tmp` and are not contest assets or
external evidence.
