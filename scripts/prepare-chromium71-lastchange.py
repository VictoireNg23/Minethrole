#!/usr/bin/env python3
"""Run the original lastchange generator in staging; install only absent outputs."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def command(workspace, output):
    src = workspace / 'src'
    return [str(workspace / 'with-tools.sh'), 'python', str(src / 'build/util/lastchange.py'),
            '-s', str(src), '-o', str(output)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    if not (root / 'preparation.json').is_file():
        raise SystemExit('Expected isolated prepared workspace')
    destination = root / 'src/build/util'
    names = ('LASTCHANGE', 'LASTCHANGE.committime')
    for name in names:
        path = destination / name
        if path.exists() or path.is_symlink():
            raise SystemExit('Refused occupied destination: ' + str(path))
    stage = Path(tempfile.mkdtemp(prefix='lastchange-stage-', dir=root))
    result = {'status': 'incomplete', 'directory': str(stage), 'hooks_global': 'not run', 'build': 'not run'}
    cmd = command(root, stage / 'LASTCHANGE')
    print('Command:', json.dumps(cmd), flush=True)
    try:
        process = subprocess.run(cmd, cwd=root / 'src', stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, timeout=60)
        (stage / 'generator.log').write_text(process.stdout)
        print(process.stdout, flush=True)
        result['exit_code'] = process.returncode
        if process.returncode:
            raise RuntimeError('Original generator failed; no output installed')
        for name in names:
            if not (stage / name).is_file() or (stage / name).is_symlink():
                raise RuntimeError('Generator did not produce expected file: ' + name)
        int((stage / 'LASTCHANGE.committime').read_text().strip())
        result['values'] = {name: (stage / name).read_text() for name in names}
        for name in names:
            with (destination / name).open('xb') as output:
                output.write((stage / name).read_bytes())
        result['status'] = 'original_lastchange_outputs_prepared'
    except Exception as error:
        result['error'] = str(error)
    (stage / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', stage / 'result.json')
    return 0 if result['status'] == 'original_lastchange_outputs_prepared' else 1


if __name__ == '__main__':
    raise SystemExit(main())
