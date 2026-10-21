#!/usr/bin/env python3
"""Read-only diagnosis of the historical devtools-node-modules sync failure."""
import argparse
import ast
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile

DEPENDENCY = 'src/third_party/devtools-node-modules'


def describe(path):
    result = {'path': str(path), 'lexists': os.path.lexists(path)}
    if not result['lexists']:
        return result
    info = path.lstat()
    result.update(mode=stat.filemode(info.st_mode), uid=info.st_uid, gid=info.st_gid,
                  bytes=info.st_size, mtime_ns=info.st_mtime_ns)
    if stat.S_ISLNK(info.st_mode):
        result['symlink_target'] = os.readlink(path)
        result['target_exists'] = path.exists()
    elif stat.S_ISDIR(info.st_mode):
        result['children_first_25'] = sorted(p.name for p in path.iterdir())[:25]
    return result


def entries_value(text, key):
    # Parse only literal entries assignments; never execute .gclient_entries.
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'entries' for t in node.targets):
            value = ast.literal_eval(node.value)
            if not isinstance(value, dict):
                raise ValueError('entries is not a dictionary')
            return value.get(key)
    return None


def log_context(path):
    lines = path.read_text(errors='replace').splitlines()
    selected = set(range(min(50, len(lines))))
    for i, line in enumerate(lines):
        if any(word in line for word in ('devtools-node-modules', '_DeleteOrMove', 'IOError:', 'Error:', 'URL changed')):
            selected.update(range(max(0, i-12), min(len(lines), i+15)))
    return [{'line': i+1, 'text': lines[i]} for i in sorted(selected)]


def git_observation(repo, args):
    env = os.environ.copy()
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        env.pop(key, None)
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    try:
        result = subprocess.run(['git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
                                 '-c', 'core.hooksPath=/dev/null', '-c', 'remote.origin.promisor=false',
                                 '-C', str(repo), *args], env=env, capture_output=True, text=True, timeout=20)
        return {'exit': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {'unavailable': str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('sync_diagnostic_directory', type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve(strict=True)
    diagnostic = args.sync_diagnostic_directory.resolve(strict=True)
    if not diagnostic.is_relative_to(root):
        raise ValueError('Diagnostic directory outside workspace')
    manifest = json.loads((root / 'preparation.json').read_text())
    tools = Path(manifest['tools'])
    target = root / DEPENDENCY
    report = {'sync_result': json.loads((diagnostic / 'result.json').read_text()),
              'log_context': log_context(diagnostic / 'sync.log'),
              'filesystem': [describe(target), describe(target.parent), describe(target / '.git')],
              'git_tree': git_observation(root / 'src', ['ls-tree', 'HEAD', '--', 'third_party/devtools-node-modules']),
              'git_index': git_observation(root / 'src', ['ls-files', '--stage', '--', 'third_party/devtools-node-modules']),
              'matching_audits': [], 'matching_seed_results': [], 'historical_code': []}
    for clone in manifest.get('clones', []):
        if clone['destination'] == str(root / 'src'):
            report['filesystem'].append(describe(Path(clone['source']) / 'third_party/devtools-node-modules'))
    for path in [root / '.gclient_entries', root / 'src/.gclient_entries']:
        if path.is_file():
            try:
                report.setdefault('gclient_entries', []).append({'path': str(path), 'value': entries_value(path.read_text(), DEPENDENCY)})
            except (ValueError, SyntaxError, TypeError) as error:
                report.setdefault('gclient_entries', []).append({'path': str(path), 'unavailable': str(error)})
    for pattern, field, section in [('deps-audit-*/report.json', 'matching_audits', 'dependencies'),
                                    ('deps-seed-*/result.json', 'matching_seed_results', 'entries')]:
        for path in sorted(root.glob(pattern)):
            data = json.loads(path.read_text())
            matches = [row for row in data[section] if row['path'] == DEPENDENCY]
            if matches:
                report[field].append({'report': str(path), 'entries': matches})
    for path in [root / '_bad_scm', root / 'src/_bad_scm']:
        report['filesystem'].append(describe(path))
    scm = tools / 'depot_tools/gclient_scm.py'
    lines = scm.read_text(errors='replace').splitlines()
    for start, end in [(160, 212), (470, 570)]:
        report['historical_code'].append({'file': str(scm), 'first_line': start,
                                          'text': '\n'.join(lines[start-1:end])})
    output = Path(tempfile.mkdtemp(prefix='devtools-diagnostic-', dir=root)) / 'report.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print('Report:', output)
    for name, data in report.items():
        print('\n=== ' + name + ' ===\n' + json.dumps(data, indent=2))
    print('\nEND: no sync, source fetch, hook, patch, move, deletion or build performed.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, SyntaxError) as error:
        print('FAILED / INCOMPLETE:', error)
        raise SystemExit(1)
