#!/usr/bin/env python3
"""Fetch the exact historical dependency from a third-party mirror, no sync.

Creates only a previously absent dependency directory, a new alternative
.gclient file, and new logs. Never deletes, moves, or overwrites existing files.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import tempfile

CHROMIUM = 'c2bec8045f7ad3ece1c5d80236183a21c1fac3f5'
REVISION = '5f7cd2497d7a643125c3b6eb910d99ba28be6899'
MIRROR = 'https://github.com/bpsinc-native/src_third_party_devtools-node-modules.git'
DEPENDENCY = 'src/third_party/devtools-node-modules'
CONFIG_NAME = '.gclient.minethrottle-mirror'
OPTIONS = ['-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
           '-c', 'gc.auto=0', '-c', 'maintenance.auto=false',
           '-c', 'fetch.fsckObjects=true', '-c', 'transfer.fsckObjects=true']


def environment():
    env = os.environ.copy()
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_CACHE_PATH'):
        env.pop(name, None)
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    return env


def read_solution(text):
    body = ast.parse(text).body
    if (len(body) != 1 or not isinstance(body[0], ast.Assign) or len(body[0].targets) != 1
            or not isinstance(body[0].targets[0], ast.Name) or body[0].targets[0].id != 'solutions'):
        raise ValueError('Unexpected original .gclient; no overwrite attempted')
    solution = ast.literal_eval(body[0].value)
    expected = [{'name': 'src', 'url': 'https://chromium.googlesource.com/chromium/src.git',
                 'managed': False, 'custom_deps': {}, 'custom_vars': {}}]
    if solution != expected:
        raise ValueError('Original .gclient settings differ; stopping')
    return solution


def fetch_exact(target, remote, revision, logs, timeout=900):
    target.mkdir()  # Refuse existing paths, including empty directories/links.
    git = ['git', *OPTIONS, '-C', str(target)]
    commands = [git + ['init'], git + ['remote', 'add', 'origin', remote],
                git + ['fetch', '--no-tags', '--depth=1', 'origin', revision],
                git + ['fsck', '--strict', '--no-reflogs'],
                git + ['checkout', '--no-recurse-submodules', '--detach', revision]]
    for index, command in enumerate(commands):
        print('Running:', json.dumps(command), flush=True)
        with (logs / ('git-' + str(index) + '.log')).open('xb') as output:
            try:
                result = subprocess.run(command, env=environment(), stdin=subprocess.DEVNULL,
                                        stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
            except subprocess.TimeoutExpired:
                print('TIMEOUT. Partial dependency retained; do not delete or retry unchanged.', flush=True)
                raise
        print((logs / ('git-' + str(index) + '.log')).read_text(errors='replace'), flush=True)
        if result.returncode:
            raise RuntimeError('Git command failed, exit=' + str(result.returncode) + '; original error log retained')
    actual = subprocess.check_output(git + ['rev-parse', 'HEAD'], env=environment(), timeout=30).decode().strip()
    if actual != revision:
        raise ValueError('Fetched checkout HEAD does not match exact historical commit')
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('--fetch-exact', action='store_true', help='Explicitly download the pinned dependency')
    args = parser.parse_args()
    root = args.workspace.resolve(strict=True)
    config = root / CONFIG_NAME
    target = root / DEPENDENCY
    solution = read_solution((root / '.gclient').read_text())
    if os.path.lexists(target) or os.path.lexists(config):
        raise ValueError('Dependency or alternative config already exists; preserve it and inspect before proceeding')
    for parent in target.parents:
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError('Symbolic destination parent; stopping')
    if not target.parent.is_dir():
        raise ValueError('Expected existing third_party directory')
    head = subprocess.check_output(['git', *OPTIONS, '-C', str(root / 'src'), 'rev-parse', 'HEAD'], env=environment(), timeout=30).decode().strip()
    if head != CHROMIUM:
        raise ValueError('Workspace Chromium revision differs')
    print('Third-party mirror:', MIRROR)
    print('Required exact commit:', REVISION)
    print('Original .gclient and DEPS will be preserved.')
    if not args.fetch_exact:
        print('PLAN ONLY: add --fetch-exact to download the pinned dependency and create the new config.')
        return
    logs = Path(tempfile.mkdtemp(prefix='devtools-exact-mirror-', dir=root))
    report = {'mirror': MIRROR, 'expected_revision': REVISION, 'dependency': str(target),
              'alternative_config': str(config), 'status': 'incomplete',
              'original_config': 'untouched', 'gclient_sync': 'not run', 'hooks': 'not run', 'build': 'not run'}
    report_path = logs / 'result.json'
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print('Diagnostic directory:', logs, flush=True)
    actual = fetch_exact(target, MIRROR, REVISION, logs)
    solution[0]['custom_deps'][DEPENDENCY] = MIRROR + '@' + REVISION
    with config.open('x') as output:
        output.write('solutions = ' + repr(solution) + '\n')
    report.update(status='exact_commit_verified_alternative_config_prepared', actual_revision=actual)
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('Report:', report_path)
    print('STOP: do not run previous sync command; it still selects the dead URL. No gclient sync was run.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print('FAILED / INCOMPLETE:', error, flush=True)
        raise SystemExit(1)
