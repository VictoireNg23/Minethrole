#!/usr/bin/env python3
"""Read original decision settings; never enable defense or run Chromium."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile


def settings(source):
    result = {}
    for name, pattern, convert in [
        ('defensive_enabled', r'bool\s+is_defensive\s*=\s*(true|false)\s*;', lambda x: x == 'true'),
        ('interval_cpu_ms', r'int\s+INTERVAL\s*=\s*(\d+)\s*;', int),
        ('cosine_threshold', r'double\s+Cosine_threshold\s*=\s*([\d.]+)\s*;', float),
        ('sigma_threshold', r'double\s+Sigma_threshold\s*=\s*([\d.]+)\s*;', float),
        ('sleep_seconds', r'int\s+SLEEP_TIME\s*=\s*(\d+)\s*;', int),
    ]:
        matches = re.findall(pattern, source)
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous setting: ' + name)
        result[name] = convert(matches[0])
    for name in ('baseline_value', 'baseline_stddev', 'baseline_normalized'):
        match = re.search(r'double\s+' + name + r'\[4\]\[3\]\s*=\s*(\{.*?\});', source, re.S)
        if not match:
            raise ValueError('Missing profile array: ' + name)
        result[name] = json.loads(match[1].replace('{', '[').replace('}', ']'))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('cpu_report', type=Path)
    args = parser.parse_args()
    cpu_path = args.cpu_report.resolve()
    cpu = json.loads(cpu_path.read_text())
    if cpu.get('status') != 'synthetic_cpu_clocks_consistent' or len(cpu.get('cases', [])) != 72:
        parser.error('Expected successful 72-case CPU audit')
    source_path = args.workspace.resolve() / 'src/v8/src/wasm/module-compiler.cc'
    source = source_path.read_text()
    observed = settings(source)
    root = Path(__file__).resolve().parents[1]
    original = json.loads((root / 'config/original.json').read_text())
    expected = {k: original[k] for k in ('interval_cpu_ms', 'cosine_threshold', 'sigma_threshold', 'sleep_seconds')}
    expected.update(defensive_enabled=original['original_defensive_default'],
                    baseline_value=original['means'], baseline_stddev=original['stddev'],
                    baseline_normalized=original['normalized'])
    mismatches = [key for key in expected if observed[key] != expected[key]]
    destination = Path(tempfile.mkdtemp(prefix='decision-readiness-', dir=cpu_path.parent.parent))
    report = dict(status='original_decision_settings_confirmed' if not mismatches else 'decision_settings_differ',
                  source=str(source_path), source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
                  cpu_report=str(cpu_path), settings=observed, mismatches=mismatches,
                  decision_executed_by_this_inspection=False, sources_modified=False,
                  browser_started=False, dataset_execution='not run',
                  limits='Source inspection only. Defense false disables the original decision branch; no mining verdict established.')
    (destination / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('Report:', destination / 'result.json')
    return 0 if not mismatches else 1


if __name__ == '__main__':
    raise SystemExit(main())
