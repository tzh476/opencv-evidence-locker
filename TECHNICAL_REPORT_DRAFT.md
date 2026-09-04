# Agentic Vision Evidence Locker — technical report

> Local and container verification plus one bounded live AWS smoke run are
> documented below. This report does not claim a persistent production service,
> contest award, prize eligibility decision, or payment.

## 1. Project summary

Agentic Vision Evidence Locker turns a short video into reviewable, reproducible
visual-change evidence. OpenCV 5 detects changed frame transitions and bounding
regions. A bounded agent policy may only choose an action justified by those
evidence cards: finish when no material change exists, rerun region extraction
when an event is not reviewable, seal localized evidence for a summary, or ask a
human to approve a material transition. The project never treats a language-model
summary as visual evidence.

The design targets inspection, incident review, and media-triage workflows where
an operator needs to see *what changed*, the exact source-frame hashes, and why
the next action was selected.

## 2. OpenCV 5 contribution

The local pipeline pins `opencv-python==5.0.0.93` and uses OpenCV substantively:

1. OpenCV decodes the input video and obtains its frame rate.
2. Each adjacent BGR frame pair is converted to grayscale, downsampled with
   `INTER_AREA`, and compared with `absdiff` for a normalized change score.
3. Full-resolution `absdiff`, thresholding, morphology-close, contour extraction,
   and bounding rectangles create changed-region evidence.
4. An adaptive minimum-region area suppresses tiny contour specks without hiding
   the main changed region.
5. Hysteresis prevents continuous motion from producing a card for every frame.
6. OpenCV renders separate review overlays; source frames are not modified.

This is not a generic chatbot around a fixed image result: OpenCV output controls
whether the system completes, reruns, seals evidence, or requires human review.

## 3. Agentic decision boundary

The policy is deterministic and fail-closed in the current local build:

| OpenCV evidence | Permitted plan | Why |
| --- | --- | --- |
| No card over threshold | `complete_no_material_change` | No visual transition was extracted. |
| Card has no reviewable region | `rerun_region_extraction_then_review` | Do not summarize an unlocalized event. |
| Any card has score at least 0.25 | `request_human_approval` | A material transition requires a person. |
| Other localized cards | `seal_evidence_for_agent_summary` | A later summary may cite only the extracted card frames. |

The explanation module rejects unknown frame citations and recommendations that
do not equal the bounded plan. This preserves human control and makes it possible
to audit the agent output against the vision evidence.

## 4. Reproducibility and evidence receipt

Every evidence card includes a frame index, timestamp, score, sorted regions,
and SHA-256 hashes of the exact before/after frame shape, dtype, and bytes. The
complete report is canonical JSON sealed with its own SHA-256 receipt. Overlays
use hash-addressed filenames and carry their own SHA-256 values. Re-running an
identical input is expected to generate an identical canonical receipt.

Local commands:

```bash
cd artifacts/prototypes/agentic-vision-evidence-locker
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest -v
.venv/bin/python evaluate_synthetic.py
.venv/bin/python evidence_locker.py input.mp4 --output evidence.json --overlay-dir overlays
.venv/bin/python report_ui.py evidence.json --output overlays/review.html
```

## 5. Evaluation performed locally

The deterministic synthetic suite contains four scenarios: no change, localized
change, full-frame change, and low-amplitude noise. On the seeded local suite it
produced 2 true positives, 2 true negatives, 0 false positives, 0 false
negatives, and 100% agreement between expected and selected policy action. This
is a small engineering smoke test, **not** a claim of production accuracy or
real-world benchmark performance.

The unit suite covers deterministic evidence ordering, frame validation,
hysteresis/re-arming, missing-region failure handling, overlay immutability,
receipt stability, explanation constraints, Lambda event safeguards, and
HTML escaping in the review UI.

## 6. Failure modes and limitations

- Change detection is not object recognition, identity verification, intent
  inference, or anomaly detection in a safety-critical sense.
- Thresholds and minimum region area are content-dependent; subtle visual
  changes can be missed and illumination/camera movement can trigger events.
- The synthetic four-case suite is deliberately small. A final entry needs a
  right-cleared, held-out evaluation set and reported precision/recall tradeoffs.
- The system stores frame hashes and overlays for review; an approved deployment
  must define retention, sample licensing, and access controls before accepting
  user-provided media.
- The agent cannot make an irreversible or factual claim beyond the OpenCV
  evidence. Material changes route to human approval.

## 7. Verified bounded AWS smoke run

On September 4, 2026, the SAM stack was deployed in `us-east-2` and exercised
with one locally generated synthetic MP4. The private input bucket triggered the
arm64 Lambda container. OpenCV `5.0.0` produced one evidence card and wrote a
1,681-byte AES-256-encrypted JSON report to the separate private evidence bucket.
The structured completion log measured `3004.288 ms` for analysis; the successful
invocation was billed for `3791 ms` and used `160 MB` peak memory out of `2048 MB`.

The canonical report receipt was
`5c189c2ab35a37032e798cee3098ce0f315f37730c55997761de6ec2161b4d90` and
the storage receipt was
`116b0b09bab3f1aa9195d90ad2d6b1809b9ecb27c7bc6e56b6729a282db230ed`.
The first cold initialization attempt reached Lambda's initialization timeout;
AWS retried and the event completed successfully. This is a concrete optimization
target before any production claim.

After verification, all test objects and AWS resources created for the run were
deleted. Final queries returned zero remaining buckets, Lambda functions, ECR
repositories, active CloudFormation stacks, matching log groups, and matching
IAM roles. The project intentionally leaves no persistent write endpoint.

## 8. Submission-material checklist

- [x] Local code, pinned runtime dependency, tests, synthetic evaluation, and
  architecture diagram.
- [x] Technical report, video, and applicant-reviewed project description.
- [x] One bounded AWS deployment with right-cleared synthetic media, logs,
  latency, memory, and receipt evidence; resources removed afterward.
- [x] Judge-accessible read-only endpoint and public source package.
- [x] Applicant-reviewed video, project-page declarations, terms, and final
  submission.
- [ ] Larger right-cleared held-out evaluation and cold-start optimization.
