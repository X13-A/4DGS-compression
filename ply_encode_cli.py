#!/usr/bin/env python3
"""CLI for encoding PLY files into PNG textures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from ply_loader import PlyLoader
from ply_texture_encoder import PlyTextureEncoder, save_texture


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Encode a PLY file into PNG textures.")
    parser.add_argument("ply_path", help="Path to the PLY file to encode.")
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Directory to write textures and metadata.",
    )
    parser.add_argument(
        "--png-compression",
        type=int,
        default=0,
        help="PNG compression level (0-9).",
    )
    parser.add_argument(
        "--element",
        default="vertex",
        help="PLY element name to encode.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    loader = PlyLoader()
    try:
        ply = loader.load(args.ply_path)
    except FileNotFoundError:
        print(f"Error: file not found: {args.ply_path}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Error: failed to read PLY: {exc}", file=sys.stderr)
        return 2

    loader.summarize(ply)
    
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(args.ply_path).stem

    encoder = PlyTextureEncoder()
    encoded = encoder.encode(ply, element_name=args.element)

    file_map: dict[str, str] = {}
    for group in encoded.groups:
        file_name = f"{stem}_{group.name}.png"
        output_path = out_dir / file_name
        save_texture(
            output_path,
            group.texture,
            group.min_values,
            group.max_values,
            png_compression=args.png_compression,
            bit_depth=group.bit_depth,
        )
        file_map[group.name] = file_name
        print(f"Texture saved to: {output_path}")

    metadata = encoded.to_metadata(Path(args.ply_path).name, file_map)
    metadata_path = out_dir / f"{stem}_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Metadata saved to: {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
