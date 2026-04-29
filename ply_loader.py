"""Load and summarize PLY files."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from plyfile import PlyData


class PlyLoader:
    def load(self, ply_path: str) -> PlyData:
        return PlyData.read(ply_path)

    def _extract_format_version(self, ply: PlyData) -> tuple[str, str]:
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

    def summarize(self, ply: PlyData) -> None:
        format_value, version_value = self._extract_format_version(ply)
        elements = []
        for element in ply.elements:
            properties = []
            for prop in element.properties:
                dtype_value = prop.dtype() if callable(prop.dtype) else prop.dtype
                dtype = str(dtype_value)
                size = int(np.dtype(dtype_value).itemsize)
                properties.append((prop.name, dtype, size))
            elements.append((element.name, element.count, properties))

        lines: list[str] = []
        lines.append(f"Format: {format_value}")
        lines.append(f"Version: {version_value}")
        lines.append("Elements:")
        for name, count, properties in elements:
            lines.append(f"  - {name}: {count} entries")
            for prop_name, dtype, size in properties:
                lines.append(f"    - {prop_name}: {dtype}, {size} bytes")
        print("\n".join(lines))
