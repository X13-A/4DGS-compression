"""Encode PLY element data into per-group PNG textures."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np
from plyfile import PlyData


@dataclass(frozen=True)
class GroupTexture:
    name: str
    properties: list[str]
    texture: np.ndarray
    min_values: list[float]
    max_values: list[float]
    bit_depth: int


@dataclass(frozen=True)
class EncodedTextures:
    element_name: str
    entry_count: int
    width: int
    height: int
    property_order: list[str]
    property_types: dict[str, str]
    format_value: str
    version_value: str
    groups: list[GroupTexture]

    def to_metadata(self, source_name: str, file_map: dict[str, str]) -> dict[str, object]:
        return {
            "version": 1,
            "source_ply": source_name,
            "element_name": self.element_name,
            "entry_count": self.entry_count,
            "texture_size": {"width": self.width, "height": self.height},
            "format": self.format_value,
            "format_version": self.version_value,
            "property_order": list(self.property_order),
            "property_types": dict(self.property_types),
            "groups": [
                {
                    "name": group.name,
                    "properties": list(group.properties),
                    "channels": len(group.properties),
                    "min": list(group.min_values),
                    "max": list(group.max_values),
                    "file": file_map[group.name],
                    "bit_depth": group.bit_depth,
                }
                for group in self.groups
            ],
        }


class PlyTextureEncoder:
    def encode(self, ply: PlyData, element_name: str = "vertex") -> EncodedTextures:
        if element_name not in ply:
            raise ValueError(f"Element not found: {element_name}")

        # Build per-vertex textures and capture normalization ranges.
        element = ply[element_name]
        entry_count = int(element.count)
        width, height = self._select_texture_size(entry_count)
        property_order = [prop.name for prop in element.properties]
        property_types = {
            prop.name: np.dtype(prop.dtype() if callable(prop.dtype) else prop.dtype).str
            for prop in element.properties
        }
        format_value, version_value = _extract_format_version(ply)

        groups: list[GroupTexture] = []
        for group_name, props in self._property_groups(element):
            channel_count = len(props)
            if channel_count > 4:
                raise ValueError(
                    f"Group '{group_name}' has {channel_count} properties; max is 4."
                )

            bit_depth = 16 if group_name == "xyz" else 8
            writer = _TextureWriter(width, height, channel_count)
            self._write_property_group(element, props, writer, 0)
            texture = writer.finalize()
            min_values, max_values = _channel_stats(texture, entry_count)
            groups.append(
                GroupTexture(
                    name=group_name,
                    properties=props,
                    texture=texture,
                    min_values=min_values,
                    max_values=max_values,
                    bit_depth=bit_depth,
                )
            )

        return EncodedTextures(
            element_name=element_name,
            entry_count=entry_count,
            width=width,
            height=height,
            property_order=property_order,
            property_types=property_types,
            format_value=format_value,
            version_value=version_value,
            groups=groups,
        )

    def _select_texture_size(self, entry_count: int) -> tuple[int, int]:
        if entry_count <= 0:
            return 1, 1
        root = int(math.sqrt(entry_count))
        best_width = root
        best_height = math.ceil(entry_count / best_width)
        best_area = best_width * best_height
        best_diff = abs(best_width - best_height)

        # Find the smallest near-square rectangle that fits all entries.
        width = root
        while width <= entry_count:
            height = math.ceil(entry_count / width)
            area = width * height
            diff = abs(width - height)
            if diff < best_diff or (diff == best_diff and area < best_area):
                best_width = width
                best_height = height
                best_area = area
                best_diff = diff
            if width >= height:
                break
            width += 1

        return best_width, best_height

    def _write_property_group(
        self,
        element,
        property_names: list[str],
        writer: "_TextureWriter",
        start_index: int,
    ) -> int:
        index = start_index
        arrays = [element.data[name] for name in property_names]
        length = len(arrays[0]) if arrays else 0
        for i in range(length):
            channel_values: list[float] = []
            for values in arrays:
                flattened = list(_flatten_value(values[i]))
                if len(flattened) != 1:
                    raise ValueError("Property values must be scalar for texture output")
                channel_values.append(_coerce_float(flattened[0]))

            writer.write_by_index(index, channel_values)
            index += 1
        return index

    def _property_groups(self, element) -> list[tuple[str, list[str]]]:
        prop_names = [prop.name for prop in element.properties]
        remaining = set(prop_names)
        groups: list[tuple[str, list[str]]] = []

        def add_group(group_name: str, names: list[str]) -> None:
            if all(name in remaining for name in names):
                groups.append((group_name, names))
                for name in names:
                    remaining.remove(name)

        add_group("xyz", ["x", "y", "z"])
        add_group("color", ["f_dc_0", "f_dc_1", "f_dc_2"])
        add_group("scale", ["scale_0", "scale_1", "scale_2"])
        if all(name in remaining for name in ["rot_0", "rot_1", "rot_2", "rot_3"]):
            add_group("rotation", ["rot_0", "rot_1", "rot_2", "rot_3"])
        else:
            add_group("rotation", ["rot_0", "rot_1", "rot_2"])
        add_group("opacity", ["opacity"])

        for name in prop_names:
            if name in remaining:
                groups.append((name, [name]))
                remaining.remove(name)

        return groups


class _TextureWriter:
    def __init__(self, width: int, height: int, channels: int) -> None:
        # Float32 storage; normalization happens during PNG export.
        shape = (height, width) if channels == 1 else (height, width, channels)
        self._data = np.zeros(shape, dtype=np.float32)
        self._width = width
        self._height = height
        self._channels = channels

    def write_by_index(self, index: int, values: list[float]) -> None:
        if index < 0 or index >= self._width * self._height:
            raise ValueError("Texture writer overflow")
        if len(values) != self._channels:
            raise ValueError("Channel count mismatch for texture writer")
        row = index // self._width
        col = index % self._width
        if self._channels == 1:
            self._data[row, col] = values[0]
        else:
            self._data[row, col, :] = values

    def finalize(self) -> np.ndarray:
        return self._data


def save_texture(
    path: str | Path,
    texture: np.ndarray,
    min_values: list[float],
    max_values: list[float],
    png_compression: int = 0,
    bit_depth: int = 8,
) -> None:
    if texture.ndim not in (2, 3):
        raise ValueError("Texture data must be 2D or 3D array")
    if texture.ndim == 3 and texture.shape[2] not in (1, 3, 4):
        raise ValueError("Only 1, 3, or 4 channel textures can be saved")
    if png_compression < 0 or png_compression > 9:
        raise ValueError("PNG compression must be between 0 and 9")
    if bit_depth not in (8, 16):
        raise ValueError("Bit depth must be 8 or 16")

    # Normalize using the stored per-channel bounds for round-trip decoding.
    output = _normalize_texture(texture, min_values, max_values, bit_depth)
    params = [cv2.IMWRITE_PNG_COMPRESSION, png_compression]
    if not cv2.imwrite(str(Path(path)), output, params):
        raise ValueError(f"Failed to write texture to {path}")


def _normalize_texture(
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

    max_code = 65535.0 if bit_depth == 16 else 255.0
    output_dtype = np.uint16 if bit_depth == 16 else np.uint8
    output = np.zeros_like(data, dtype=output_dtype)
    for channel in range(channels):
        channel_data = data[:, :, channel]
        min_value = min_values[channel]
        max_value = max_values[channel]
        if max_value <= min_value:
            output[:, :, channel] = 0
            continue
        scaled = (channel_data - min_value) / (max_value - min_value)
        output[:, :, channel] = np.clip(scaled * max_code, 0, max_code).astype(
            output_dtype
        )

    if output.shape[2] == 1:
        return output[:, :, 0]
    return output


def _channel_stats(texture: np.ndarray, entry_count: int) -> tuple[list[float], list[float]]:
    data = texture.astype(np.float32)
    if data.ndim == 2:
        data = data[:, :, None]
    channels = data.shape[2]
    flat = data.reshape(-1, channels)[:entry_count]
    if flat.size == 0:
        return [0.0] * channels, [0.0] * channels

    min_values = [float(np.min(flat[:, channel])) for channel in range(channels)]
    max_values = [float(np.max(flat[:, channel])) for channel in range(channels)]
    return min_values, max_values


def _extract_format_version(ply: PlyData) -> tuple[str, str]:
    header = ply.header
    format_value = getattr(header, "format", None)
    version_value = getattr(header, "version", None)
    if format_value and version_value:
        return str(format_value), str(version_value)

    if isinstance(header, str):
        for line in header.splitlines():
            parts = line.strip().split()
            if len(parts) >= 3 and parts[0] == "format":
                return parts[1], parts[2]

    return "unknown", "unknown"


def _flatten_value(value: object) -> Iterator[object]:
    if value is None:
        return iter(())
    if isinstance(value, (str, bytes)):
        return iter((value,))
    if isinstance(value, (list, tuple)):
        return iter(value)
    try:
        return iter(value)  # type: ignore[arg-type]
    except TypeError:
        return iter((value,))


def _coerce_float(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isfinite(number):
        return number
    return 0.0
