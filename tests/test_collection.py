import json

import pytest

from conftest import mpd, ref
from ldraw_tools import cli
from ldraw_tools.collection import compare_inventory


def test_exact_colors_and_quantities_count_duplicate_bom_and_stock_rows_once():
    bom = [dict(part="3001", colour_code=4, quantity=2), dict(part="3001.dat", colour_code=4, quantity=2),
           dict(part="3001", colour_code=1, quantity=1)]
    stock = {"parts": [dict(part="3001.DAT", colour=4, quantity=1), dict(part="3001", colour=4, quantity=2),
                       dict(part="3001", colour=1, quantity=10), dict(part=None, colour=None, quantity=5)]}
    report = compare_inventory(bom, stock)
    assert (report["required"], report["owned"], report["missing"], report["unmapped_inventory"]) == (5, 4, 1, 5)
    assert not report["matches"] and len(report["rows"]) == 2
    stock["parts"][0]["quantity"] += 1
    assert compare_inventory(bom, stock)["matches"]


@pytest.mark.parametrize("quantity", [-1, 1.5, True, "2"])
def test_inventory_rejects_invalid_quantities(quantity):
    with pytest.raises(ValueError):
        compare_inventory([], {"parts": [dict(part="3001", colour=4, quantity=quantity)]})


def test_inherited_color_and_empty_model_never_claim_inventory_success():
    stock = {"parts": [dict(part="3001", colour=4, quantity=2)]}
    report = compare_inventory([dict(part="3001", colour_code=16, quantity=1)], stock)
    assert not report["matches"] and report["unresolved"] == 1 and report["owned"] == 0
    assert not compare_inventory([], stock)["matches"]
    with pytest.raises(ValueError):
        compare_inventory([], {"parts": [dict(part="3001", colour=16, quantity=2)]})


def test_bom_inventory_cli_expands_repeated_submodels_with_inherited_color(tmp_path, monkeypatch, parts):
    model = tmp_path / "model.mpd"
    model.write_text(mpd(ref("unit.ldr", position="0 0 0") + "\n" + ref("unit.ldr", position="100 0 0")) + mpd(ref(colour=16), "unit.ldr"))
    inventory = tmp_path / "owned.json"
    monkeypatch.setattr(cli, "get_parts", lambda *a, **kw: parts)
    monkeypatch.setattr(cli, "library_path", lambda *a: parts.path.parent)
    args = cli.parser().parse_args(["bom", str(model), "--inventory", str(inventory)])
    inventory.write_text(json.dumps({"parts": [dict(part="3001", colour=4, quantity=1)]}))
    report, status = cli.run(args)
    assert status == 1 and report["checks_passed"]
    assert report["inventory"]["required"] == 2 and report["inventory"]["missing"] == 1
    inventory.write_text(json.dumps({"parts": [dict(part="3001", colour=4, quantity=2)]}))
    report, status = cli.run(args)
    assert status == 0 and report["inventory"]["matches"]
