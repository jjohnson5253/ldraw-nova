"""Exact LDraw part/color palettes and optional quantity limits.

CSV columns: part_id, color_id; optional name, max_quantity.
Unknown columns are ignored and omitted from canonical palette exports.
"""
from __future__ import annotations

import csv
import io
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

PART_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
MAX_CATALOG_BYTES = 16 * 1024 * 1024


def normalize_part_id(value: str) -> str:
    value = value.strip().lower().replace("\\", "/")
    if value.startswith("parts/"):
        value = value[6:]
    if value.endswith(".dat"):
        value = value[:-4]
    if not PART_ID.fullmatch(value):
        raise ValueError("Invalid LDraw part identifier")
    return value


@dataclass(frozen=True)
class CatalogPart:
    part_id: str
    color_id: int
    name: str
    max_quantity: int | None = None


class PartsUnavailable(ValueError):
    """An actionable, bounded report for the agent or inventory caller."""


class PartsCatalog:
    def __init__(self, parts: list[CatalogPart]):
        self.parts = {}
        for part in parts:
            key = (part.part_id, part.color_id)
            if key in self.parts and self.parts[key] != part:
                raise ValueError(f"Ambiguous catalog mapping: {part.part_id}/{part.color_id}")
            self.parts[key] = part
        if not self.parts:
            raise ValueError("Parts palette has no mapped parts")

    @classmethod
    def from_csv(cls, content: str) -> PartsCatalog:
        if len(content.encode()) > MAX_CATALOG_BYTES:
            raise ValueError("Parts catalog exceeds its size limit")
        reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
        required = {"part_id", "color_id"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Parts catalog is missing required columns")
        parts = []
        for row in reader:
            if not row["part_id"] or not row["color_id"]:
                continue
            color = int(row["color_id"])
            limit = int(row["max_quantity"]) if row.get("max_quantity") else None
            if color < 0 or color in {16, 24} or limit is not None and limit < 0:
                raise ValueError("Invalid catalog color or quantity limit")
            part_name = row.get('name') or row['part_id']
            if len(part_name) > 300:
                raise ValueError("Invalid catalog description")
            parts.append(CatalogPart(normalize_part_id(row["part_id"]), color,
                part_name, limit))
        return cls(parts)

    @classmethod
    def load(cls, path: Path) -> PartsCatalog:
        if path.stat().st_size > MAX_CATALOG_BYTES:
            raise ValueError("Parts catalog exceeds its size limit")
        return cls.from_csv(path.read_text(encoding="utf-8"))

    def validate(self, inventory: dict[tuple[str, int], int]) -> None:
        errors, quantities = [], Counter()
        for (part_id, color), quantity in inventory.items():
            if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
                raise ValueError("Part quantities must be positive integers")
            part = self.parts.get((normalize_part_id(part_id), color))
            if part is None:
                errors.append(f"{part_id}.dat color {color} (x{quantity})")
                continue
            quantities[(part.part_id, color)] += quantity
        for key, quantity in quantities.items():
            limit = self.parts[key].max_quantity
            if limit is not None and quantity > limit:
                errors.append(f"{key[0]}.dat color {key[1]}: requested {quantity}, available {limit}")
        if errors:
            remaining = f"; and {len(errors) - 20} more" if len(errors) > 20 else ""
            raise PartsUnavailable("Parts unavailable in the allowed catalog: " + "; ".join(errors[:20]) + remaining)
        if not inventory:
            raise ValueError("Model contains no physical parts")

    def to_csv(self) -> str:
        """Serialize only palette fields, keeping external metadata out of Nova."""
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["part_id", "color_id", "name", "max_quantity"])
        for part in sorted(self.parts.values(), key=lambda item: (item.part_id, item.color_id)):
            writer.writerow([part.part_id, part.color_id, part.name,
                             part.max_quantity if part.max_quantity is not None else ""])
        return output.getvalue()

    def search(self, query: str = "", color_id: int | None = None, *, offset: int = 0, limit: int = 50) -> dict:
        query = query.casefold().strip()
        rows = [part for part in self.parts.values()
                if (color_id is None or part.color_id == color_id)
                and (not query or query in f"{part.part_id} {part.name}".casefold())]
        rows.sort(key=lambda part: (part.part_id, part.color_id))
        return {"total": len(rows), "parts": [
            {"part_id": part.part_id + ".dat", "color_id": part.color_id,
             "name": part.name,
             "max_quantity": part.max_quantity} for part in rows[offset:offset + limit]]}


def reject_custom_parts(content: str) -> None:
    for line in content.splitlines():
        tokens = line.split()
        if tokens[:2] == ['0', '!COLOUR']:
            raise PartsUnavailable('Custom colors are not allowed by the parts catalog')
        if tokens[:2] == ['0', 'FILE'] and tokens[-1].lower().endswith('.dat'):
            raise PartsUnavailable('Embedded DAT definitions cannot override library parts')
        if tokens and tokens[0] in {'2', '3', '4', '5'}:
            raise PartsUnavailable('Custom geometry is not an allowed library part')
