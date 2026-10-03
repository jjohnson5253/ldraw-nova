"""External tools must produce nonempty artifacts before publishing them."""
from pathlib import Path
import subprocess

import pytest

from conftest import mpd, ref
from ldraw_tools.external import prepare_glb, render, render_steps


@pytest.mark.parametrize('payload', [b'', None, b'converted model'])
def test_glb_export_requires_nonempty_output(parts, tmp_path, monkeypatch, payload):
    source = tmp_path / 'source.mpd'
    source.write_text(mpd(ref()))
    output = tmp_path / 'model.glb'
    output.write_bytes(b'previous export')

    def convert(command, **kwargs):
        if payload is not None:
            Path(command[command.index('-o') + 1]).write_bytes(payload)
        return subprocess.CompletedProcess(command, 0, '', '')

    monkeypatch.setattr('ldraw_tools.external.subprocess.run', convert)
    if payload:
        prepare_glb(source, parts.path.parent, output, parts)
        assert output.read_bytes() == payload
    else:
        with pytest.raises(ValueError, match='GLB conversion failed'):
            prepare_glb(source, parts.path.parent, output, parts)
        assert output.read_bytes() == b'previous export'


@pytest.mark.parametrize('empty_artifact', ['image', 'bom'])
def test_render_rejects_empty_artifacts(parts, tmp_path, monkeypatch, empty_artifact):
    source = tmp_path / 'source.mpd'
    source.write_text(mpd(ref()))
    outdir = tmp_path / 'renders'
    outdir.mkdir()
    image, bom = outdir / 'home.png', outdir / 'leocad-bom.csv'
    image.write_bytes(b'previous image')
    bom.write_bytes(b'previous BOM')

    def render_output(command, **kwargs):
        kind, flag = ('image', '-i') if '-i' in command else ('bom', '-csv')
        Path(command[command.index(flag) + 1]).write_bytes(b'' if kind == empty_artifact else b'fresh artifact')
        return subprocess.CompletedProcess(command, 0, '', '')

    monkeypatch.setattr('ldraw_tools.external.subprocess.run', render_output)
    with pytest.raises(ValueError, match='LeoCAD .* failed'):
        render(source, parts.path.parent, outdir, views=('home',))
    assert (image if empty_artifact == 'image' else bom).read_bytes() == (
        b'previous image' if empty_artifact == 'image' else b'previous BOM')


@pytest.mark.parametrize('numbered', [False, True])
def test_step_render_rejects_empty_images(parts, tmp_path, monkeypatch, numbered):
    source = tmp_path / 'source.mpd'
    source.write_text(mpd(ref()))
    outdir = tmp_path / 'steps'
    outdir.mkdir()
    output = outdir / 'step-001-home.png'
    output.write_bytes(b'previous step')

    def render_output(command, **kwargs):
        target = Path(command[command.index('-i') + 1])
        if numbered:
            target = target.with_name(target.stem + '1.png')
        target.write_bytes(b'')
        return subprocess.CompletedProcess(command, 0, '', '')

    monkeypatch.setattr('ldraw_tools.external.subprocess.run', render_output)
    with pytest.raises(ValueError, match='LeoCAD did not render every requested home step'):
        render_steps(source, parts.path.parent, outdir, steps=[1], views=('home',))
    assert output.read_bytes() == b'previous step'
