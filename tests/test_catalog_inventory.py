from pathlib import Path
import pytest
from ldraw_tools.catalog_inventory import model_inventory, check_rigid_transform
from ldraw_tools.parts_catalog import PartsCatalog, PartsUnavailable

MODEL = '0 FILE root.ldr\n1 4 0 0 0 1 0 0 0 1 0 0 0 1 child.ldr\n0 FILE child.ldr\n1 16 0 0 0 1 0 0 0 1 0 0 0 1 3001.dat\n'


def library():
    path = Path('/opt/ldraw/ldraw')
    if not path.exists():
        pytest.skip('Real LDraw library available in the Nova image')
    return path


def test_real_hierarchy_colors_and_unknown_dependencies(tmp_path):
    source = tmp_path / 'model.mpd'; source.write_text(MODEL)
    inventory = model_inventory(source, library())
    assert inventory == {('3001', 4): 1}
    catalog = PartsCatalog.from_csv('part_id,color_id\n3001,4\n')
    catalog.validate(inventory)
    source.write_text(MODEL.replace('1 4 ', '1 0 '))
    with pytest.raises(PartsUnavailable):
        catalog.validate(model_inventory(source, library()))
    source.write_text(MODEL.replace('3001.dat', 'missing.ldr'))
    with pytest.raises((ValueError, FileNotFoundError, KeyError)):
        model_inventory(source, library())


def test_real_parser_rejects_supplier_impersonation(tmp_path):
    source = tmp_path / 'model.mpd'; source.write_text(MODEL + '0 FILE 3001.dat\n0 Fake\n')
    with pytest.raises(PartsUnavailable):
        model_inventory(source, library())


def test_palette_parts_allow_rotations_but_not_changed_geometry():
    check_rigid_transform([[0.707107, 0, 0.707107], [0, 1, 0], [-0.707107, 0, 0.707107]])
    for rows in ([[2, 0, 0], [0, 1, 0], [0, 0, 1]],
                 [[1, .1, 0], [0, 1, 0], [0, 0, 1]],
                 [[-1, 0, 0], [0, 1, 0], [0, 0, 1]],
                 [[float('nan'), 0, 0], [0, 1, 0], [0, 0, 1]]):
        with pytest.raises(ValueError):
            check_rigid_transform(rows)


def test_unknown_dat_and_scaled_parts_fail_closed(tmp_path):
    source = tmp_path / 'model.mpd'
    for content in (MODEL.replace('3001.dat', 'missing.dat'),
                    MODEL.replace('1 16 0 0 0 1 ', '1 16 0 0 0 2 ')):
        source.write_text(content)
        with pytest.raises((ValueError, FileNotFoundError, KeyError)):
            model_inventory(source, library())
