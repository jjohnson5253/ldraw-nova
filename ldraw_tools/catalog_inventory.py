"""Expand an MPD into physical inventory, optionally checking a supplier CSV.

Run with the toolkit interpreter: python -m ldraw_tools.catalog_inventory
MODEL LIBRARY [--catalog CSV]. Unknown dependencies and custom parts fail closed.
"""
from __future__ import annotations

import argparse
import json
import math
import tempfile
from collections import Counter
from pathlib import Path

from .parts_catalog import PartsCatalog, normalize_part_id, reject_custom_parts


def model_inventory(source: Path, library: Path) -> dict[tuple[str, int], int]:
    from . import common, document

    if source.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("Model exceeds the 32 MB inventory limit")
    reject_custom_parts(source.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="nova-inventory-") as temporary:
        original_cache = common.CACHE, document.CACHE
        common.CACHE = document.CACHE = Path(temporary) / "cache"
        try:
            physical, _ = document.physical_context(document.parse_source(source), common.get_parts(library))
            inventory = Counter()
            for index, occurrence in enumerate(physical.iter_occurrences()):
                if index >= 100_000:
                    raise ValueError("Model exceeds the 100,000 physical parts limit")
                if not occurrence.reference.lower().endswith(".dat"):
                    raise ValueError("Unresolved dependency in physical inventory")
                values = [occurrence.position.x, occurrence.position.y, occurrence.position.z,
                          *(number for row in occurrence.matrix.rows for number in row)]
                if not all(math.isfinite(float(number)) for number in values):
                    raise ValueError("Invalid physical placement")
                inventory[(normalize_part_id(occurrence.reference), occurrence.colour.code)] += 1
            if not inventory:
                raise ValueError("Model contains no physical parts")
            return dict(inventory)
        finally:
            common.CACHE, document.CACHE = original_cache


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("library", type=Path)
    parser.add_argument("--catalog", type=Path)
    args = parser.parse_args()
    inventory = model_inventory(args.source, args.library)
    if args.catalog:
        PartsCatalog.load(args.catalog).validate(inventory)
    print(json.dumps([[part, color, quantity] for (part, color), quantity in inventory.items()]))


if __name__ == "__main__":
    main()
