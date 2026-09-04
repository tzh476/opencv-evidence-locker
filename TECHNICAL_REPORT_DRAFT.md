# Agentic Vision Evidence Locker — technical report draft

> Local preparation only — not a Devpost submission, a representation that AWS
> has been deployed, or a claim of prize eligibility. The applicant must review
> every statement, add deployment evidence after an approved deployment, and
> complete any final project-page declarations personally.

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

## 7. Proposed AWS component — not deployed

The prepared adapter and `template.yaml` define a proposed low-cost, meaningful
AWS path, not an existing service. An encrypted private input bucket accepts
right-cleared `incoming/*.mp4` objects and invokes an arm64 Lambda container
with OpenCV 5. The function analyzes one bounded sample, writes a
server-side-encrypted JSON receipt to a separate private report bucket, and
returns the receipt location in its invocation result. The adapter rejects
multiple records and output-recursion events. The template caps reserved
concurrency at two, expires objects after seven days by default, and retains
CloudWatch logs for fourteen days.

Before claiming this component in any entry, the applicant must personally:

1. approve the account, billing, IAM, storage, and retention choices;
2. deploy and verify the endpoint using a right-cleared sample;
3. capture the actual architecture, logs, receipt, latency, and cost evidence;
4. remove any assertion from this report that the deployed result cannot support.

## 8. Submission-material checklist

- [x] Local code, pinned runtime dependency, tests, synthetic evaluation, and
  architecture diagram.
- [x] Local technical-report and video-script drafts.
- [ ] Applicant-reviewed project description and license decision.
- [ ] Applicant-approved AWS account/billing path and a meaningful deployed
  component.
- [ ] Right-cleared demo media, held-out evaluation, and deployment receipts.
- [ ] Judge-accessible endpoint or applicant-arranged live demonstration.
- [ ] Applicant-reviewed video, project-page declarations, terms, and final
  submission.
