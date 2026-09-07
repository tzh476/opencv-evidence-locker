"""Evaluate frozen real-frame probes against an independent foreground proxy."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np

from evidence_locker import analyze_frames, plan_review, seal_report
from fetch_evaluation_data import PROTOCOL


def foreground(mask: np.ndarray) -> np.ndarray:
    if mask is None or mask.ndim not in (2, 3):
        raise ValueError("missing or invalid annotation")
    return np.any(mask != 0, axis=2) if mask.ndim == 3 else mask != 0


def reference_label(previous: np.ndarray, current: np.ndarray, protocol: dict):
    before, after = foreground(previous), foreground(current)
    if before.shape != after.shape:
        raise ValueError("annotation shapes differ")
    fraction = float(np.mean(before != after))
    if fraction >= protocol["positive_mask_xor_fraction"]:
        return True, fraction
    if fraction <= protocol["negative_mask_xor_fraction"]:
        return False, fraction
    return None, fraction


def confusion(expected, detected):
    if expected is None:
        return "ambiguous"
    return ("TP" if detected else "FN") if expected else ("FP" if detected else "TN")


def metrics(rows: list[dict]) -> dict:
    counts = Counter(row["outcome"] for row in rows)
    tp, fp, fn, tn = (counts[key] for key in ("TP", "FP", "FN", "TN"))
    return {
        "total": len(rows), "scored": tp + fp + fn + tn,
        **{key: counts[key] for key in ("TP", "TN", "FP", "FN", "ambiguous")},
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "specificity": tn / (tn + fp) if tn + fp else None,
    }


def probe(previous, current, expected, protocol):
    cards = analyze_frames([previous, current], fps=1,
                           event_threshold=protocol["event_threshold"],
                           reset_threshold=protocol["reset_threshold"])
    return {"expected_change": expected, "detected_change": bool(cards),
            "outcome": confusion(expected, bool(cards)),
            "review_plan": asdict(plan_review(cards)),
            "evidence_cards": [asdict(card) for card in cards]}


def annotation_preview(before, after, cards, output: Path):
    """Only publish CC-BY annotation shapes, never original camera pixels."""
    panels = []
    for mask in (before, after):
        fg = foreground(mask)
        panel = np.full((*fg.shape, 3), (28, 22, 15), dtype=np.uint8)
        panel[fg] = (193, 222, 97)
        panels.append(panel)
    for card in cards:
        for x, y, w, h in card["changed_regions"]:
            cv2.rectangle(panels[1], (x, y), (x + w - 1, y + h - 1), (97, 151, 255), 2)
    preview = np.concatenate(panels, axis=1)
    preview = cv2.resize(preview, (640, round(640 * preview.shape[0] / preview.shape[1])),
                         interpolation=cv2.INTER_NEAREST)
    if not cv2.imwrite(str(output), preview):
        raise OSError(f"unable to write {output}")


def evaluate(data: Path, output: Path) -> dict:
    protocol = json.loads(PROTOCOL.read_text())
    manifest = json.loads((data / "manifest.json").read_text())
    protocol_hash = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    if manifest["protocol_sha256"] != protocol_hash:
        raise ValueError("data was fetched with a different protocol")
    sequences = manifest["sequences"]
    if len(sequences) != protocol["sequence_count"] or len(set(sequences)) != len(sequences):
        raise ValueError("incomplete or duplicate sequences")
    frames = {n for pair in protocol["frame_pairs"] for n in pair}
    required = {f"DAVIS/{kind}/480p/{seq}/{n:05d}.{ext}"
                for seq in sequences for n in frames
                for kind, ext in (("JPEGImages", "jpg"), ("Annotations", "png"))}
    if len(manifest["files"]) != len(required) or {item["path"] for item in manifest["files"]} != required:
        raise ValueError("manifest does not contain exactly the frozen sample")
    for item in manifest["files"]:
        path = (data / item["path"]).resolve()
        if not path.is_relative_to(data.resolve()):
            raise ValueError("source path escapes dataset directory")
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"source hash mismatch: {item['path']}")

    output.mkdir(parents=True, exist_ok=True)
    images = output / "annotations"
    images.mkdir(exist_ok=True)
    real, controls = [], []
    rng = np.random.default_rng(protocol["control_noise_seed"])
    for sequence in sequences:
        def load(kind, n, extension):
            path = data / f"DAVIS/{kind}/480p/{sequence}/{n:05d}.{extension}"
            image = cv2.imread(str(path), cv2.IMREAD_COLOR if extension == "jpg" else cv2.IMREAD_UNCHANGED)
            if image is None:
                raise ValueError(f"cannot decode {path}")
            return image

        for first, last in protocol["frame_pairs"]:
            before, after = (load("JPEGImages", n, "jpg") for n in (first, last))
            mb, ma = (load("Annotations", n, "png") for n in (first, last))
            if before.shape[:2] != foreground(mb).shape or after.shape[:2] != foreground(ma).shape:
                raise ValueError("image/annotation dimensions differ")
            label, fraction = reference_label(mb, ma, protocol)
            row = {"id": f"{sequence}-{first:05d}-{last:05d}", "sequence": sequence,
                   "frames": [first, last], "kind": "real_pair",
                   "mask_xor_fraction": fraction, **probe(before, after, label, protocol)}
            filename = f"annotations/{row['id']}.png"
            annotation_preview(mb, ma, row["evidence_cards"], output / filename)
            row["annotation_preview"] = filename
            row["annotation_preview_sha256"] = hashlib.sha256((output / filename).read_bytes()).hexdigest()
            real.append(row)
        base = load("JPEGImages", 0, "jpg")
        variants = {
            "exact_repeat": base.copy(),
            "sensor_noise": np.clip(base.astype(np.int16) + rng.integers(-2, 3, base.shape), 0, 255).astype(np.uint8),
            "brightness_shift": np.clip(base.astype(np.int16) + protocol["control_brightness_delta"], 0, 255).astype(np.uint8),
        }
        for kind, current in variants.items():
            controls.append({"id": f"{sequence}-{kind}", "sequence": sequence, "kind": kind,
                             **probe(base, current, False, protocol)})
    by_sequence = {seq: metrics([row for row in real if row["sequence"] == seq]) for seq in sequences}
    recalls = [m["recall"] for m in by_sequence.values() if m["recall"] is not None]
    report = {
        "schema_version": 1, "protocol_id": protocol["id"], "protocol_sha256": protocol_hash,
        "frozen_detector_commit": protocol["frozen_detector_commit"],
        "detector_sha256": hashlib.sha256(Path(__file__).with_name("evidence_locker.py").read_bytes()).hexdigest(),
        "opencv_version": cv2.__version__, "numpy_version": np.__version__,
        "reference": "DAVIS human-annotated foreground occupancy XOR; a proxy, not semantic incident labels",
        "real_pairs": metrics(real), "controls": metrics(controls),
        "controls_by_kind": {kind: metrics([r for r in controls if r["kind"] == kind]) for kind in variants},
        "by_sequence": by_sequence,
        "macro_sequence_recall": sum(recalls) / len(recalls) if recalls else None,
        "macro_recall_sequence_count": len(recalls),
        "real_results": real, "control_results": controls,
        "source_manifest": manifest,
    }
    report["receipt_sha256"] = seal_report(report)
    (output / "results.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/evaluation"))
    args = parser.parse_args()
    report = evaluate(args.data_dir, args.output_dir)
    print(json.dumps({key: report[key] for key in ("real_pairs", "controls_by_kind", "macro_sequence_recall", "receipt_sha256")}, indent=2))
