import json

import pytest
from ldraw import Model, Piece, Vector

from ldraw_tools.builder import rotation
from ldraw_tools.common import get_parts
from ldraw_tools.connectivity import inspect_connections, snap_report, apply_snap
from ldraw_tools.connection_adapter import connection_contacts
from ldraw_tools.technic import registry, definition, managed
from ldraw_tools.technic_review import review_structure


def model(*placements):
    return Model.from_pieces([Piece.place(code, colour=4, position=Vector(*at), matrix=matrix)
                             for code, at, matrix in placements], name='structure.ldr')


I = rotation()
PIN_Y = rotation('z', 90)
AXLE_Z = rotation('y', -90)


def errors(report):
    return {d['code'] for d in report['diagnostics'] if d['severity'] == 'error'}


def test_registry_matches_geometry_and_removes_phantom_holes(official):
    assert all(definition(official.geometry(c)) for c in registry()['parts'])
    m = model(('32523', (0, 0, 0), I))
    inspection = inspect_connections(m, official)
    assert len(inspection.occurrences[0].connections) == 3
    assert all(managed(f) for f in inspection.occurrences[0].connections)
    assert definition(official.geometry('32064'))
    assert definition(official.geometry('4265c'))


@pytest.mark.parametrize('y', [0, 30])
def test_collar_in_bore_and_tip_touch_are_not_connections(official, y):
    m = model(('32523', (0, 0, 0), I), ('2780', (0, y, 0), PIN_Y))
    assert not connection_contacts(inspect_connections(m, official))
    assert 'technic.invalid_seating' in errors(review_structure(m, official))


def test_pin_snap_seats_a_grip_and_reports_friction(official):
    m = model(('32523', (0, 0, 0), I), ('2780', (100, 0, 0), I))
    snap = snap_report(m, official, 1, 0, limit=1)
    candidate = snap['candidates'][0]
    assert abs(candidate['local_placement']['at'][1]) == 10
    fitted = apply_snap(m, snap)
    report = review_structure(fitted, official)
    assert report['joint_count'] == 1 and report['joints'][0]['friction'] is True
    assert not errors(report)


def test_cross_axle_bearing_keyed_roll_and_wrong_family(official):
    bearing = model(('3700', (0, 0, 0), I), ('3705', (0, 10, 0), AXLE_Z))
    report = review_structure(bearing, official)
    assert report['joints'][0]['behavior'] == 'bearing'
    assert 'technic.bearing_rotation' in {d['code'] for d in report['diagnostics']}
    keyed = model(('32064a', (0, 0, 0), I), ('3705', (0, 10, 0), AXLE_Z))
    assert review_structure(keyed, official)['joints'][0]['behavior'] == 'keyed'
    rolled = model(('32064a', (0, 0, 0), I), ('3705', (0, 10, 0), AXLE_Z*rotation('x', 45)))
    assert 'technic.invalid_seating' in errors(review_structure(rolled, official))
    wrong = model(('32064a', (0, 0, 0), I), ('2780', (0, 10, 10), AXLE_Z))
    assert not review_structure(wrong, official)['joints']


def test_mixed_connector_ports(official):
    m = model(('3700', (0, 0, 0), I), ('43093', (0, 10, 10), AXLE_Z),
              ('32064a', (0, 0, 20), I))
    report = review_structure(m, official)
    assert {j['behavior'] for j in report['joints']} == {'pin', 'keyed'}
    assert not errors(report)


def test_thin_layers_fill_one_grip(official):
    # Thin beam holes have odd half-module Z offsets.
    thin = ('32063', (0, 5, 10), I)
    m = model(thin, ('2780', (0, 10, 0), PIN_Y))
    assert 'technic.incomplete_grip' in errors(review_structure(m, official))
    filled = model(thin, ('32063', (0, -5, 10), I), ('2780', (0, 10, 0), PIN_Y))
    assert not errors(review_structure(filled, official))


def test_occupied_spans_and_holes(official):
    m = model(('32523', (0, 0, 0), I), ('32523', (0, 0, 0), I), ('2780', (0, 10, 0), PIN_Y))
    assert 'technic.occupied_span' in errors(review_structure(m, official))
    doubled = model(('32523', (0, 0, 0), I), ('2780', (0, 10, 0), PIN_Y), ('2780', (0, 10, 0), PIN_Y))
    assert 'technic.occupied_hole' in errors(review_structure(doubled, official))


def test_axle_accepts_disjoint_bushes_and_requires_retention(official):
    m = model(('32064a', (0, 0, 0), I), ('3705', (0, 10, 0), AXLE_Z),
              ('3713', (0, 10, -20), I), ('3713', (0, 10, 20), I))
    report = review_structure(m, official)
    assert report['joint_count'] == 3
    assert 'technic.axial_retention' not in {d['code'] for d in report['diagnostics']}
    assert not errors(report)
    pending = model(('32064a', (0, 0, 0), I), ('3705', (0, 10, 0), AXLE_Z),
                    ('3713', (0, 10, -20), I), ('3713', (100, 10, 20), I))
    snap = snap_report(pending, official, 3, 1, limit=20)
    assert any(c['collision']['status'] != 'blocked' and c['local_placement']['at'][2] >= 20
               for c in snap['candidates'])


