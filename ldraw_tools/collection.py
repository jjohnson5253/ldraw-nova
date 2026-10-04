"""Compare the existing physical BOM with an explicit owned-parts snapshot."""
from collections import Counter
import re


def part_key(value):
    if not isinstance(value, str):
        return None
    value = value.casefold().removesuffix('.dat')
    return value if re.fullmatch(r'[a-z0-9_-]+', value) else None


def compare_inventory(bom, inventory):
    """Count exact part/color quantities across the whole expanded model.

    Provider rows without an unambiguous LDraw mapping remain visible as
    unmapped inventory; they cannot contribute stock to a generated model.
    """
    if not isinstance(inventory, dict) or not isinstance(inventory.get('parts'), list):
        raise ValueError('Inventory must contain a parts list')
    stock = Counter()
    unmapped = 0
    for row in inventory['parts']:
        if not isinstance(row, dict):
            raise ValueError('Each inventory row must be an object')
        quantity, colour = row.get('quantity'), row.get('colour')
        if type(quantity) is not int or not 0 <= quantity <= 100_000_000:
            raise ValueError('Inventory quantities must be nonnegative integers')
        part = part_key(row.get('part'))
        if part is None or colour is None:
            unmapped += quantity
            continue
        if type(colour) is not int or colour < 0 or colour in (16, 24):
            raise ValueError('Inventory needs explicit LDraw colors, not inherited or edge colors')
        stock[part, colour] += quantity
    required = Counter()
    descriptions = {}
    for row in bom:
        key = (part_key(row['part']), row['colour_code'])
        required[key] += row['quantity']
        descriptions[key] = row
    rows = []
    for (part, colour), quantity in required.items():
        known = part is not None and type(colour) is int and colour >= 0 and colour not in (16, 24)
        owned = min(quantity, stock[part, colour]) if known else 0
        description = descriptions[part, colour]
        rows.append(dict(part=part or description['part'], colour=colour,
                         description=description.get('description'), colour_name=description.get('colour_name'),
                         required=quantity, owned=owned, missing=quantity - owned if known else 0,
                         unresolved=0 if known else quantity))
    total = sum(row['required'] for row in rows)
    owned = sum(row['owned'] for row in rows)
    missing = sum(row['missing'] for row in rows)
    unresolved = sum(row['unresolved'] for row in rows)
    return dict(rows=rows, required=total, owned=owned, missing=missing, unresolved=unresolved,
                unmapped_inventory=unmapped, coverage=owned / total if total else None,
                matches=bool(total) and missing == 0 and unresolved == 0)
