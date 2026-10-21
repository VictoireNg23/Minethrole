#!/usr/bin/env python3
"""Integrate verified WebRTC objects locally, refusing occupied or modified files."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

REVISION = '0ba24191ee90c70679d2452363676c2d65b6b751'


def git(repo, *args):
    command = ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
               '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-c', 'fetch.fsckObjects=true',
               '-C', str(repo)] + list(args)
    result = subprocess.run(command, env=dict(os.environ, GIT_NO_LAZY_FETCH='1',
                            GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0'),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=180)
    if result.returncode:
        raise RuntimeError('%s\n%s' % (' '.join(command), result.stderr))
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('fetch_report', type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if not (workspace / 'preparation.json').is_file():
        raise SystemExit('Refused: missing isolated workspace preparation.json')
    logdir = Path(tempfile.mkdtemp(prefix='webrtc-integrate-', dir=workspace))
    report = {'status': 'incomplete', 'gclient': 'not run', 'hooks': 'not run', 'build': 'not run'}
    print('Diagnostic directory:', logdir, flush=True)
    try:
        source_report = json.loads(args.fetch_report.read_text())
        if source_report.get('status') != 'exact_commit_fetched_and_fsck_passed' or source_report.get('revision') != REVISION:
            raise RuntimeError('Fetch report does not confirm required commit')
        source = Path(source_report['repository']).resolve()
        target = workspace / 'src/third_party/webrtc'
        if target.is_symlink() or target.resolve() != target or not (target / '.git').exists():
            raise RuntimeError('Refused: target absent, symlinked or without own .git')
        if Path(git(target, 'rev-parse', '--show-toplevel')).resolve() != target:
            raise RuntimeError('Unexpected repository root')
        if git(target, 'status', '--porcelain=v1', '--untracked-files=all'):
            raise RuntimeError('Refused: tracked or untracked changes in target; preserve and inspect')
        if git(source, 'rev-parse', '--verify', 'FETCH_HEAD^{commit}') != REVISION:
            raise RuntimeError('Source FETCH_HEAD differs')
        if git(source, 'cat-file', '-t', REVISION + '^{tree}') != 'tree':
            raise RuntimeError('Source tree unavailable')
        print('Importing exact commit from local repository only.', flush=True)
        git(target, 'fetch', '--no-tags', '--depth=1', str(source), REVISION)
        if git(target, 'rev-parse', '--verify', 'FETCH_HEAD^{commit}') != REVISION:
            raise RuntimeError('Imported revision differs')
        git(target, 'checkout', '--no-recurse-submodules', '--detach', REVISION)
        report['actual_revision'] = git(target, 'rev-parse', 'HEAD')
        if report['actual_revision'] != REVISION or git(target, 'status', '--porcelain=v1', '--untracked-files=all'):
            raise RuntimeError('Post-check failed')
        report['status'] = 'exact_webrtc_checkout_prepared'
        report['target'] = str(target)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as error:
        report['error'] = str(error)
    (logdir / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('Report:', logdir / 'result.json')
    return 0 if report['status'] == 'exact_webrtc_checkout_prepared' else 1


if __name__ == '__main__':
    raise SystemExit(main())
