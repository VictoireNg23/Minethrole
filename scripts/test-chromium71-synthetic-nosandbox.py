#!/usr/bin/env python3
"""Run only the repository's benign synthetic fixture without Chromium sandbox."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import signal
import subprocess
import tempfile

EXPECTED_BINARY = '59e77231028f446d0abe03342ab6b2c2e17687a99aa86b58ca82f4118fb9218c'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results_run', type=Path)
    parser.add_argument('--browser', type=Path, default=Path('/tmp/minethrottle71-browser-test-_ysw60o_/browser/chrome'))
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    if os.geteuid() != 0 or not 1 <= args.repeats <= 10:
        parser.error('Root controller required; repeats must be 1..10')
    binary = args.browser.resolve()
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    if digest != EXPECTED_BINARY:
        parser.error('Unexpected browser SHA256; inspect build provenance first')
    account = pwd.getpwnam('minethrottle-test')
    if account.pw_uid == 0:
        parser.error('Runtime account must be nonroot')
    raw = args.results_run.resolve() / 'raw'
    if not raw.is_dir():
        parser.error('Expected existing persistent run/raw directory')
    output = Path(tempfile.mkdtemp(prefix='synthetic-nosandbox-', dir=raw))
    fixture = Path(__file__).resolve().parents[1] / 'tests/fixtures/browser-wasm-counter.html'
    shutil.copy2(fixture, output / 'fixture.html')
    cases = []
    print('Persistent results:', output, flush=True)
    for mode in ('negative', 'dormant', 'active'):
        for repeat in range(args.repeats):
            saved = output / f'{mode}-{repeat}'
            saved.mkdir()
            local = Path(tempfile.mkdtemp(prefix='minethrottle71-synthetic-'))
            page = local / 'test.html'
            shutil.copyfile(fixture, page)
            os.chown(page, account.pw_uid, account.pw_gid)
            os.chown(local, account.pw_uid, account.pw_gid)
            command = ['/usr/sbin/runuser', '-u', account.pw_name, '--', str(binary),
                       '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
                       '--no-first-run', '--no-default-browser-check', '--disable-background-networking',
                       '--disable-component-update', '--disable-extensions', '--disable-sync',
                       '--metrics-recording-only', '--user-data-dir=' + str(local / 'profile'),
                       '--dump-dom', page.as_uri() + '#' + mode]
            env = dict(os.environ)
            tunables = [x for x in env.get('GLIBC_TUNABLES', '').split(':')
                        if x and not x.startswith('glibc.pthread.rseq=')]
            env['GLIBC_TUNABLES'] = ':'.join(tunables + ['glibc.pthread.rseq=0'])
            timeout = False
            with (saved / 'stdout.html').open('w') as stdout, (saved / 'stderr.log').open('w') as stderr:
                process = subprocess.Popen(command, cwd=local, env=env, stdout=stdout, stderr=stderr,
                                           start_new_session=True)
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    timeout = True
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
            rows = []
            artifacts = []
            for path in local.iterdir():
                if path.is_file() and path.suffix in ('.count', '.stack', '.txt', '.asmjs'):
                    shutil.copy2(path, saved / path.name)
                    artifacts.append(path.name)
                    if path.suffix == '.count':
                        for line in path.read_text(errors='replace').splitlines():
                            fields = line.split()
                            if len(fields) == 22:
                                try:
                                    rows.append([int(x) for x in fields[10:]])
                                except ValueError:
                                    pass
            text = (saved / 'stdout.html').read_text(errors='replace')
            match = re.search(r'<pre id="wasm-result">(.*?)</pre>', text, re.S)
            try:
                observed = json.loads(html.unescape(match.group(1))) if match else None
            except ValueError:
                observed = None
            expected = [20000 if mode == 'active' else 0] + [0] * 11
            maxima = [max(row[i] for row in rows) for i in range(12)] if rows else None
            passed = (process.returncode == 0 and not timeout and maxima == expected and
                      observed == {'status': 'executed', 'mode': mode,
                                   'calls': 0 if mode == 'dormant' else 20000})
            case = dict(mode=mode, repeat=repeat, status='passed' if passed else 'failed_or_unmeasurable',
                        exit_code=process.returncode, timeout=timeout, sample_rows=len(rows),
                        counter_maxima=maxima, expected=expected, wasm_result=observed,
                        command=command, local_directory=str(local), artifacts=artifacts)
            (saved / 'result.json').write_text(json.dumps(case, indent=2) + '\n')
            cases.append(case)
            print(json.dumps({k: case[k] for k in ('mode', 'repeat', 'status', 'exit_code', 'sample_rows', 'counter_maxima')}), flush=True)
    passed = all(case['status'] == 'passed' for case in cases)
    report = dict(status='synthetic_browser_controls_passed' if passed else 'synthetic_browser_controls_failed_or_incomplete',
                  binary_sha256=digest, sandbox_disabled=True, runtime_user=account.pw_name,
                  glibc_tunables=env['GLIBC_TUNABLES'], fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest(),
                  cases=cases, dataset_execution='not run', detection_validation='not performed')
    (output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Status:', report['status'])
    print('Report:', output / 'result.json')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
