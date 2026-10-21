#!/usr/bin/env python3
"""Compile patched V8/d8 only, with bounded parallelism and retained logs."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time


def command(workspace, output, jobs):
    return [str(workspace / 'with-tools.sh'), '/usr/bin/ninja', '-C', str(output), '-j', str(jobs), '-k', '1', 'd8']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('gn_report', type=Path)
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument('--timeout', type=int, default=900)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 32 or args.timeout < 1:
        raise SystemExit('Require jobs in 1..32 and a positive timeout')
    root = args.workspace.resolve()
    report = json.loads(args.gn_report.read_text())
    if report.get('status') != 'gn_generation_passed_patched' or report.get('exit_code') != 0:
        raise SystemExit('Successful patched GN report required')
    output = Path(report['output_directory']).resolve()
    if not (root / 'preparation.json').is_file() or output.parent != root / 'src/out' or not (output / 'build.ninja').is_file():
        raise SystemExit('Unexpected workspace or generated output directory')
    st = os.statvfs(output)
    if st.f_bavail * st.f_frsize < 30 * 1024 ** 3:
        raise SystemExit('Less than 30 GiB free; inspect available space before building')
    logs = Path(tempfile.mkdtemp(prefix='d8-build-', dir=root))
    env = dict(os.environ, CCACHE_DIR=str(root / 'ccache-d8'), CCACHE_MAXSIZE='10G', CCACHE_BASEDIR=str(root / 'src'))
    cmd = command(root, output, args.jobs)
    result = {'status': 'incomplete', 'command': cmd, 'log': str(logs / 'build.log'),
              'target': 'd8', 'chrome_compilation': 'not run', 'runtime_validation': 'not run',
              'ccache_directory': env['CCACHE_DIR']}
    print('Command:', json.dumps(cmd), flush=True)
    print('Log:', logs / 'build.log', flush=True)
    started = time.monotonic()
    with (logs / 'build.log').open('w+') as log:
        process = None
        try:
            process = subprocess.Popen(cmd, cwd=root / 'src', env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            result['exit_code'] = process.wait(timeout=args.timeout)
            result['status'] = 'd8_build_passed' if process.returncode == 0 else 'd8_build_failed'
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            result['status'] = 'd8_build_timeout_or_interrupted'
            if process is not None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                result['exit_code'] = process.returncode
        except OSError as error:
            result['error'] = str(error)
        result['elapsed_seconds'] = round(time.monotonic() - started, 2)
        log.seek(0)
        print(log.read()[-24000:], flush=True)
    result['binary_exists'] = (output / 'd8').is_file()
    (logs / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', logs / 'result.json')
    return 0 if result['status'] == 'd8_build_passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
