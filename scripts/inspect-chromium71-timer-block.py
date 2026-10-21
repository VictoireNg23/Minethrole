#!/usr/bin/env python3
"""Read sources and failed browser output; never launch or modify Chromium."""
import argparse
import json
from pathlib import Path
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('browser_report', type=Path)
    args = parser.parse_args()
    report_path = args.browser_report.resolve()
    previous = json.loads(report_path.read_text())
    src = args.workspace.resolve() / 'src'
    findings = []
    searches = {
        'sandbox/linux/seccomp-bpf-helpers/baseline_policy.cc': ('setitimer', 'IsAllowed', 'EvaluateSyscall'),
        'sandbox/linux/seccomp-bpf-helpers/syscall_sets.cc': ('setitimer', 'IsAllowed', 'IsTimer'),
        'sandbox/policy/linux/bpf_renderer_policy_linux.cc': ('setitimer', 'EvaluateSyscall'),
        'v8/src/wasm/module-compiler.cc': ('void SetTimer(', 'void SignalHandler(', 'pthread_getcpuclockid'),
    }
    for name, needles in searches.items():
        path = src / name
        if not path.is_file():
            findings.append({'file': name, 'missing': True})
            continue
        lines = path.read_text().splitlines()
        selected = set()
        for index, line in enumerate(lines):
            if any(needle in line for needle in needles):
                selected.update(range(max(0, index - 5), min(len(lines), index + 42)))
        findings.append({'file': name, 'lines': [f'{i + 1}: {lines[i]}' for i in sorted(selected)]})
    output = report_path.parent / 'stdout.html'
    text = output.read_text(errors='replace') if output.is_file() else ''
    result = {
        'status': 'read_only_timer_block_inspection',
        'source_report': str(report_path),
        'stderr': previous.get('stderr_tail'),
        'stdout_tail': text[-12000:],
        'sources': findings,
        'browser_started': False,
        'sources_modified': False,
        'dataset_execution': 'not run',
    }
    destination = Path(tempfile.mkdtemp(prefix='timer-inspection-', dir=report_path.parent.parent))
    (destination / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', destination / 'result.json')


if __name__ == '__main__':
    main()
