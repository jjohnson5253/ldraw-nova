"""CLI catalogs can be browsed before installing a parts library."""
import json
import sys

import pytest

from ldraw_tools import cli
from ldraw_tools.examples import search_examples
from ldraw_tools.technic_recipes import RECIPES
from ldraw_tools.vehicles import DESIGNS


@pytest.mark.parametrize('command,expected', [
    (['vehicle', 'list'], DESIGNS),
    (['technic', 'list'], RECIPES),
    (['mechanism', 'list'], search_examples(family='mechanism', limit=100)),
    (['spaceship', 'list'], search_examples(family='spaceship', limit=100)),
    (['spaceship', 'details'], search_examples(family='spaceship', details=True, limit=100)),
])
def test_bundled_catalog_does_not_resolve_library(monkeypatch, capsys, command, expected):
    def unavailable_library(*args, **kwargs):
        raise ValueError('Parts library unavailable')

    monkeypatch.setattr(cli, 'library_path', unavailable_library)
    monkeypatch.setattr(sys, 'argv', ['ldraw-agent', *command])
    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out) == expected


def test_part_inspection_still_requires_library(monkeypatch, capsys):
    monkeypatch.delenv('LDRAW_DIR', raising=False)
    monkeypatch.delenv('LDRAWDIR', raising=False)
    monkeypatch.setattr(sys, 'argv', ['ldraw-agent', 'part', '3001.dat'])
    assert cli.main() == 2
    report = json.loads(capsys.readouterr().out)
    assert report['checks_passed'] is False
    assert 'Set LDRAW_DIR' in report['error']
