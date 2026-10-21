#!/usr/bin/env python3
"""Run only the benign counter fixture; compare original .count output to expectations."""
import argparse
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('build_report', type=Path)
    parser.add_argument('fixture', type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    build = json.loads(args.build_report.read_text())
    if build.get('status') != 'd8_build_passed' or build.get('exit_code') != 0:
        raise SystemExit('Successful d8 build required')
    # Recover the exact output from the recorded Ninja -C argument.
    output = Path(build['command'][build['command'].index('-C') + 1]).resolve()
    if output.parent != root / 'src/out' or not (root / 'preparation.json').is_file():
        raise SystemExit('Unexpected output path')
    fixture = args.fixture.resolve()
    run = Path(tempfile.mkdtemp(prefix='counter-smoke-', dir=root))
    result = {'status': 'incomplete', 'cases': [], 'dataset_execution': 'not run', 'defense_validation': 'not performed'}
    for mode in ('dormant', 'negative', 'active'):
        cwd = run / mode
        cwd.mkdir()
        item = {'mode': mode, 'status': 'incomplete'}
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
            expected = [20000] + [0] * 11 if mode == 'active' else [0] * 12
            item['expected'] = expected
            item['status'] = 'passed' if process.returncode == 0 and 'SMOKE_OK ' + mode in process.stdout and item['counter_maxima'] == expected else 'failed_or_unmeasurable'
        except Exception as error:
            item['error'] = str(error)
        result['cases'].append(item)
    result['status'] = 'counter_smoke_passed' if all(i['status'] == 'passed' for i in result['cases']) else 'counter_smoke_failed_or_incomplete'
    (run / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', run / 'result.json')
    return 0 if result['status'] == 'counter_smoke_passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