def test_connected_pivot_is_not_a_restrained_frame(official):
    placements = [('32523', (0, 0, 0), I), ('32523', (0, 20, 0), I), ('3673', (0, 10, 0), PIN_Y)]
    report = review_structure(model(*placements), official, contract={'version': 1, 'require_rigid': True})
    assert 'technic.structural_restraint' in errors(report)
    restrained = review_structure(model(*placements, ('2780', (0, 10, 20), PIN_Y)), official,
                                   contract={'version': 1, 'require_rigid': True})
    assert not errors(restrained) and len(restrained['restrained_groups']) == 1


def test_required_second_mount_and_contract_indices(official):
    m = model(('32523', (0, 0, 0), I), ('32523', (0, 20, 0), I), ('2780', (0, 10, 0), PIN_Y),
              ('2780', (0, 10, 40), PIN_Y))
    c = {'version': 1, 'required_joints': [{'between': [3, 1]}]}
    assert 'technic.missing_required_joint' in errors(review_structure(m, official, contract=c))
    with pytest.raises(ValueError, match='absent'):
        review_structure(m, official, contract={'version': 1, 'required_joints': [{'between': [0, 100]}]})
    with pytest.raises(ValueError, match='revision'):
        review_structure(m, official, contract={'version': 1, 'model_sha256': '0'*64})


def test_assembly_order_and_geometry_revision_are_explicit(official):
    from dataclasses import replace
    from ldraw_tools.builder import build_plan
    plan = dict(version=1, author='Tests', sections=[dict(name='main.ldr', description='Pin insertion order', steps=[
        [dict(id='beam', ref='32523.dat', colour=4, at=[0, 0, 0])],
        [dict(id='pin', ref='2780.dat', colour=0, at=[0, 10, 0], matrix=PIN_Y.rows)],
        [dict(id='second', ref='32523.dat', colour=4, at=[0, 20, 0])],
    ])])
    _, m, ds = build_plan(plan, official)
    contract = {'version': 1, 'assembly': [{'connector': 1, 'before': [2]}]}
    assert not errors(review_structure(m, official, contract=contract))
    contract['assembly'][0]['before'] = [0]
    assert 'technic.insertion_order' in errors(review_structure(m, official, contract=contract))
    g = official.geometry('32523')
    assert definition(replace(g, points=(*g.points, Vector(100, 0, 0)))) is None


@pytest.mark.parametrize('name,levels', [('reinforced-frame', 2), ('box-chassis', 2),
                                      ('frame-tower', 1), ('frame-tower', 3), ('service-platform', 2)])
def test_structural_recipes_meet_declared_mounts_and_geometry(official, name, levels):
    from ldraw_tools.technic_recipes import structure_plan
    from ldraw_tools.builder import build_plan
    from ldraw_tools.geometry import analyze_geometry
    plan, contract = structure_plan(name, levels=levels)
    _, m, diagnostics = build_plan(plan, official)
    assert not [d for d in diagnostics if d['severity']=='error']
    report = review_structure(m, official, contract=contract)
    assert report['checks_passed'] and len(report['restrained_groups']) == 1
    assert not [d for d in analyze_geometry(m, official)['diagnostics'] if d['severity']=='error']


def test_structural_discovery_uses_selected_content_not_parent_theme():
    from ldraw_tools.discovery import structural_candidate
    row = dict(kind='submodels', description='A static chassis frame', theme='Technic',
               parent_description='Working gearbox and engine mechanism')
    assert structural_candidate(row, {'bom': [{'description': 'Technic Beam 5'}]})
    assert not structural_candidate(row, {'bom': [{'description': 'Technic Gear 16 Tooth'}]})
    assert not structural_candidate(dict(row, description='Motor and gearbox'))
    assert structural_candidate({'kind': 'parts', 'part': '2780.dat'})
    assert not structural_candidate({'kind': 'parts', 'part': '3648.dat'})


@pytest.mark.parametrize('gear', ['32270', '32498', '3648', '4716'])
def test_caddy_gear_hub_requires_a_seated_axle(official, gear):
    mounted = model((gear, (0, 0, 0), I), ('44294', (0, 0, 0), AXLE_Z))
    assert connection_contacts(inspect_connections(mounted, official))
    offset = model((gear, (0, 0, 0), I), ('44294', (10, 0, 0), AXLE_Z))
    assert not connection_contacts(inspect_connections(offset, official))


def test_caddy_gear_mesh_does_not_mount_either_gear(official):
    gears = model(('32498', (0, 0, 0), I), ('32270', (0, 60, 0), I))
    assert not connection_contacts(inspect_connections(gears, official))


def test_caddy_post_pin_and_lid_hinge_axle(official):
    post = model(('40490', (0, 0, 0), I), ('3673', (0, 10, 0), PIN_Y))
    assert connection_contacts(inspect_connections(post, official))
    hinge = model(('32449', (0, 0, 0), I), ('50451', (0, 0, -30), PIN_Y))
    assert connection_contacts(inspect_connections(hinge, official))
    missed = model(('32449', (0, 0, 0), I), ('50451', (1, 0, -30), PIN_Y))
    assert not connection_contacts(inspect_connections(missed, official))


