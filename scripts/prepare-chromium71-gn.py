#!/usr/bin/env python3
"""Stage the exact historical Linux GN binary without modifying Chromium."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request


def verify(data, expected):
    if hashlib.sha1(data).hexdigest() != expected:
        raise ValueError('GN SHA-1 mismatch; do not execute this file')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if not (workspace / 'preparation.json').is_file():
        raise SystemExit('Expected prepared workspace')
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1')
    head = subprocess.check_output(['git', '-C', str(workspace / 'src'), 'rev-parse', 'HEAD'], env=env, text=True, timeout=30).strip()
    if head != 'c2bec8045f7ad3ece1c5d80236183a21c1fac3f5':
        raise SystemExit('Unexpected Chromium revision')
    expected = (workspace / 'src/buildtools/linux64/gn.sha1').read_text().strip()
    if not re.fullmatch('[0-9a-f]{40}', expected):
        raise SystemExit('Invalid historical GN SHA-1')
    root = Path(tempfile.mkdtemp(prefix='minethrottle71-gn-'))
    report = {'status': 'incomplete', 'expected_sha1': expected, 'directory': str(root),
              'chromium_modified': False, 'build': 'not run'}
    print('New directory (retained):', root, flush=True)
    url = 'https://storage.googleapis.com/chromium-gn/' + expected
    report['url'] = url
    print('Downloading:', url, flush=True)
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            if not response.geturl().startswith('https://'):
                raise ValueError('Refused non-HTTPS redirect')
            data = response.read(64 * 1024 * 1024 + 1)
        if len(data) > 64 * 1024 * 1024:
            raise ValueError('Download exceeds 64 MiB limit')
        binary = root / 'gn'
        binary.write_bytes(data)
        verify(data, expected)
        report['sha256'] = hashlib.sha256(data).hexdigest()
        binary.chmod(0o700)
        result = subprocess.run([str(binary), '--version'], cwd=root, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=15)
        print(result.stdout, flush=True)
        report['version_output'] = result.stdout.strip()
        report['version_exit_code'] = result.returncode
        if result.returncode:
            raise RuntimeError('Historical GN cannot start on this host')
        report['status'] = 'historical_gn_verified_and_version_checked'
    except Exception as error:
        report['error'] = str(error)
    (root / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('Report:', root / 'result.json')
    return 0 if report['status'] == 'historical_gn_verified_and_version_checked' else 1


if __name__ == '__main__':
    raise SystemExit(main())
