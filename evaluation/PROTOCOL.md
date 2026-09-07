# Frozen real-video change evaluation

Protocol v1 is committed before running detector predictions on these samples.
The detector and its thresholds stay at `d09d968`. This is a held-out sample
relative to this project's development, not a private or official DAVIS test set.

Select the first 12 alphabetically sorted names of the official DAVIS 2017
validation split, with pairs (0, 5), (10, 15), (20, 25) from every sequence.
Do not select sequences or frames by detector score. Missing inputs fail the run;
they must not silently reduce the denominator. There are 36 real frame pairs.

## What the labels mean

The reference is independent human-drawn DAVIS foreground segmentation. Collapse
object IDs into foreground and compute the fraction of pixels where occupancy
changes between the two masks. At least 0.5% is positive; at most 0.1% is negative;
the interval between them is ambiguous and is reported separately. These cutoffs
are fixed before predictions. Object-ID changes do not count as movement.

This is a **foreground-change proxy**, not semantic incident ground truth, object
recognition, segmentation accuracy, or an official DAVIS J&F score. Camera motion,
changing backgrounds, texture, and changing light can disagree with this proxy.
Report every pair and all false positives/negatives; do not relabel disagreements.
Pairs from one sequence are correlated. Report macro sequence metrics as well as
pooled counts and avoid a claim of statistical generalization from 12 sequences.

Evaluate the two frames as an independent probe of the unchanged detector (fresh
hysteresis per pair). Use fps=1 only as a pair-index convention; the five-frame
gap is not a one-second latency measurement. This does not evaluate streaming
hysteresis, exact event timing, human-review effectiveness, or cloud latency.

## Constructed controls — separate denominator

For each sequence's frame 0: exact repeat, bounded seeded +/-2 intensity noise,
and +40 brightness with uint8 clipping. These are constructed real-image controls,
not untouched real videos. Their foreground geometry is unchanged. They expose
nuisance-trigger behavior under the same proxy. Never pool these 36 easy/hard
controls into the 36 real-pair precision/recall numbers.

## Audit and presentation

Record archive identity, individual JPEG/PNG SHA-256 hashes, protocol hash,
detector file hash, OpenCV/NumPy version, per-pair result, and a sealed JSON report.
Repeat the full local run for deterministic evidence. Do not tune on this set;
future tuning makes it development data and needs a fresh holdout.

Official sources: https://davischallenge.org/davis2017/code.html and
https://davischallenge.org/challenge2017/rulesdates.html . Cite Perazzi et al.,
CVPR 2016, and Pont-Tuset et al., arXiv:1704.00675 (2017).
DAVIS annotations are CC BY 4.0. The evaluation-code BSD license is not assumed
to clear every source video's redistribution rights. Download original frames
locally for research; publish measurements and attributed annotation-only
silhouettes, not original video pixels, until per-video rights are verified.
The public UI must label silhouettes as annotation diagrams, not camera footage.