def test_saved_card_caddy_only_leaves_the_omitted_motor_drive_disconnected(official):
    from pathlib import Path
    from ldraw_tools.document import parse_source
    source = Path(__file__).parent / 'fixtures/technic-card-caddy.mpd'
    inspection = inspect_connections(parse_source(source), official)
    neighbors = {o.index: set() for o in inspection.occurrences}
    for contact in connection_contacts(inspection):
        a, b = contact.first_occurrence.index, contact.second_occurrence.index
        neighbors[a].add(b)
        neighbors[b].add(a)
    reached, pending = set(), [0]
    while pending:
        current = pending.pop()
        if current not in reached:
            reached.add(current)
            pending.extend(neighbors[current] - reached)
    assert set(neighbors) - reached == {232, 233}


def test_geometry_fingerprint_ignores_point_order_and_submicroscopic_roundoff(official):
    from dataclasses import replace
    local = official.geometry('32449')
    points = tuple(Vector(p.x + 1e-9, p.y, p.z) for p in reversed(local.points))
    assert definition(replace(local, points=points)) is not None
    changed = (Vector(points[0].x + .01, points[0].y, points[0].z), *points[1:])
    assert definition(replace(local, points=changed)) is None


def test_sprocket_fingerprint_accepts_roundoff_at_half_micro_ldu(official):
    from dataclasses import replace
    local = official.geometry('57519')
    points = tuple(Vector(p.x + 1e-13, p.y - 1e-13, p.z) for p in reversed(local.points))
    assert definition(replace(local, points=points)) is not None


@pytest.mark.parametrize('part,x,y', [('57519', 0, 0), ('3703', 120, 10), ('3895', 100, 10)])
def test_excavator_axle_must_cross_an_actual_bore(official, part, x, y):
    def seated(dx, dz):
        assembly = model((part, (0, 0, 0), I), ('44294', (x + dx, y, dz), AXLE_Z))
        return connection_contacts(inspect_connections(assembly, official))
    assert seated(0, 0)
    assert not seated(8, 0)
    assert not seated(0, 80)


def test_excavator_pin_grips_and_stopped_drive_axle(official):
    def joined(first, second):
        return connection_contacts(inspect_connections(model(first, second), official))
    pin = ('4459', (0, 0, 0), I)
    assert joined(pin, ('32523', (10, 0, 0), rotation('z', 90)))
    assert not joined(pin, ('32523', (25, 0, 0), rotation('z', 90)))
    shaft = ('32209', (0, 0, 0), I)
    assert joined(shaft, ('32270', (43, 0, 0), AXLE_Z))
    assert not joined(shaft, ('32270', (-32, 0, 0), AXLE_Z))


def test_seated_grip_can_end_flush_with_another_bore_without_joining_it(official):
    def stack(last_x):
        return model(('4459', (0, 0, 0), I),
                     ('32523', (10, 0, 0), rotation('z', 90)),
                     ('32523', (last_x, 0, 0), rotation('z', 90)))
    flush = stack(30)
    assert 'technic.invalid_seating' not in errors(review_structure(flush, official))
    assert not any(2 in (c.first_occurrence.index, c.second_occurrence.index)
                   and 0 in (c.first_occurrence.index, c.second_occurrence.index)
                   for c in connection_contacts(inspect_connections(flush, official)))
    assert 'technic.invalid_seating' in errors(review_structure(stack(29), official))


def test_bent_liftarm_distinguishes_keyed_ends_from_round_middle(official):
    beam = ('6629', (0, 0, 0), I)
    def seated(second):
        return connection_contacts(inspect_connections(model(beam, second), official))
    assert seated(('4459', (0, 10, 20), PIN_Y))
    assert not seated(('4459', (0, 10, 0), PIN_Y))
    assert not seated(('44294', (48, 0, 136), PIN_Y))
    assert seated(('44294', (48, 0, 136), rotation('y', -53.13010235415598) * PIN_Y))


@pytest.mark.parametrize('part,x,z', [('15458', -80, 20), ('32526', 20, 80)])
def test_boom_pin_seats_in_measured_panel_or_elbow_bore(official, part, x, z):
    def seated(dx):
        return connection_contacts(inspect_connections(
            model((part, (0, 0, 0), I), ('4459', (x + dx, 10, z), PIN_Y)), official))
    assert seated(0)
    assert not seated(8)


def test_partial_axle_reports_span_needed_to_seat_both_bore_faces(official):
    assembly = model(('3707', (0, 0, 0), I),
                     ('32523', (80, 0, 0), rotation('z', 90)))
    issues = review_structure(assembly, official)['diagnostics']
    [error] = [d for d in issues if d['code'] == 'technic.invalid_seating']
    [span] = error['short_shafts_ldu']
    assert span['engagement'] == 10 and span['shaft_length'] == 160
    assert span['minimum_centered_span'] == 180 and span['bore_length'] == 20
