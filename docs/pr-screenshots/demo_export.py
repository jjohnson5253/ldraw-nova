from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from ldraw_tools.external import prepare_glb
with TemporaryDirectory() as temp:
    root = Path(temp)
    source = root / 'source.mpd'
    source.write_text('0 Demo model\n')
    destination = root / 'model.glb'
    previous = b'previous export fixture'
    destination.write_bytes(previous)
    def converter(command, **kwargs):
        Path(command[command.index('-o') + 1]).write_bytes(b'')
        return subprocess.CompletedProcess(command, 0, '', '')
    print('Converter exit status: 0 (simulated)')
    print('Converter output:      0 bytes')
    print(f'Destination before:    {len(previous)} bytes')
    with patch('ldraw_tools.external.subprocess.run', converter):
        try:
            prepare_glb(source, root, destination, SimpleNamespace(by_code={'3001': 'Brick 2 x 4'}))
            print('Result:                ACCEPTED')
        except ValueError as error:
            print('Result:                REJECTED')
            print(f'Error:                 {str(error).strip()}')
    print(f'Destination after:     {destination.stat().st_size} bytes')
    print('Previous file intact:  ' + ('YES' if destination.read_bytes() == previous else 'NO'))
