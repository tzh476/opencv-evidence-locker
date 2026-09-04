# Agentic Vision Evidence Locker — five-minute demo script draft

> Local draft only. Replace bracketed items with applicant-reviewed facts and
> only show media that the applicant is entitled to publish.

## 0:00–0:30 — problem and promise

"A vision system often tells an operator that something changed, but not exactly
which frames justify that conclusion or what the agent is allowed to do next.
Agentic Vision Evidence Locker uses OpenCV 5 to turn a short video into
hash-addressed evidence cards, then constrains the agent to a human-reviewable
next action."

Show: project title and the architecture diagram.

## 0:30–1:30 — OpenCV pipeline

"The pipeline decodes a video, compares adjacent frames, extracts contour-based
changed regions, and produces an overlay. Each card includes a timestamp, score,
regions, and hashes for the exact before and after frames. Hysteresis prevents
continuous motion from flooding the operator with duplicate cards."

Show: a right-cleared sample clip, generated overlay, then its JSON evidence
card. Do not call a box an identified object unless the submitted model actually
supports that claim.

## 1:30–2:30 — bounded agent loop and human control

"The agent does not invent visual findings. No card means complete. A card with
no reviewable region triggers a rerun. A localized card is sealed for a summary.
A material transition requests human approval. The explanation is rejected if it
cites a frame absent from the OpenCV receipt or proposes a different action."

Show: the standalone review page and the selected decision reason. Optionally
show the negative test that rejects an unknown-frame explanation.

## 2:30–3:30 — evaluation and limitations

"The local engineering evaluation contains no change, localized change,
full-frame change, and low-amplitude noise. It reports its confusion counts and
policy-action agreement. This is a smoke suite, not a production accuracy claim.
Illumination changes, camera movement, threshold selection, and domain shift
remain known limitations, so material changes stay under human approval."

Show: output of `evaluate_synthetic.py` and the limitations section of the
technical report.

## 3:30–4:30 — AWS component (record only after approval and deployment)

"[Only after actual deployment:] The same OpenCV 5 pipeline runs in an arm64 AWS
Lambda container. A bounded demo request produces an encrypted S3 receipt and
logs the correlation ID, OpenCV version, input hash, latency, and safeguard
events. This is the vision computation that drives the later agent action, not
static hosting."

Show only actual, redacted deployment evidence: architecture, a completed demo
request, CloudWatch log fields, and the resulting receipt. If no deployment has
occurred, replace this section with: "The AWS adapter is prepared locally; cloud
deployment has not been performed and is not represented in this demo."

## 4:30–5:00 — close

"The project keeps the visual decision trace inspectable: OpenCV extraction,
receipt, constrained plan, and human decision. The same input can be rerun
locally to reproduce the evidence."

Show: final receipt hash and the reproducibility commands.
