import pytest
from ldraw_tools.parts_catalog import PartsCatalog, PartsUnavailable, normalize_part_id

CATALOG = ('part_id,color_id,name,max_quantity\n'
           '3001,4,Brick 2 x 4,4\n'
           '3001,36,Brick 2 x 4 transparent,\n'
           '3005,4,Brick 1 x 1,\n')


def test_exact_color_quantity_and_normalization():
    catalog = PartsCatalog.from_csv(CATALOG)
    catalog.validate({('PARTS/3001.DAT', 4): 4, ('3001', 36): 1})
    for inventory in ({('3001', 0): 1}, {('3001', 4): 5}, {('unknown', 4): 1}):
        with pytest.raises(PartsUnavailable):
            catalog.validate(inventory)
    for quantity in (0, -1, 1.5, True):
        with pytest.raises(ValueError):
            catalog.validate({('3001', 4): quantity})


def test_search_returns_bounded_relevant_pairs_without_pricing():
    catalog = PartsCatalog.from_csv(CATALOG)
    assert catalog.search('transparent')['parts'][0]['color_id'] == 36
    assert catalog.search('3001', 4)['total'] == 1
    assert len(catalog.search(limit=1)['parts']) == 1
    assert catalog.search(offset=100)['parts'] == []
    assert 'unit_price' not in catalog.search()['parts'][0]


def test_normalized_pairs_share_quantity_limits():
    catalog = PartsCatalog.from_csv("part_id,color_id,max_quantity\n3001,4,2\n")
    with pytest.raises(PartsUnavailable):
        catalog.validate({("3001", 4): 2, ("3001.dat", 4): 1})


@pytest.mark.parametrize('bad', ['../3001', '/3001', 's/3001', '3001.ldr', '3001;rm'])
def test_unsafe_identifiers_are_rejected(bad):
    with pytest.raises(ValueError):
        normalize_part_id(bad)


def test_ambiguous_pairs_and_empty_palette_fail_closed():
    with pytest.raises(ValueError, match='Ambiguous'):
        PartsCatalog.from_csv(CATALOG + '3001,4,Duplicate,\n')
    with pytest.raises(ValueError, match='no mapped'):
        PartsCatalog.from_csv(CATALOG.splitlines()[0] + '\n')


def test_round_trip_discards_external_metadata_and_preserves_quantities():
    external = 'part_id,color_id,name,max_quantity,unit_price,weight_kg,external_field\n3001,4,Brick,5,0.25,0.01,other\n'
    palette = PartsCatalog.from_csv(external)
    exported = palette.to_csv()
    assert 'unit_price' not in exported and 'weight_kg' not in exported and 'external_field' not in exported
    assert PartsCatalog.from_csv(exported).parts == palette.parts


def test_utf8_bom_does_not_hide_headers():
    catalog = PartsCatalog.from_csv('\ufeffpart_id,color_id,name\n3001,4,Brick\n')
    assert catalog.search()['parts'][0]['name'] == 'Brick'
