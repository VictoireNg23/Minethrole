#!/usr/bin/env python3
"""Read existing sync logs and local metadata; no sync, network or cleanup."""
import argparse
import collections
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def significant(lines):
    heartbeat = re.compile(r'^\[[0-9:.]+\]\s*(?:Still working on:|src)\s*$')
    return [line for line in lines if line.strip() and not heartbeat.match(line)]


def inspect_log(path):
    # Stream the log rather than retaining an entire long progress journal.
    first = []
    last = collections.deque(maxlen=80)
    operations = collections.deque(maxlen=60)
    count = 0
    with path.open(errors='replace') as stream:
        for raw in stream:
            count += 1
            line = raw.rstrip('\n')
            if len(first) < 70:
                first.append(line)
            if significant([line]):
                last.append(line)
            if re.search(r'fetch|clone|cache|error|fatal|warning|retry|https?://|running ', line, re.I):
                operations.append(line)
    return {'line_count': count, 'first_lines': first,
            'last_non_heartbeat_lines': list(last), 'operation_lines': list(operations)}


def proc_observations(roots):
    result = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cwd = (entry / 'cwd').resolve(strict=True)
            if not any(cwd.is_relative_to(root) for root in roots):
                continue
            # Do not print command lines, environment variables or credentials.
            name = (entry / 'comm').read_text().strip()
            result.append({'pid': int(entry.name), 'executable_name': name, 'cwd': str(cwd)})
        except (OSError, RuntimeError, ValueError):
            continue
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('sync_diagnostic_directory', type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve(strict=True)
    diagnostic = args.sync_diagnostic_directory.resolve(strict=True)
    if not diagnostic.is_relative_to(workspace):
        raise ValueError('Expected diagnostic directory inside workspace')
    manifest = json.loads((workspace / 'preparation.json').read_text())
    tools = Path(manifest['tools']).resolve(strict=True)
    report = {'previous_result': json.loads((diagnostic / 'result.json').read_text()),
              'log': inspect_log(diagnostic / 'sync.log'), 'local_git': {},
              'existing_locks': [], 'new_pack_files': [], 'cache_top_level': []}
    env = os.environ.copy()
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        env.pop(key, None)
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    for name in ('src', 'src/v8'):
        repo = workspace / name
        command = ['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null', '-C', str(repo)]
        report['local_git'][name] = {}
        for label, argv in [('HEAD', ['rev-parse', '--verify', 'HEAD']), ('shallow', ['rev-parse', '--is-shallow-repository'])]:
            try:
                result = subprocess.run(command + argv, env=env, capture_output=True, text=True, timeout=15)
                report['local_git'][name][label] = {'exit': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
            except (OSError, subprocess.TimeoutExpired) as error:
                report['local_git'][name][label] = {'unavailable': str(error)}
        for filename in ('index.lock', 'packed-refs.lock', 'shallow.lock', 'FETCH_HEAD.lock'):
            path = repo / '.git' / filename
            if path.exists():
                report['existing_locks'].append({'path': str(path), 'bytes': path.stat().st_size})
        packs = repo / '.git/objects/pack'
        if packs.is_dir():
            report['new_pack_files'].extend({'path': str(p), 'bytes': p.stat().st_size} for p in packs.iterdir() if p.is_file())
    cache = workspace / 'git-cache'
    if cache.is_dir():
        report['cache_top_level'] = [{'name': p.name, 'is_directory': p.is_dir()} for p in cache.iterdir()]
    report['processes_in_workspace_or_tools'] = proc_observations([workspace, tools])
    # Read selected SCM code as text, never import or execute it. These excerpts
    # help distinguish cache/fetch decisions made by this exact old revision.
    scm = tools / 'depot_tools/gclient_scm.py'
    excerpts = []
    if scm.is_file():
        lines = scm.read_text(errors='replace').splitlines()
        matches = [i for i, line in enumerate(lines) if re.search(r'def (_Fetch|update|_GetCacheMirror)\b|git_cache\.Mirror|GetCachePath', line)]
        for index in matches[:8]:
            excerpts.append({'line': index + 1, 'text': '\n'.join(lines[max(0, index-2):index+26])})
    report['historical_scm_excerpts'] = excerpts
    output = Path(tempfile.mkdtemp(prefix='sync-timeout-diagnostic-', dir=workspace)) / 'report.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print('Report:', output)
    for key, value in report.items():
        print('\n=== ' + key + ' ===')
        print(json.dumps(value, indent=2))
    print('\nEND: no source fetch, sync, hook, build, process termination or lock removal performed.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print('FAILED / INCOMPLETE:', error)
        raise SystemExit(1)
