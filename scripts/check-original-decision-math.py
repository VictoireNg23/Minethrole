#!/usr/bin/env python3
"""Check original profile arithmetic only; no dataset classifier or runtime verdict."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import tempfile


def scores(speeds, means, stddev, normalized):
    norm = math.sqrt(sum(x*x for x in speeds))
    cosine = -1.0 if norm == 0 else sum(x / norm * y for x, y in zip(speeds, normalized))
    sigma = sum((x - mean) / std for x, mean, std in zip(speeds, means, stddev)) / 3
    return cosine, sigma


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('readiness_report', type=Path)
    args = parser.parse_args()
    source = args.readiness_report.resolve()
    readiness = json.loads(source.read_text())
    if readiness.get('status') != 'original_decision_settings_confirmed' or readiness.get('mismatches') != []:
        parser.error('Confirmed original settings required')
    settings = readiness['settings']
    cases = []
    for profile in range(4):
        means = settings['baseline_value'][profile]
        stddev = settings['baseline_stddev'][profile]
        normalized = settings['baseline_normalized'][profile]
        # These are theoretical speeds, not measured fixture rates or labels.
        for name, vector in [('reference_mean', means), ('zero', [0, 0, 0]),
                             ('different_shape', [means[0], 0, 0])]:
            cosine, sigma = scores(vector, means, stddev, normalized)
            condition = cosine >= settings['cosine_threshold'] and sigma >= -settings['sigma_threshold']
            expected = name == 'reference_mean'
            cases.append(dict(profile=profile, input=name, speeds=vector, cosine=cosine,
                              mean_zscore=sigma, original_positive_condition=condition,
                              expected_condition=expected,
                              passed=condition == expected and (name != 'reference_mean' or abs(sigma) < 1e-12)))
    output = Path(tempfile.mkdtemp(prefix='decision-math-', dir=source.parent.parent))
    passed = all(c['passed'] for c in cases)
    report = dict(status='original_profile_math_checks_passed' if passed else 'original_profile_math_checks_failed',
                  readiness_report=str(source), readiness_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  cases=cases, chromium_execution='not run', defense_enabled=False,
                  dataset_execution='not run', classification='not performed',
                  limits='Python arithmetic cross-check of the original three-component score only. Does not validate C++ execution, sampling gates, signal delivery, slowing or measured mining profiles.')
    (output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    for case in cases:
        print(json.dumps(case))
    print('Status:', report['status'])
    print('Report:', output / 'result.json')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
