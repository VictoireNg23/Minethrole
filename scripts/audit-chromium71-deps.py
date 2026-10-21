#!/usr/bin/env python3
"""Inspect primary historical DEPS and local objects; no evaluation of DEPS code.

Conditions are reported, NOT evaluated. Nested DEPS and downloads are not run.
"""
import argparse
import ast
import collections
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile

CHROMIUM = 'c2bec8045f7ad3ece1c5d80236183a21c1fac3f5'


class Reader:
    def __init__(self, text):
        self.text = text
        self.assignments = {}
        self.mutations = []
        for node in ast.parse(text).body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id in self.assignments:
                            self.mutations.append(target.id)
                        self.assignments[target.id] = node.value
                    elif isinstance(target, ast.Subscript):
                        self.mutations.append(ast.unparse(target))
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                self.mutations.append(ast.unparse(node.value.func))
            elif not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)):
                self.mutations.append('unsupported top-level ' + type(node).__name__)
        self.var_nodes = {}
        variables = self.assignments.get('vars')
        if isinstance(variables, ast.Dict):
            self.var_nodes = {ast.literal_eval(k): v for k, v in zip(variables.keys, variables.values) if k is not None}

    def value(self, node, stack=()):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.List):
            return [self.value(x, stack) for x in node.elts]
        if isinstance(node, ast.Dict):
            return {self.value(k, stack): self.value(v, stack) for k, v in zip(node.keys, node.values)}
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return self.value(node.left, stack) + self.value(node.right, stack)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'Var' and len(node.args) == 1 and not node.keywords:
            name = self.value(node.args[0], stack)
            if name in stack or name not in self.var_nodes:
                raise ValueError('Unresolved Var: ' + str(name))
            return self.value(self.var_nodes[name], stack + (name,))
        raise ValueError('Unsupported expression: ' + ast.unparse(node))

    def rows(self):
        if self.mutations:
            raise ValueError('Additional assignments/mutations require review: ' + ', '.join(self.mutations))
        groups = []
        deps = self.assignments.get('deps')
        if deps is not None:
            groups.append(('deps', deps))
        deps_os = self.assignments.get('deps_os')
        if deps_os is not None:
            if not isinstance(deps_os, ast.Dict):
                raise ValueError('Nonliteral deps_os container')
            groups.extend(('deps_os:' + str(ast.literal_eval(k)), v) for k, v in zip(deps_os.keys, deps_os.values))
        if not groups:
            raise ValueError('No dependencies found')
        rows = []
        for group, node in groups:
            if not isinstance(node, ast.Dict):
                raise ValueError('Nonliteral dependency container: ' + group)
            for key, value in zip(node.keys, node.values):
                row = {'group': group, 'path': self.value(key)}
                try:
                    row['definition'] = self.value(value)
                except (ValueError, TypeError) as error:
                    row['unresolved'] = str(error)
                rows.append(row)
        return rows


def env():
    result = os.environ.copy()
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        result.pop(key, None)
    result.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    return result


def git_command(repo):
    command = ['git', '--no-optional-locks', '--no-replace-objects', '-c', 'core.fsmonitor=false',
               '-c', 'core.hooksPath=/dev/null', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-C', str(repo)]
    remotes = subprocess.check_output(command + ['remote'], env=env(), timeout=10).decode().splitlines()
    for remote in remotes:
        command.extend(['-c', 'remote.' + remote + '.promisor=false'])
    return command


def local_object(repo, revision):
    if not repo.is_dir():
        return {'repository': str(repo), 'status': 'directory_absent'}
    try:
        command = git_command(repo)
        top = subprocess.check_output(command + ['rev-parse', '--show-toplevel'], env=env(), timeout=15).decode().strip()
        if Path(top).resolve() != repo.resolve():
            return {'repository': str(repo), 'status': 'not_a_separate_git_root'}
        result = subprocess.run(command + ['cat-file', '-e', revision + '^{commit}'], env=env(), timeout=15,
                                capture_output=True)
        status = 'commit_present' if result.returncode == 0 else 'commit_unavailable_or_git_error'
        return {'repository': str(repo), 'status': status, 'exit_code': result.returncode}
    except (OSError, subprocess.SubprocessError) as error:
        return {'repository': str(repo), 'status': 'inspection_incomplete', 'reason': str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('original_project', type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve(strict=True)
    project = args.original_project.resolve(strict=True)
    command = git_command(workspace / 'src')
    head = subprocess.check_output(command + ['rev-parse', 'HEAD'], env=env(), timeout=30).decode().strip()
    if head != CHROMIUM:
        raise ValueError('Workspace is not at expected Chromium revision')
    text = subprocess.check_output(command + ['show', CHROMIUM + ':DEPS'], env=env(), timeout=90).decode()
    rows = Reader(text).rows()
    for row in rows:
        path = PurePosixPath(row['path'])
        if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != 'src':
            row['audit_status'] = 'unsupported_dependency_path'
            continue
        definition = row.get('definition')
        if 'unresolved' in row:
            row['audit_status'] = 'definition_unresolved'
            continue
        url = definition if isinstance(definition, str) else definition.get('url') if isinstance(definition, dict) else None
        if isinstance(definition, dict) and definition.get('dep_type') == 'cipd':
            row['audit_status'] = 'cipd_not_tested'
        elif isinstance(url, str) and re.search(r'@[0-9a-f]{40}$', url):
            revision = url.rsplit('@', 1)[1]
            row['revision'] = revision
            row['audit_status'] = 'local_git_objects_inspected'
            row['candidates'] = [local_object(project / name / str(path), revision) for name in ('chromium', 'chromium71')]
            print(str(path), revision, [x['status'] for x in row['candidates']], flush=True)
        elif definition is None:
            row['audit_status'] = 'disabled_definition'
        else:
            row['audit_status'] = 'non_sha_git_or_other_definition'
    report = {'chromium_revision': CHROMIUM, 'scope': 'primary DEPS only; conditions not evaluated; nested DEPS not read',
              'summary': dict(collections.Counter(row['audit_status'] for row in rows)), 'dependencies': rows}
    output = Path(tempfile.mkdtemp(prefix='deps-audit-', dir=workspace)) / 'report.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print('Report:', output)
    print(json.dumps(report['summary'], indent=2))
    reusable = [row['path'] for row in rows if any(x['status'] == 'commit_present' for x in row.get('candidates', []))]
    print('Dependencies with a local commit candidate:', len(reusable))
    print('Unresolved definitions:', [{'path': row['path'], 'reason': row['unresolved']} for row in rows if 'unresolved' in row])
    print('END: no clone, fetch, gclient, hook, patch or build executed. Conditions still require platform selection.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        print('FAILED / INCOMPLETE:', error)
        raise SystemExit(1)
