#!/usr/bin/env python3
"""CLI for decoding PNG textures back into a PLY file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from ply_texture_decoder import PlyTextureDecoder, save_ply


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Decode PNG textures into a PLY file.")
    parser.add_argument(
        "--metadata",
        required=True,
        help="Path to the metadata JSON produced by the encoder.",
    )
    parser.add_argument(
        "--textures-dir",
        required=True,
        help="Directory containing the PNG textures.",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Directory to write the reconstructed PLY file.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    decoder = PlyTextureDecoder()
    try:
        ply = decoder.decode(args.metadata, args.textures_dir)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Error: failed to decode textures: {exc}", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    source_stem = Path(args.metadata).stem.replace("_metadata", "")
    output_path = out_dir / f"{source_stem}_reconstructed.ply"
    save_ply(ply, output_path)
    print(f"Reconstructed PLY saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
