import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from ply_loader import PlyLoader
from ply_texture_encoder import PlyTextureEncoder, save_texture


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Encode a PLY file into PNG textures.")
    parser.add_argument(
        "ply_path",
        nargs="?",
        help="Path to the PLY file to encode (omit when using --ply-dir).",
    )
    parser.add_argument(
        "--ply-dir",
        help="Directory containing PLY files to encode.",
    )
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
    return parser.parse_args(argv)


def _encode_one(
    ply_path: Path,
    out_dir: Path,
    png_compression: int,
    name_prefix: str,
) -> None:
    loader = PlyLoader()
    try:
        ply = loader.load(str(ply_path))
    except FileNotFoundError:
        print(f"Error: file not found: {ply_path}", file=sys.stderr)
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"Error: failed to read PLY: {exc}", file=sys.stderr)
        raise

    loader.summarize(ply)

    encoder = PlyTextureEncoder()
    encoded = encoder.encode(ply)

    file_map: dict[str, str] = {}
    for group in encoded.groups:
        file_name = f"{name_prefix}{group.name}.png"
        output_path = out_dir / file_name
        normalize = group.name not in ("xyz_0", "xyz_1")
        save_texture(
            output_path,
            group.texture,
            group.min_values,
            group.max_values,
            png_compression=png_compression,
            bit_depth=group.bit_depth,
            normalize=normalize,
        )
        file_map[group.name] = file_name
        print(f"Texture saved to: {output_path}")

    metadata = encoded.to_metadata(ply_path.name, file_map)
    metadata_path = out_dir / f"{name_prefix}metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Metadata saved to: {metadata_path}")


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.ply_path and args.ply_dir:
        print("Error: provide either a PLY path or --ply-dir, not both.", file=sys.stderr)
        return 2
    if not args.ply_path and not args.ply_dir:
        print("Error: provide a PLY path or --ply-dir.", file=sys.stderr)
        return 2

    if args.ply_dir:
        ply_dir = Path(args.ply_dir)
        if not ply_dir.is_dir():
            print(f"Error: not a directory: {ply_dir}", file=sys.stderr)
            return 2
        ply_paths = sorted(ply_dir.glob("*.ply"))
        if not ply_paths:
            print(f"Error: no .ply files found in {ply_dir}", file=sys.stderr)
            return 2

        for index, ply_path in enumerate(ply_paths):
            name_prefix = f"FRAME_{index}_"
            try:
                _encode_one(
                    ply_path,
                    out_dir,
                    args.png_compression,
                    name_prefix,
                )
            except Exception:
                return 2
        return 0

    ply_path = Path(args.ply_path)
    name_prefix = f"{ply_path.stem}_"
    try:
        _encode_one(
            ply_path,
            out_dir,
            args.png_compression,
            name_prefix,
        )
    except Exception:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
