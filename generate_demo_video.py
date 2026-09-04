"""Generate a small, right-cleared synthetic MP4 for the AWS smoke run."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def generate(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (320, 180)
    )
    if not writer.isOpened():
        raise RuntimeError("OpenCV could not create the synthetic MP4")
    try:
        for index in range(20):
            frame = np.zeros((180, 320, 3), dtype=np.uint8)
            if index >= 10:
                cv2.rectangle(frame, (70, 45), (249, 134), (90, 230, 170), thickness=-1)
            writer.write(frame)
    finally:
        writer.release()
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("synthetic MP4 was not written")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    generate(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
