#!/usr/bin/env python3
"""Read-only inspection of the isolated WebRTC index and worktree."""
import argparse
from collections import Counter
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    target = workspace / 'src/third_party/webrtc'
    if not (workspace / 'preparation.json').is_file() or target.is_symlink() or target.resolve() != target or not (target / '.git').exists():
        raise SystemExit('Refused: unexpected workspace or repository path')
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    commands = [(['rev-parse', '--show-toplevel'], False),
                (['rev-parse', '--verify', 'HEAD'], False),
                (['rev-parse', '--verify', 'HEAD^{tree}'], False),
                (['status', '--porcelain=v1', '--untracked-files=all'], True),
                (['ls-files', '--stage'], True)]
    for command, bounded in commands:
        print('\n=== git %s ===' % ' '.join(command), flush=True)
        try:
            result = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(target)] + command,
                                    env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, errors='replace', timeout=60)
            lines = result.stdout.splitlines()
            print('exit:', result.returncode, 'total lines:', len(lines))
            if command[0] == 'status':
                print('Status counts:', dict(Counter(line[:2] for line in lines)))
            print('\n'.join(lines[:60] if bounded else lines))
            print(result.stderr[:4000])
        except subprocess.TimeoutExpired:
            print('TIMEOUT; observation unavailable')
    print('\n=== Top-level entries (first 60) ===')
    entries = sorted(target.iterdir(), key=lambda path: path.name)
    for path in entries[:60]:
        print(repr(path.name), 'symlink' if path.is_symlink() else 'directory' if path.is_dir() else 'file')
    print('Total entries:', len(entries))
    print('END: no fetch, checkout, index write, deletion, move, hook or build requested.')


if __name__ == '__main__':
    main()
