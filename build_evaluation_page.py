"""Render a judge-facing, progressive-disclosure evaluation explorer."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from evidence_locker import seal_report


def escape(value):
    return html.escape(str(value), quote=True)


def render(report: dict) -> str:
    body = dict(report)
    receipt = body.pop("receipt_sha256")
    if seal_report(body) != receipt:
        raise ValueError("evaluation receipt mismatch")
    stats = report["real_pairs"]
    if stats["total"] != len(report["real_results"]):
        raise ValueError("evaluation denominator mismatch")
    cases = []
    # Show misses first, retaining every real sample in the page and JSON.
    for row in sorted(report["real_results"], key=lambda r: (r["outcome"] != "FN", r["id"])):
        outcome = row["outcome"]
        name = row["sequence"].replace("-", " ")
        cards = row["evidence_cards"]
        labels = {"TP": "Detected", "FN": "Missed", "FP": "Nuisance trigger", "TN": "Quiet", "ambiguous": "Unscored"}
        cases.append(f'''<details class="case" data-outcome="{escape(outcome)}">
<summary><span class="status {escape(outcome)}">{labels[outcome]}</span>
<span>{escape(name)} <small>frames {escape(row['frames'][0])} → {escape(row['frames'][1])}</small></span>
<span class="fraction">{row['mask_xor_fraction']:.2%} foreground change</span></summary>
<div class="case-body"><p>Human annotation: before (left), after (right). Orange boxes show the detector's regions projected onto the annotation. These diagrams contain no original camera pixels.</p>
<img loading="lazy" src="{escape(row['annotation_preview'])}" width="640" alt="DAVIS foreground annotation pair for {escape(name)}">
<dl><dt>Reference</dt><dd>Foreground occupancy changed by {row['mask_xor_fraction']:.2%} of image area.</dd>
<dt>Detector</dt><dd>{len(cards)} card(s). {escape(row['review_plan']['reason'])}</dd>
<dt>Next action</dt><dd><code>{escape(row['review_plan']['action'])}</code></dd></dl>
<details><summary>Inspect exact evidence</summary><pre>{escape(json.dumps(cards, indent=2))}</pre></details>
</div></details>''')
    controls = []
    descriptions = {
        "exact_repeat": ("Exact repeat", "The same real frame twice."),
        "sensor_noise": ("Small sensor-like noise", "Seeded ±2 pixel intensity perturbation; constructed control."),
        "brightness_shift": ("Lighting change", "+40 intensity with clipping; geometry unchanged. Constructed control."),
    }
    for key, (name, description) in descriptions.items():
        values = report["controls_by_kind"][key]
        controls.append(f'<article class="control"><h3>{name}</h3><p>{description}</p>'
                        f'<strong>{values["FP"]} / {values["total"]}</strong><p>nuisance triggers under the foreground proxy</p></article>')
    return '''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Evidence Locker · Real-video evaluation</title>
<style>
:root{color-scheme:dark;--bg:#08121d;--panel:#101f30;--ink:#edf5fd;--muted:#acc0d3;--mint:#84ebc2;--line:#314459;--orange:#ffb37d}
*{box-sizing:border-box}body{margin:0;font:16px/1.65 system-ui,sans-serif;background:var(--bg);color:var(--ink)}
main{max-width:1120px;margin:auto;padding:32px 24px 72px}a{color:var(--mint)}nav{display:flex;gap:24px;flex-wrap:wrap;margin-bottom:52px}
.eyebrow{color:var(--mint);text-transform:uppercase;letter-spacing:.13em;font-size:.75rem;font-weight:700}
h1{font-size:clamp(2.2rem,5vw,4.5rem);line-height:1.08;letter-spacing:-.04em;max-width:900px;margin:16px 0 24px}
h2{font-size:1.7rem;line-height:1.25;margin:44px 0 14px}p{max-width:850px}.lede{font-size:1.16rem;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:28px 0}.metric,.control{border:1px solid var(--line);background:var(--panel);border-radius:14px;padding:24px}.metric strong,.control strong{font-size:2.6rem;line-height:1.2;display:block}.metric p,.control p{color:var(--muted);margin:10px 0 0}.warn{border-left:3px solid var(--orange);padding:16px 22px;background:#211e20}.warn strong{color:var(--orange)}
details{border:1px solid var(--line);border-radius:10px;margin:10px 0;background:var(--panel)}summary{padding:16px;cursor:pointer}summary:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid var(--mint);outline-offset:4px}.case>summary{display:flex;align-items:center;gap:16px}.case[open]>summary{border-bottom:1px solid var(--line)}small{color:var(--muted);display:block}.fraction{margin-left:auto;color:var(--muted);font-size:.88rem}.status{border:1px solid currentColor;border-radius:6px;padding:3px 9px;font-size:.8rem;color:var(--mint)}.FN,.FP{color:var(--orange)}
.case-body,.method{padding:8px 22px 22px}.case-body img{display:block;width:100%;max-width:640px;height:auto;margin:20px auto;border:1px solid var(--line);border-radius:8px}.case-body p{color:var(--muted);font-size:.9rem}dt{font-weight:700}dd{margin:2px 0 16px;color:var(--muted)}code,pre{font: .85rem/1.5 ui-monospace,monospace;overflow-wrap:anywhere}pre{white-space:pre-wrap;padding:16px;max-height:300px;overflow:auto}select{font:inherit;background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:9px;margin-left:12px}.tools{display:flex;flex-wrap:wrap;align-items:center;gap:12px}.tools p{margin-left:auto;color:var(--muted)}footer{border-top:1px solid var(--line);margin-top:40px;padding-top:20px;font-size:.85rem;color:var(--muted)}.receipt{overflow-wrap:anywhere}.case[hidden]{display:none}
@media(max-width:650px){main{padding:22px 16px 48px}nav{margin-bottom:32px}.grid{grid-template-columns:1fr}.metric{padding:20px}.case>summary{flex-wrap:wrap;gap:10px}.fraction{margin-left:0;width:100%}.tools p{margin-left:0}select{max-width:100%;margin-left:0;display:block}.case-body{padding:8px 14px 18px}}
</style><main><nav><a href="../index.html">← Evidence Locker demo</a><a href="results.json">Download all results</a><a href="https://github.com/tzh476/opencv-evidence-locker/tree/main/evaluation">Protocol &amp; reproduction</a></nav>
<header><p class="eyebrow">Frozen detector · independent annotations · visible failures</p>
<h1>What does the detector catch?<br>What does it miss?</h1>
<p class="lede">A small held-out probe of real video: 12 DAVIS sequences, 36 frame pairs, and a detector frozen before the first prediction. Reference labels come from human-drawn foreground masks.</p></header>
''' + f'''<section class="grid" aria-label="Real-video results">
<article class="metric"><strong>{stats['TP']} / {stats['TP'] + stats['FN']}</strong><p>positive foreground changes detected</p></article>
<article class="metric"><strong>{stats['FN']} missed</strong><p>inspect every miss below</p></article>
<article class="metric"><strong>{stats['TN'] + stats['FP']} negatives</strong><p>real-video false-positive rate cannot be estimated from this sample</p></article></section>
<p class="warn"><strong>Detection recall: {stats['recall']:.1%} on this proxy.</strong> This is not overall accuracy, semantic incident detection, or an official DAVIS score. All 36 selected pairs happen to be positive. Constructed controls have their own denominator below.</p>
<h2>Inspect all 36 real probes</h2><p>Misses appear first. Expand a case to inspect the independent annotation and exact detector evidence.</p>
<div class="tools"><label for="filter">Show <select id="filter"><option value="all">All real probes</option><option value="FN">Missed changes</option><option value="TP">Detected changes</option></select></label><p id="count" role="status">36 cases</p></div>
<section aria-label="Real frame-pair cases">{''.join(cases)}</section>
<h2>How nuisance changes behave</h2><p>36 constructed controls based on real frames. Foreground geometry stays fixed. Lighting changes are still pixel changes, so a trigger is a nuisance under this proxy, not a broken pixel-difference calculation.</p>
<section class="grid">{''.join(controls)}</section>
<p class="warn"><strong>Operational limit:</strong> changing illumination can trigger review even when foreground geometry has not moved. Small foreground movement can also be missed. Use these cards for assisted review; do not treat a quiet result as proof that nothing happened.</p>
<h2>How to interpret the evidence</h2>
<details><summary>Sampling, labels, and leakage controls</summary><div class="method"><p>First 12 alphabetically sorted names from DAVIS 2017 validation; fixed frame pairs (0,5), (10,15), (20,25). No selection by score. Human foreground occupancy XOR ≥0.5% is positive; ≤0.1% is negative; the middle interval is unscored. There were {stats['ambiguous']} ambiguous pairs.</p><p>Detector commit <code>{escape(report['frozen_detector_commit'])}</code>; event threshold 0.02, reset threshold 0.01. Pair probes reset hysteresis each time. Sequence-macro recall is {report['macro_sequence_recall']:.1%} across {report['macro_recall_sequence_count']} sequences; pairs within a sequence are correlated. This public validation subset was unused in this project's prior tuning but is not a private test set. No thresholds were adjusted after seeing results.</p></div></details>
<details><summary>Reproduce and verify the receipt</summary><div class="method"><pre>python fetch_evaluation_data.py --output-dir /tmp/davis-probes
python evaluate_heldout.py --data-dir /tmp/davis-probes --output-dir /tmp/heldout-results
python build_evaluation_page.py --results /tmp/heldout-results/results.json</pre><p>Source files are checksum-verified. All per-pair predictions, source hashes, dependency versions, and the protocol hash are in <a href="results.json">results.json</a>. The receipt hashes canonical JSON excluding its own receipt_sha256 field.</p><p class="receipt">Receipt: <code>{escape(receipt)}</code></p></div></details>
<details><summary>What this evaluation does not establish</summary><div class="method"><p>No object identity, intent, incident classification, production accuracy, localization IoU, real-world review-time savings, or AWS latency is measured here. The annotations define a different target from global pixel intensity. Camera and background motion can disagree with that target. Future tuning on these examples requires a new holdout.</p></div></details>
<footer><p>Annotation diagrams adapted from DAVIS 2017, by Jordi Pont-Tuset, Federico Perazzi, Sergi Caelles, Pablo Arbeláez, Alexander Sorkine-Hornung and Luc Van Gool. <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Changes: binary foreground union, colorization, side-by-side layout, detector-box overlay and resizing. Original camera frames are not redistributed.</p><p><a href="https://davischallenge.org/davis2017/code.html">Official dataset</a> · <a href="https://davischallenge.org/challenge2017/rulesdates.html">Annotation license</a> · Perazzi et al., CVPR 2016; Pont-Tuset et al., arXiv:1704.00675, 2017. No endorsement implied.</p></footer></main>
<script>const filter=document.querySelector('#filter');filter.addEventListener('change',()=>{{let count=0;for(const row of document.querySelectorAll('.case')){{row.hidden=filter.value!=='all'&&row.dataset.outcome!==filter.value;if(!row.hidden)count++;}}document.querySelector('#count').textContent=count+' cases';}});</script></html>'''


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("docs/evaluation/results.json"))
    args = parser.parse_args()
    page = render(json.loads(args.results.read_text()))
    args.results.with_name("index.html").write_text(page)
