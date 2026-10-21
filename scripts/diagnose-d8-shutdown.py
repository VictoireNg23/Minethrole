#!/usr/bin/env python3
"""Repeat benign d8 cases; retain crashes and optionally obtain a GDB backtrace."""
import argparse
import json
from pathlib import Path
import resource
import shutil
import subprocess
import tempfile


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('build_report', type=Path)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('--gdb-only', action='store_true', help='Skip repeated direct runs and collect only GDB diagnostics')
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    build = json.loads(args.build_report.read_text())
    if build.get('status') != 'd8_build_passed':
        raise SystemExit('Successful d8 build required')
    command = build['command']
    output = Path(command[command.index('-C') + 1]).resolve()
    if output.parent != workspace / 'src/out' or not (workspace / 'preparation.json').is_file():
        raise SystemExit('Unexpected workspace/output')
    binary = output / 'd8'
    fixture = args.fixture.resolve()
    root = Path(tempfile.mkdtemp(prefix='d8-shutdown-diagnostic-', dir=workspace))
    print('Diagnostic directory:', root, flush=True)
    result = {'cases': [], 'gdb': shutil.which('gdb'), 'patch_changes': 'none', 'defense_validation': 'not performed'}
    for mode in (() if args.gdb_only else ('dormant', 'negative', 'active')):
        for repeat in range(3):
            cwd = root / ('%s-%d' % (mode, repeat))
            cwd.mkdir()
            item = {'mode': mode, 'repeat': repeat}
            try:
                process = subprocess.run([str(binary), str(fixture), '--', mode], cwd=cwd,
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                         timeout=10, preexec_fn=no_core)
                (cwd / 'stdout.log').write_text(process.stdout)
                item.update(exit_code=process.returncode,
                            marker='SMOKE_OK ' + mode in process.stdout,
                            signal=-process.returncode if process.returncode < 0 else None,
                            count_files=[str(p) for p in cwd.glob('*.count')])
            except subprocess.TimeoutExpired:
                item['status'] = 'timeout'
            result['cases'].append(item)
            print(json.dumps(item), flush=True)
    if result['gdb']:
        cwd = root / 'gdb-dormant'
        cwd.mkdir()
        gdb_command = [result['gdb'], '-nx', '-nh', '--batch',
                       '-ex', 'set pagination off', '-ex', 'set confirm off',
                       '-ex', 'handle SIGALRM nostop noprint pass',
                       '-ex', 'run', '-ex', 'thread apply all bt 25', '-ex', 'info symbol $pc', '-ex', 'x/i $pc',
                       '--args', str(binary), str(fixture), '--', 'dormant']
        try:
            process = subprocess.run(gdb_command, cwd=cwd, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, timeout=30, preexec_fn=no_core)
            (cwd / 'gdb.log').write_text(process.stdout)
            result['gdb_exit_code'] = process.returncode
            result['gdb_log'] = str(cwd / 'gdb.log')
            print('\n=== GDB output (last 16000 characters) ===\n' + process.stdout[-16000:])
        except subprocess.TimeoutExpired:
            result['gdb_status'] = 'timeout'
    else:
        print('GDB absent: not installed by this diagnostic.')
    (root / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Report:', root / 'result.json')
    print('This is a diagnostic, not a passing validation; retain the original failed report.')


if __name__ == '__main__':
    main()
