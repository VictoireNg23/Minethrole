#!/usr/bin/env python3
"""Fetch only the required historical WebRTC revision into a NEW temporary repo."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

REVISION = '0ba24191ee90c70679d2452363676c2d65b6b751'
URL = 'https://webrtc.googlesource.com/src.git'


def main():
    root = Path(tempfile.mkdtemp(prefix='minethrottle71-webrtc-exact-'))
    repo = root / 'repository'
    print('NEW directory (retained on failure):', root, flush=True)
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_NO_LAZY_FETCH='1')
    report = {'revision': REVISION, 'url': URL, 'repository': str(repo), 'status': 'incomplete',
              'checkout': 'not run', 'gclient': 'not run', 'hooks': 'not run', 'build': 'not run'}
    commands = [['init', str(repo)], ['-C', str(repo), 'fetch', '--no-tags', '--depth=1', URL, REVISION],
                ['-C', str(repo), 'rev-parse', '--verify', 'FETCH_HEAD^{commit}'],
                ['-C', str(repo), 'cat-file', '-t', REVISION + '^{tree}'],
                ['-C', str(repo), 'fsck', '--strict', '--no-reflogs']]
    try:
        for index, args in enumerate(commands):
            command = ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'gc.auto=0',
                       '-c', 'maintenance.auto=false', '-c', 'fetch.fsckObjects=true',
                       '-c', 'transfer.fsckObjects=true'] + args
            print('Running:', json.dumps(command), flush=True)
            # Each command owns a log; a fetch timeout cannot overwrite prior output.
            with (root / ('command-%d.log' % index)).open('w+') as log:
                try:
                    result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
                finally:
                    log.seek(0)
                    output = log.read()
                    print(output[-16000:], flush=True)
            if result.returncode:
                raise RuntimeError('Command %d exited %d' % (index, result.returncode))
            if index == 2 and output.strip() != REVISION:
                raise RuntimeError('FETCH_HEAD differs from required revision')
        report['status'] = 'exact_commit_fetched_and_fsck_passed'
    except (subprocess.TimeoutExpired, RuntimeError, OSError) as error:
        report['error'] = str(error)
    (root / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('Report:', root / 'result.json')
    return 0 if report['status'] == 'exact_commit_fetched_and_fsck_passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
