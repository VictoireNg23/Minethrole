#!/usr/bin/env python3
"""Bounded gclient --help test in the isolated historical tools snapshot.

May bootstrap historical CIPD/vpython tools. Never runs sync, hooks or a build.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile

REVISION = 'c6a8d114b060f5f68637e8897712a24252402377'


def check(root, timeout):
    provenance = json.loads((root / 'provenance.json').read_text())
    if provenance['revision'] != REVISION:
        raise ValueError('Unexpected depot_tools revision; stopping')
    if os.environ.get('VPYTHON_BYPASS'):
        raise ValueError('VPYTHON_BYPASS is set; remove it for this validated-runtime test')
    launcher = root / 'with-env.sh'
    gclient = root / 'depot_tools/gclient'
    if not os.access(launcher, os.X_OK) or not os.access(gclient, os.X_OK):
        raise ValueError('Missing executable launcher or historical gclient')
    logs = Path(tempfile.mkdtemp(prefix='gclient-help-check-', dir=root))
    print('New diagnostic directory:', logs, flush=True)
    command = [str(launcher), str(gclient), '--help']
    status = 'failed'
    with (logs / 'stdout.log').open('xb') as stdout, (logs / 'stderr.log').open('xb') as stderr:
        process = subprocess.Popen(command, cwd=logs, stdout=stdout, stderr=stderr,
                                   stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            status = 'timeout'
            # Terminate only the new process group created for this test.
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            code = process.returncode
    if status != 'timeout' and code == 0:
        # Zero exit without actual help text is not enough to validate startup.
        output = (logs / 'stdout.log').read_text(errors='replace') + (logs / 'stderr.log').read_text(errors='replace')
        if 'gclient' in output.lower() and ('usage' in output.lower() or 'commands' in output.lower()):
            status = 'help_completed'
        else:
            status = 'help_output_not_recognized'
    result = {'revision': REVISION, 'command': command, 'cwd': str(logs),
              'status': status, 'underlying_exit_code': code,
              'timeout_seconds': timeout, 'chromium_sync': 'not run',
              'hooks': 'not run', 'build': 'not run'}
    (logs / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    for name in ('stdout.log', 'stderr.log'):
        text = (logs / name).read_text(errors='replace')
        print('\n=== ' + name + ' ===', flush=True)
        if len(text) > 20000:
            print('[displaying last 20000 characters; complete log retained]')
        print(text[-20000:])
    print(json.dumps(result, indent=2), flush=True)
    print('Help startup only. Dependency synchronization and runtime compatibility remain unvalidated.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('isolated_tools_root', type=Path)
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error('--timeout must be positive')
    result = check(args.isolated_tools_root.resolve(strict=True), args.timeout)
    return 0 if result['status'] == 'help_completed' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('FAILED / INCOMPLETE:', error, flush=True)
        raise SystemExit(1)
