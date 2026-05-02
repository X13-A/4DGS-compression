"""Decode PNG textures into a reconstructed PLY file."""

import json
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np
from plyfile import PlyData, PlyElement

TextureLoader = Callable[[str, str], np.ndarray]


class PlyTextureDecoder:
    def decode(self, metadata_path: str | Path, textures_dir: str | Path) -> PlyData:
        metadata = _load_metadata(metadata_path)
        textures_dir = Path(textures_dir)

        def loader(group_name: str, file_name: str) -> np.ndarray:
            return _read_texture(textures_dir / file_name)

        return _decode_with_loader(metadata, loader)

    def decode_from_textures(
        self,
        metadata: dict[str, Any],
        textures_by_group: dict[str, np.ndarray],
    ) -> PlyData:
        def loader(group_name: str, file_name: str) -> np.ndarray:
            if group_name not in textures_by_group:
                raise ValueError(f"Missing texture for group '{group_name}'")
            return textures_by_group[group_name]

        return _decode_with_loader(metadata, loader)


def save_ply(ply: PlyData, output_path: str | Path) -> None:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    ply.write(str(target))


def _read_texture(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(f"Texture file not found: {path}")
    texture = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if texture is None:
        raise ValueError(f"Failed to read texture: {path}")
    if texture.ndim == 2:
        return texture.astype(np.float32)
    if texture.shape[2] not in (1, 3, 4):
        raise ValueError(f"Unsupported channel count in texture: {path}")
    return texture.astype(np.float32)


def _decode_with_loader(metadata: dict[str, Any], texture_loader: TextureLoader) -> PlyData:
    element_name = metadata["element_name"]
    entry_count = int(metadata["entry_count"])
    texture_size = metadata["texture_size"]
    width = int(texture_size["width"])
    height = int(texture_size["height"])
    property_order = list(metadata["property_order"])
    property_types = dict(metadata["property_types"])

    values: dict[str, np.ndarray] = {}
    for group in metadata["groups"]:
        group_name = group["name"]
        properties = list(group["properties"])
        file_name = group["file"]
        min_values = list(group["min"])
        max_values = list(group["max"])
        bit_depth = int(group.get("bit_depth", 8))

        texture = texture_loader(group_name, file_name)
        if texture.shape[0] != height or texture.shape[1] != width:
            raise ValueError(
                f"Texture {group_name} has unexpected dimensions {texture.shape}"
            )
        data = _denormalize_texture(texture, min_values, max_values, bit_depth)
        flat = _flatten_texture(data)[:entry_count]

        if flat.shape[1] != len(properties):
            raise ValueError(
                f"Texture {group_name} has {flat.shape[1]} channels; "
                f"expected {len(properties)}"
            )

        for channel_index, prop_name in enumerate(properties):
            values[prop_name] = flat[:, channel_index]

    dtype = [(name, np.dtype(property_types[name])) for name in property_order]
    data = np.empty(entry_count, dtype=dtype)
    for name in property_order:
        if name not in values:
            raise ValueError(f"Missing data for property '{name}'")
        data[name] = values[name]

    element = PlyElement.describe(data, element_name)
    text, byte_order = _format_settings(metadata.get("format", "unknown"))
    return PlyData([element], text=text, byte_order=byte_order)


def _denormalize_texture(
    texture: np.ndarray,
    min_values: list[float],
    max_values: list[float],
    bit_depth: int,
) -> np.ndarray:
    data = texture.astype(np.float32)
    if data.ndim == 2:
        data = data[:, :, None]
    channels = data.shape[2]
    if channels != len(min_values) or channels != len(max_values):
        raise ValueError("Normalization bounds do not match channel count")
    if bit_depth not in (8, 16):
        raise ValueError("Bit depth must be 8 or 16")

    max_code = 65535.0 if bit_depth == 16 else 255.0
    output = np.zeros_like(data, dtype=np.float32)
    for channel in range(channels):
        min_value = float(min_values[channel])
        max_value = float(max_values[channel])
        if max_value <= min_value:
            output[:, :, channel] = min_value
            continue
        scaled = data[:, :, channel] / max_code
        output[:, :, channel] = scaled * (max_value - min_value) + min_value

    if output.shape[2] == 1:
        return output[:, :, 0]
    return output



def _flatten_texture(texture: np.ndarray) -> np.ndarray:
    data = texture.astype(np.float32)
    if data.ndim == 2:
        data = data[:, :, None]
    channels = data.shape[2]
    return data.reshape(-1, channels)


def _load_metadata(path: str | Path) -> dict[str, Any]:
    metadata_path = Path(path)
    with metadata_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _format_settings(format_value: str) -> tuple[bool, str]:
    if format_value == "ascii":
        return True, "="
    if format_value == "binary_big_endian":
        return False, ">"
    if format_value == "binary_little_endian":
        return False, "<"
    return False, "="
