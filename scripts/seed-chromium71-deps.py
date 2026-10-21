#!/usr/bin/env python3
"""Reuse unconditional Git dependencies from a primary-DEPS local audit.

Default: plan only. --apply: shared local clones in the new workspace only.
Never evaluates platform conditions, fetches sources or runs gclient/hooks.
"""
import argparse
import collections
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
from urllib.parse import urlsplit

CHROMIUM = 'c2bec8045f7ad3ece1c5d80236183a21c1fac3f5'
OPTIONS = ['-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
           '-c', 'gc.auto=0', '-c', 'maintenance.auto=false']


def environment():
    env = os.environ.copy()
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        env.pop(name, None)
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    return env


def run(command, timeout=60, check=True):
    return subprocess.run(command, env=environment(), timeout=timeout, check=check,
                          capture_output=True, text=True)


def git(repo):
    command = ['git', '--no-optional-locks', '--no-replace-objects', *OPTIONS, '-C', str(repo)]
    for remote in run(command + ['remote'], timeout=15).stdout.splitlines():
        command += ['-c', 'remote.' + remote + '.promisor=false']
    return command


def plan_rows(report):
    if report.get('chromium_revision') != CHROMIUM:
        raise ValueError('Audit Chromium revision mismatch')
    plan = []
    seen = set()
    for row in report['dependencies']:
        item = {'path': row['path'], 'group': row['group']}
        path = PurePosixPath(row['path'])
        definition = row.get('definition')
        condition = definition.get('condition') if isinstance(definition, dict) else None
        url = definition if isinstance(definition, str) else definition.get('url') if isinstance(definition, dict) else None
        candidates = [c['repository'] for c in row.get('candidates', []) if c['status'] == 'commit_present']
        if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != 'src' or len(path.parts) < 2:
            item['status'] = 'unsupported_path'
        elif row['group'] != 'deps':
            item['status'] = 'platform_group_deferred'
        elif condition not in (None, '', True, 'True'):
            item.update(status='condition_deferred', condition=condition)
        elif not isinstance(url, str) or not re.search(r'@[0-9a-f]{40}$', url):
            item['status'] = 'not_a_pinned_git_dependency'
        elif path.as_posix() in seen:
            raise ValueError('Duplicate primary dependency path: ' + str(path))
        elif not candidates:
            item['status'] = 'no_confirmed_local_commit'
        else:
            remote, revision = url.rsplit('@', 1)
            parsed = urlsplit(remote)
            if parsed.scheme != 'https' or parsed.username or parsed.password:
                item['status'] = 'unsupported_remote'
            else:
                item.update(status='candidate', candidates=candidates, remote=remote, revision=revision)
        if row['group'] == 'deps':
            seen.add(path.as_posix())
        plan.append(item)
    return sorted(plan, key=lambda item: (len(PurePosixPath(item['path']).parts), item['path']))


def apply_one(item, workspace):
    target = workspace / item['path']
    # Reject any existing symlink in the destination path, even an internal one.
    for parent in [target, *target.parents]:
        if parent == workspace:
            break
        if parent.is_symlink():
            return dict(item, status='destination_symlink_deferred')
    if not target.resolve().is_relative_to(workspace):
        return dict(item, status='destination_outside_workspace')
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        try:
            command = git(target)
            top = run(command + ['rev-parse', '--show-toplevel'], timeout=15).stdout.strip()
            head = run(command + ['rev-parse', 'HEAD'], timeout=15).stdout.strip()
            if Path(top).resolve() == target and head == item['revision']:
                return dict(item, status='existing_exact_checkout_untouched')
        except (OSError, subprocess.SubprocessError):
            pass
        return dict(item, status='occupied_destination_untouched')
    source = None
    for candidate in item['candidates']:
        try:
            repo = Path(candidate).resolve(strict=True)
            command = git(repo)
            top = run(command + ['rev-parse', '--show-toplevel'], timeout=15).stdout.strip()
            if Path(top).resolve() == repo and run(command + ['cat-file', '-e', item['revision'] + '^{commit}'], timeout=30, check=False).returncode == 0:
                source = repo
                break
        except (OSError, subprocess.SubprocessError):
            continue
    if source is None:
        return dict(item, status='source_recheck_incomplete')
    target.parent.mkdir(parents=True, exist_ok=True)
    print('Local shared clone:', item['path'], '<-', source, flush=True)
    # Only new destinations (or pre-existing empty directories) are populated.
    run(['git', *OPTIONS, 'clone', '--local', '--shared', '--no-checkout', '--no-tags',
         '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
         '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-c', 'core.autocrlf=false',
         '-c', 'submodule.recurse=false', str(source), str(target)], timeout=900)
    command = git(target)
    run(command + ['checkout', '--no-recurse-submodules', '--detach', item['revision']], timeout=900)
    head = run(command + ['rev-parse', 'HEAD']).stdout.strip()
    if head != item['revision']:
        raise ValueError('Unexpected checkout HEAD: ' + str(target))
    run(command + ['remote', 'set-url', 'origin', item['remote']])
    stores = (target / '.git/objects/info/alternates').read_text().splitlines()
    return dict(item, status='local_clone_prepared', source=str(source), borrowed_object_stores=stores)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('audit_report', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    workspace = args.workspace.resolve(strict=True)
    if run(git(workspace / 'src') + ['rev-parse', 'HEAD']).stdout.strip() != CHROMIUM:
        raise ValueError('Unexpected workspace Chromium revision')
    report = json.loads(args.audit_report.read_text())
    plan = plan_rows(report)
    logdir = Path(tempfile.mkdtemp(prefix='deps-seed-', dir=workspace))
    output = logdir / 'result.json'
    state = {'mode': 'apply_local_only' if args.apply else 'plan_only', 'entries': plan, 'status': 'incomplete'}
    output.write_text(json.dumps(state, indent=2) + '\n')
    print('Report:', output, flush=True)
    print('Initial plan:', dict(collections.Counter(x['status'] for x in plan)), flush=True)
    print('Unsupported paths:', [x['path'] for x in plan if x['status'] == 'unsupported_path'])
    print('Deferred conditions:', dict(collections.Counter(str(x.get('condition')) for x in plan if x['status'] == 'condition_deferred')))
    if args.apply:
        for index, item in enumerate(plan):
            if item['status'] == 'candidate':
                plan[index] = apply_one(item, workspace)
                output.write_text(json.dumps(state, indent=2) + '\n')
    state['status'] = 'local_pass_completed_not_dependency_readiness'
    output.write_text(json.dumps(state, indent=2) + '\n')
    print('Final summary:', dict(collections.Counter(x['status'] for x in plan)), flush=True)
    print('Report:', output)
    print('Retain borrowed object stores. No source fetch, condition evaluation, gclient, hook or build run.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('FAILED / INCOMPLETE:', error, flush=True)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stdout or '')
            print(error.stderr or '')
        raise SystemExit(1)
