#!/usr/bin/env python3
"""Compile patched d8 or Chromium, with bounded parallelism and retained logs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time


def command(workspace, output, jobs, target="d8"):
    return [str(workspace / 'with-tools.sh'), '/usr/bin/ninja', '-C', str(output), '-j', str(jobs), '-k', '1', target]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('gn_report', type=Path)
    parser.add_argument('--target', choices=('d8', 'chrome'), default='d8')
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('--adaptation-report', type=Path, help='Record and verify the separately applied d8 shutdown adaptation')
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
    adaptation = None
    if args.adaptation_report:
        applied = json.loads(args.adaptation_report.read_text())
        if applied.get('status') != 'd8_shutdown_adaptation_applied_rebuild_required' or applied.get('adaptation_patch_sha256') != '52b887813a9351dca6e606e6732686f4ca8f7ef775a25b920f2ffea3e53d9da4':
            raise SystemExit('Expected separately applied shutdown adaptation report')
        saved_diff = (args.adaptation_report.parent / 'd8.diff').read_text().strip()
        current_diff = subprocess.check_output(['git', '-c', 'core.fsmonitor=false', '-C', str(root / 'src/v8'), 'diff', '--', 'src/d8.cc'], text=True, timeout=30).strip()
        if not saved_diff or current_diff != saved_diff:
            raise SystemExit('d8 source differs from recorded adaptation; inspect before building')
        adaptation = {'report': str(args.adaptation_report.resolve()),
                      'patch_sha256': applied['adaptation_patch_sha256'],
                      'd8_diff_sha256': hashlib.sha256(current_diff.encode()).hexdigest()}
    logs = Path(tempfile.mkdtemp(prefix=args.target + '-build-', dir=root))
    env = dict(os.environ, CCACHE_DIR=str(root / 'ccache-d8'), CCACHE_MAXSIZE='10G', CCACHE_BASEDIR=str(root / 'src'))
    cmd = command(root, output, args.jobs, args.target)
    result = {'status': 'incomplete', 'command': cmd, 'log': str(logs / 'build.log'),
              'target': args.target, 'chrome_compilation': 'requested' if args.target == 'chrome' else 'not run', 'runtime_validation': 'not run',
              'ccache_directory': env['CCACHE_DIR']}
    result['shutdown_adaptation'] = adaptation
    print('Command:', json.dumps(cmd), flush=True)
    print('Log:', logs / 'build.log', flush=True)
    started = time.monotonic()
    with (logs / 'build.log').open('w+') as log:
        process = None
        try:
            process = subprocess.Popen(cmd, cwd=root / 'src', env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            result['exit_code'] = process.wait(timeout=args.timeout)
            result['status'] = args.target + ('_build_passed' if process.returncode == 0 else '_build_failed')
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            result['status'] = args.target + '_build_timeout_or_interrupted'
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
    result['binary_exists'] = (output / args.target).is_file()
    if result['status'] == args.target + '_build_passed' and result['binary_exists']:
        digest = hashlib.sha256()
        with (output / args.target).open('rb') as binary:
            for chunk in iter(lambda: binary.read(1024 * 1024), b''):
                digest.update(chunk)
        result['binary_sha256'] = digest.hexdigest()
    (logs / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', logs / 'result.json')
    return 0 if result['status'] == args.target + '_build_passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
