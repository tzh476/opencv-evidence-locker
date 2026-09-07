# Devpost submission copy

This file is the durable source for the public Devpost fields. It prevents form
state from becoming the only copy of the submission text.

## About the project

### Inspiration

Visual change detection is easy to demo and hard to trust. In inspection,
incident review, and media triage, an agent should not be allowed to turn a
plausible summary into evidence. We built Evidence Locker around the opposite
idea: OpenCV extracts the facts first, seals them, and strictly bounds what the
agent may do next.

### What it does

Evidence Locker converts a short video into deterministic evidence cards. Each
card records the changed frame and timestamp, sorted bounding regions, a
normalized change score, and SHA-256 hashes of the exact before and after frame
data. A bounded policy then chooses one of four actions:

1. complete when no material change was extracted;
2. rerun localization when a frame-level event has no reviewable region;
3. seal localized evidence for an explanation; or
4. request human approval for a material transition.

The review page shows the selected action, its reason, the evidence cards,
hash-addressed overlays, and the canonical report receipt. The explanation layer
rejects unknown frame citations and any recommendation that differs from the
policy-selected action.

### How we built it

OpenCV 5.0.0 is used across the core path, not as a wrapper around a chatbot. It
decodes video, reads timing metadata, converts adjacent frames to grayscale,
downsamples with `INTER_AREA`, computes `absdiff`, thresholds full-resolution
deltas, closes masks morphologically, extracts contours and bounding boxes, and
renders separate review overlays without modifying the source frames.

Hysteresis prevents continuous motion from creating an event on every frame. An
adaptive region-area floor suppresses tiny contour noise. Frame shape, dtype,
and bytes are included in the hashes, evidence regions are sorted for stable
serialization, and the complete report receives its own SHA-256 receipt.

The repository also includes a Lambda adapter and bounded AWS SAM template. The
template defines private encrypted input and report buckets, an arm64 OpenCV 5
container Lambda, a single `incoming/*.mp4` event boundary, optional reserved
concurrency of one or two, short retention, and least-privilege bucket policies.
On September 4 we deployed it in `us-east-2` for one bounded smoke run. A private
S3 upload triggered Lambda, OpenCV 5.0.0 produced one evidence card and encrypted
JSON report, and the analysis completed in 3004 ms (3791 ms billed, 160 MB peak
memory). We verified both SHA-256 receipts and structured CloudWatch logs, then
deleted the stack, buckets, ECR repository, function, logs, and role. No public
write endpoint or persistent AWS resource remains.

### Agent workflow and human control

The workflow is perception -> decision -> bounded action -> human review.
OpenCV evidence changes the downstream tool decision. A full-frame transition
routes to human approval, a localized transition may be sealed for summary, and
missing localization fails closed into a rerun. The agent cannot expand its own
action set or cite a frame that OpenCV did not extract.

### Evaluation

A clean OpenCV 5 environment passes all 38 tests. The seeded four-scenario suite
covers no change, localized change, full-frame change, and low-amplitude noise:
2 true positives, 2 true negatives, 0 false positives, 0 false negatives, and
4/4 correct downstream actions. This is an engineering smoke test, not a claim
of production accuracy.

We also ran three public `opencv_extra/5.x` videos with different sizes and
metadata. All completed without upload or crash. Repeating the 15-frame sample
produced identical evidence and the same report receipt. A first run on the Big
Buck Bunny sample exposed an event flood of 56 cards across 125 frames;
hysteresis and regression tests reduced it to one card while preserving re-arm
after a quiet frame.

On September 7 we added a frozen held-out foreground-change evaluation: 36 frame
pairs from 12 DAVIS 2017 validation sequences, selected before predictions, with
reference labels derived from human foreground masks. The unchanged detector
found 34 positive pairs and missed two (94.4% recall). All 36 references were
positive, so real-video false-positive rate remains unknown. Separate constructed
controls produced no triggers for exact repeats or ±2 noise (12 each), but all
12 brightness-shift controls triggered. Every result, failure, annotation diagram,
source hash and the frozen protocol is inspectable at the live evaluation page:
https://tzh476.github.io/opencv-evidence-locker/evaluation/ . This is a small
foreground-change proxy, not semantic incident accuracy or an official DAVIS score.

### Challenges and limitations

The hardest failure was distinguishing a meaningful transition from continuous
motion without hiding later events. A second challenge was keeping the
explanation useful while preventing it from inventing visual facts. The current
detector is deliberately narrow: it does not identify objects, people, intent,
or safety-critical anomalies. Camera motion and illumination can trigger events,
and subtle changes can be missed. Production use needs a right-cleared held-out
dataset, calibrated thresholds, and measured precision/recall tradeoffs.

### What's next

The next milestone is natural negative-video evaluation and cold-start
measurement. The first live Lambda cold initialization reached the initialization
timeout before AWS retried and completed the event, so reducing image/init cost is
more valuable than keeping an idle demo stack online. We will preserve the same
evidence-first, human-controlled policy boundary.

## Built with

`OpenCV`, `AWS`, `Amazon`, `Python`, `NumPy`, `Docker`, `Lambda`, `HTML`

## Try it out

https://tzh476.github.io/opencv-evidence-locker/

https://github.com/tzh476/opencv-evidence-locker

The live page is a deterministic, read-only judge endpoint. Its canonical
machine-readable evidence is available at:
https://tzh476.github.io/opencv-evidence-locker/evidence.json

## Demo video

Public or unlisted judging URL:
https://youtu.be/K-sKVB3lXqg

Source-asset mirror:
https://github.com/tzh476/opencv-evidence-locker/releases/download/demo-v1/opencv-evidence-locker.mp4
