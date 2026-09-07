"""Fetch only the frozen DAVIS sample, using verified HTTP byte ranges."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import struct
import urllib.request
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROTOCOL = Path(__file__).parent / "evaluation/protocol.json"


def fetch_range(protocol: dict, start: int, end: int) -> bytes:
    total = protocol["archive_bytes"]
    if not 0 <= start <= end < total or end - start > 16 * 1024 * 1024:
        raise ValueError("invalid or excessive archive range")
    request = urllib.request.Request(protocol["dataset_url"], headers={
        "Range": f"bytes={start}-{end}", "If-Match": protocol["archive_etag"],
    })
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 206:
            raise ValueError("source must support partial responses; refusing whole archive")
        if response.headers.get("Content-Range") != f"bytes {start}-{end}/{total}":
            raise ValueError("archive range/size changed")
        if response.headers.get("ETag") != protocol["archive_etag"]:
            raise ValueError("archive identity changed")
        data = response.read(end - start + 2)
    if len(data) != end - start + 1:
        raise ValueError("truncated or excessive archive response")
    return data


class ArchiveIndex(io.RawIOBase):
    """Seekable view used only to read the ZIP central directory."""
    def __init__(self, protocol: dict):
        self.protocol = protocol
        self.position = 0

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        base = {0: 0, 1: self.position, 2: self.protocol["archive_bytes"]}[whence]
        self.position = base + offset
        if self.position < 0:
            raise ValueError("negative seek")
        return self.position

    def read(self, size=-1):
        remaining = self.protocol["archive_bytes"] - self.position
        size = remaining if size < 0 else min(size, remaining)
        if size <= 0:
            return b""
        data = fetch_range(self.protocol, self.position, self.position + size - 1)
        self.position += size
        return data


def read_member(protocol: dict, item: zipfile.ZipInfo) -> bytes:
    if item.file_size > 4 * 1024 * 1024 or item.flag_bits & 1:
        raise ValueError("unsupported or excessive ZIP member")
    start = item.header_offset
    end = min(protocol["archive_bytes"] - 1, start + 30 + 1024 + item.compress_size)
    block = fetch_range(protocol, start, end)
    if block[:4] != b"PK\x03\x04":
        raise ValueError("invalid ZIP local header")
    name_len, extra_len = struct.unpack_from("<HH", block, 26)
    offset = 30 + name_len + extra_len
    raw = block[offset:offset + item.compress_size]
    if len(raw) != item.compress_size:
        raise ValueError("truncated ZIP payload")
    if item.compress_type == zipfile.ZIP_DEFLATED:
        decoder = zlib.decompressobj(-15)
        data = decoder.decompress(raw, item.file_size + 1)
        if not decoder.eof or decoder.unconsumed_tail:
            raise ValueError("invalid or excessive deflate payload")
    elif item.compress_type == zipfile.ZIP_STORED:
        data = raw
    else:
        raise ValueError("unsupported ZIP compression")
    if len(data) != item.file_size or zlib.crc32(data) != item.CRC:
        raise ValueError("ZIP size/CRC mismatch")
    return data


def fetch(output: Path) -> dict:
    protocol = json.loads(PROTOCOL.read_text())
    with zipfile.ZipFile(ArchiveIndex(protocol)) as archive:
        index = {item.filename: item for item in archive.infolist()}
    split = read_member(protocol, index[protocol["split_path"]])
    sequences = sorted(split.decode().split())[:protocol["sequence_count"]]
    if len(sequences) != protocol["sequence_count"]:
        raise ValueError("incomplete validation split")
    if len(set(sequences)) != len(sequences) or any(not re.fullmatch(r"[a-z0-9-]+", seq) for seq in sequences):
        raise ValueError("invalid validation sequence name")
    frames = sorted({n for pair in protocol["frame_pairs"] for n in pair})
    paths = [f"DAVIS/{kind}/480p/{seq}/{n:05d}.{ext}"
             for seq in sequences for n in frames
             for kind, ext in (("JPEGImages", "jpg"), ("Annotations", "png"))]
    if any(path not in index for path in paths):
        raise ValueError("frozen sample is incomplete in archive")
    output.mkdir(parents=True, exist_ok=True)

    def download(path):
        local = (output / path).resolve()
        if not local.is_relative_to(output.resolve()):
            raise ValueError("source path escapes dataset directory")
        item = index[path]
        data = local.read_bytes() if local.exists() else b""
        if len(data) != item.file_size or zlib.crc32(data) != item.CRC:
            data = read_member(protocol, item)
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_bytes(data)
        return {"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    with ThreadPoolExecutor(max_workers=4) as pool:
        files = list(pool.map(download, paths))
    manifest = {
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "archive_url": protocol["dataset_url"], "archive_etag": protocol["archive_etag"],
        "archive_bytes": protocol["archive_bytes"],
        "split_sha256": hashlib.sha256(split).hexdigest(),
        "sequences": sequences, "files": files,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = fetch(args.output_dir)
    print(json.dumps({"sequences": result["sequences"], "file_count": len(result["files"])}))
