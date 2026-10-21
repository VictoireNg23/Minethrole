#!/usr/bin/env python3
"""Inspect WebRTC checkout failure without fetching or changing repositories."""
import argparse
import os
from pathlib import Path
import subprocess

REVISION = '0ba24191ee90c70679d2452363676c2d65b6b751'


def inspect(path):
    print('\n=== Repository candidate:', path, '===', flush=True)
    print('exists:', path.exists(), 'symlink:', path.is_symlink())
    if not path.is_dir():
        return
    if not (path / '.git').exists():
        print('No own .git entry; do not query an enclosing repository.')
        return
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    commands = [['rev-parse', '--show-toplevel'], ['rev-parse', '--verify', 'HEAD'],
                ['rev-parse', '--is-shallow-repository'], ['config', '--get', 'remote.origin.url'],
                ['cat-file', '-t', REVISION], ['cat-file', '-t', REVISION + '^{tree}'],
                ['config', '--get-regexp', r'remote\..*\.(fetch|promisor|partialclonefilter)']]
    for args in commands:
        print('git', ' '.join(args), flush=True)
        try:
            result = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(path)] + args,
                                    env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=30, text=True, errors='replace')
            print(result.stdout[:12000].rstrip(), '\nexit:', result.returncode)
        except subprocess.TimeoutExpired:
            print('TIMEOUT: observation unavailable')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('log', type=Path)
    parser.add_argument('--original-project', type=Path)
    args = parser.parse_args()
    third_party = args.workspace / 'src/third_party'
    candidates = [third_party / 'webrtc'] + sorted(third_party.glob('_gclient_webrtc_*'))
    if args.original_project:
        candidates += [args.original_project / name / 'src/third_party/webrtc' for name in ('chromium', 'chromium71')]
    for candidate in candidates:
        inspect(candidate)
    print('\n=== Relevant log lines (first 60 matches; 2000 characters per line) ===')
    matches = 0
    with args.log.open(encoding='utf-8', errors='replace') as log:
        for number, line in enumerate(log, 1):
            if 'webrtc' in line.lower() or REVISION in line:
                matches += 1
                if matches <= 60:
                    print('%d: %s' % (number, line.rstrip()[:2000]))
    print('Total matching lines:', matches)
    print('END: no fetch, checkout, move, deletion, hook or build performed.')


if __name__ == '__main__':
    main()
