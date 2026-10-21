#!/usr/bin/env python3
"""Run only the benign counter fixture; compare original .count output to expectations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def parse_counters(text):
    rows = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) == 22:  # pid tid module reserved sec nsec, four flags, twelve counters
            rows.append([int(value) for value in fields[10:]])
    return rows


def binary_digest(path):
    digest = hashlib.sha256()
    with path.open('rb') as binary:
        for chunk in iter(lambda: binary.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def case_passed(exit_code, marker, measured, expected):
    return exit_code == 0 and marker and measured == expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('build_report', type=Path)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('--all-signatures', action='store_true')
    parser.add_argument('--previous-smoke-report', type=Path)
    parser.add_argument('--repeat', type=int, default=1, help='Repeat every case in an independent process')
    args = parser.parse_args()
    if not 1 <= args.repeat <= 100:
        raise SystemExit('Require repeat in 1..100')
    if args.all_signatures:
        if args.previous_smoke_report is None or json.loads(args.previous_smoke_report.read_text()).get('status') != 'counter_smoke_passed':
            raise SystemExit('Full previous smoke report must confirm all cases passed')
    root = args.workspace.resolve()
    build = json.loads(args.build_report.read_text())
    if build.get('status') != 'd8_build_passed' or build.get('exit_code') != 0:
        raise SystemExit('Successful d8 build required')
    # Recover the exact output from the recorded Ninja -C argument.
    output = Path(build['command'][build['command'].index('-C') + 1]).resolve()
    if output.parent != root / 'src/out' or not (root / 'preparation.json').is_file():
        raise SystemExit('Unexpected output path')
    digest = binary_digest(output / 'd8')
    if build.get('binary_sha256') and digest != build['binary_sha256']:
        raise SystemExit('d8 differs from the supplied build report')
    fixture = args.fixture.resolve()
    run = Path(tempfile.mkdtemp(prefix='counter-smoke-', dir=root))
    result = {'status': 'incomplete', 'cases': [], 'dataset_execution': 'not run', 'defense_validation': 'not performed'}
    modes = [kind + str(i) for i in range(12) for kind in ('dormant', 'active')] if args.all_signatures else ['dormant', 'negative', 'active']
    result.update(binary_sha256=digest, build_report=str(args.build_report.resolve()),
                  shutdown_adaptation=build.get('shutdown_adaptation'), repeats=args.repeat)
    for mode, repeat in [(mode, repeat) for mode in modes for repeat in range(args.repeat)]:
        cwd = run / (mode + '-' + str(repeat))
        cwd.mkdir()
        item = {'mode': mode, 'repeat': repeat, 'status': 'incomplete'}
        try:
            # Do not use with-tools.sh: it changes cwd and would mix output files.
            process = subprocess.run([str(output / 'd8'), str(fixture), '--', mode], cwd=cwd,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=10)
            (cwd / 'stdout.log').write_text(process.stdout)
            item.update(exit_code=process.returncode, stdout=process.stdout[-4000:])
            rows = []
            for path in cwd.glob('*.count'):
                rows.extend(parse_counters(path.read_text()))
            item['sample_rows'] = len(rows)
            item['counter_maxima'] = [max(row[i] for row in rows) for i in range(12)] if rows else None
            expected = [0] * 12
            if mode.startswith('active'):
                index = int(mode[6:]) if args.all_signatures else 0
                expected[index] = 20000
            item['expected'] = expected
            item['status'] = 'passed' if case_passed(process.returncode, 'SMOKE_OK ' + mode in process.stdout, item['counter_maxima'], expected) else 'failed_or_unmeasurable'
        except Exception as error:
            item['error'] = str(error)
        result['cases'].append(item)
    result['status'] = 'counter_smoke_passed' if all(i['status'] == 'passed' for i in result['cases']) else 'counter_smoke_failed_or_incomplete'
    if binary_digest(output / 'd8') != digest:
        result['status'] = 'counter_smoke_failed_or_incomplete'
        result['error'] = 'Binary changed during test run'
    (run / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', run / 'result.json')
    return 0 if result['status'] == 'counter_smoke_passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
