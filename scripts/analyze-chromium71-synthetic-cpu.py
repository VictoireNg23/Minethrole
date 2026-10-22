#!/usr/bin/env python3
"""Audit recorded synthetic CPU clocks and counters; do not classify or launch code."""
import argparse
import json
from pathlib import Path
import tempfile


def inspect_count(text):
    groups = {}
    malformed = 0
    for line in text.splitlines():
        fields = line.split()
        if len(fields) == 3:  # original sampler header, not a module row
            continue
        try:
            if len(fields) != 22:
                raise ValueError('Unexpected row width')
            row = [int(value) for value in fields]
            if row[4] < 0 or not 0 <= row[5] < 1000000000:
                raise ValueError('Invalid timespec')
            groups.setdefault(tuple(row[:3]), []).append((row[4] * 1000000000 + row[5], row[10:]))
        except ValueError:
            malformed += 1
    streams = []
    for key, rows in groups.items():
        delta = [b[0] - a[0] for a, b in zip(rows, rows[1:])]
        streams.append(dict(identity=list(key), samples=len(rows),
                            cpu_span_ms=(rows[-1][0] - rows[0][0]) / 1000000,
                            cpu_monotonic=all(value >= 0 for value in delta),
                            cpu_advances=any(value > 0 for value in delta),
                            counters_monotonic=all(all(y >= x for x, y in zip(a[1], b[1]))
                                                   for a, b in zip(rows, rows[1:]))))
    return dict(malformed_rows=malformed, streams=streams)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('signature_report', type=Path)
    args = parser.parse_args()
    path = args.signature_report.resolve()
    previous = json.loads(path.read_text())
    cases = previous.get('cases', [])
    expected = {(kind + str(i), repeat) for kind in ('active', 'dormant')
                for i in range(12) for repeat in range(3)}
    if (previous.get('status') != 'synthetic_browser_all_signatures_passed' or
            len(cases) != 72 or {(c.get('mode'), c.get('repeat')) for c in cases} != expected or
            any(c.get('status') != 'passed' for c in cases)):
        parser.error('Expected complete successful 72-case signature report')
    results = []
    for case in cases:
        directory = path.parent / (case['mode'] + '-' + str(case['repeat']))
        files = [dict(file=p.name, **inspect_count(p.read_text(errors='replace')))
                 for p in sorted(directory.glob('*.count'))]
        streams = [stream for item in files for stream in item['streams']]
        valid = bool(streams) and all(item['malformed_rows'] == 0 for item in files) and all(
            s['samples'] >= 2 and s['cpu_monotonic'] and s['cpu_advances'] and s['counters_monotonic']
            for s in streams)
        results.append(dict(mode=case['mode'], repeat=case['repeat'],
                            status='consistent' if valid else 'needs_inspection', files=files))
    destination = Path(tempfile.mkdtemp(prefix='synthetic-cpu-audit-', dir=path.parent.parent))
    report = dict(status='synthetic_cpu_clocks_consistent' if all(c['status'] == 'consistent' for c in results)
                  else 'synthetic_cpu_clocks_need_inspection',
                  source_report=str(path), binary_sha256=previous.get('binary_sha256'),
                  sandbox_disabled=previous.get('sandbox_disabled'), glibc_tunables=previous.get('glibc_tunables'),
                  cases=results, browser_started=False, dataset_execution='not run',
                  classification='not performed',
                  limits='Clock consistency only; not CPU accuracy, reference-profile equivalence or original decision validation')
    (destination / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Status:', report['status'])
    print('Cases:', len(results))
    print('Consistent:', sum(c['status'] == 'consistent' for c in results))
    spans = [s['cpu_span_ms'] for c in results for f in c['files'] for s in f['streams']]
    print('Observed CPU spans in ms:', {'min': min(spans), 'max': max(spans)} if spans else None)
    print('Report:', destination / 'result.json')
    return 0 if report['status'] == 'synthetic_cpu_clocks_consistent' else 1


if __name__ == '__main__':
    raise SystemExit(main())
