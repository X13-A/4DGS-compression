#!/usr/bin/env python3
"""Decode H.264 texture videos back into PLYs without writing textures to disk."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from ply_texture_decoder import PlyTextureDecoder, save_ply


_FRAME_RE = re.compile(r"^FRAME_(\d+)_metadata\.json$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decode per-texture videos into PLYs without writing textures to disk."
    )
    parser.add_argument(
        "--videos-dir",
        required=True,
        help="Directory containing per-group videos (xyz_0.mp4, color.mp4, etc).",
    )
    parser.add_argument(
        "--metadata-dir",
        required=True,
        help="Directory containing FRAME_i_metadata.json files.",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Directory to write reconstructed PLY files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    videos_dir = Path(args.videos_dir)
    metadata_dir = Path(args.metadata_dir)
    out_dir = Path(args.out_dir)

    if not videos_dir.exists():
        raise FileNotFoundError(f"Videos dir not found: {videos_dir}")
    if not metadata_dir.exists():
        raise FileNotFoundError(f"Metadata dir not found: {metadata_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)

    metadata_files = sorted(metadata_dir.glob("*_metadata.json"), key=_metadata_sort_key)
    if not metadata_files:
        raise FileNotFoundError(f"No *_metadata.json files found in {metadata_dir}")

    video_caps = _open_videos(videos_dir)
    decoder = PlyTextureDecoder()

    for index, meta_path in enumerate(metadata_files):
        frame_index = _frame_index_from_meta(meta_path)
        if frame_index is None:
            frame_index = index

        metadata = _load_metadata(meta_path)
        textures = _read_frame_textures(metadata, video_caps, frame_index)
        ply = decoder.decode_from_textures(metadata, textures)

        source_stem = meta_path.stem.replace("_metadata", "")
        output_path = out_dir / f"{source_stem}_reconstructed.ply"
        save_ply(ply, output_path)
        print(f"Reconstructed PLY saved to: {output_path}")

    for cap in video_caps.values():
        cap.release()

    return 0


def _metadata_sort_key(path: Path) -> tuple[int, str]:
    index = _frame_index_from_meta(path)
    if index is None:
        return (2**31 - 1, path.name)
    return (index, path.name)


def _frame_index_from_meta(path: Path) -> int | None:
    match = _FRAME_RE.match(path.name)
    if not match:
        return None
    return int(match.group(1))


def _open_videos(videos_dir: Path) -> dict[str, cv2.VideoCapture]:
    videos = list(videos_dir.glob("*.mp4")) + list(videos_dir.glob("*.mkv"))
    if not videos:
        raise FileNotFoundError(f"No .mp4 or .mkv files found in {videos_dir}")

    caps: dict[str, cv2.VideoCapture] = {}
    for video in videos:
        group_name = video.stem
        cap = cv2.VideoCapture(str(video))
        if not cap.isOpened():
            raise ValueError(f"Failed to open video: {video}")
        caps[group_name] = cap
    return caps


def _read_frame_textures(
    metadata: dict[str, Any],
    video_caps: dict[str, cv2.VideoCapture],
    frame_index: int,
) -> dict[str, np.ndarray]:
    textures: dict[str, np.ndarray] = {}
    for group in metadata["groups"]:
        group_name = group["name"]
        if group_name not in video_caps:
            raise ValueError(f"Missing video for group '{group_name}'")

        expected_channels = len(group["properties"])
        if expected_channels == 4:
            raise ValueError(
                f"Group '{group_name}' has 4 channels; H.264 cannot preserve 4 channels."
            )

        frame = _read_frame(video_caps[group_name], frame_index, group_name)
        frame = _coerce_channels(frame, expected_channels, group_name)
        textures[group_name] = frame.astype(np.float32)

    return textures


def _read_frame(
    cap: cv2.VideoCapture, frame_index: int, group_name: str
) -> np.ndarray:
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    if not ok or frame is None:
        raise ValueError(f"Failed to read frame {frame_index} for group '{group_name}'")
    return frame


def _coerce_channels(
    frame: np.ndarray, expected_channels: int, group_name: str
) -> np.ndarray:
    if frame.ndim == 2:
        channels = 1
    else:
        channels = frame.shape[2]

    if expected_channels == 1:
        if channels == 1:
            return frame
        return frame[:, :, 0]

    if expected_channels == 3:
        if channels == 3:
            return frame
        if channels == 4:
            return frame[:, :, :3]
        raise ValueError(
            f"Group '{group_name}' expected 3 channels but got {channels}"
        )

    raise ValueError(
        f"Group '{group_name}' expected {expected_channels} channels; unsupported"
    )


def _load_metadata(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    raise SystemExit(main())
