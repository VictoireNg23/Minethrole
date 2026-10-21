#!/usr/bin/env python3
"""Generate missing GPU/Skia headers using original hook definitions, without replacements."""
import argparse
import ast
import json
from pathlib import Path
import subprocess
import tempfile


def selected_hooks(source):
    result = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'hooks' for t in node.targets):
            for entry in node.value.elts:
                try:
                    hook = ast.literal_eval(entry)
                except (ValueError, TypeError):
                    continue
                if hook.get('name') in ('gpu_lists_version', 'lastchange_skia'):
                    result[hook['name']] = hook['action']
    if len(result) != 2:
        raise ValueError('Both original header hooks required')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    if not (root / 'preparation.json').is_file():
        raise SystemExit('Expected isolated workspace')
    hooks = selected_hooks((root / 'src/DEPS').read_text())
    expected = {'gpu_lists_version': 'src/gpu/config/gpu_lists_version.h',
                'lastchange_skia': 'src/skia/ext/skia_commit_hash.h'}
    for name, action in hooks.items():
        if action[:2] != ['python', 'src/build/util/lastchange.py'] or '--header' not in action or action[action.index('--header') + 1] != expected[name]:
            raise SystemExit('Unexpected header hook action: ' + name)
    stage = Path(tempfile.mkdtemp(prefix='version-headers-', dir=root))
    report = {'status': 'incomplete', 'headers': [], 'build': 'not run', 'global_hooks': 'not run'}
    try:
        for name, action in hooks.items():
            destination = root / expected[name]
            if destination.is_symlink():
                raise ValueError('Refused symbolic link destination: ' + str(destination))
            if destination.exists():
                report['headers'].append({'name': name, 'status': 'existing_preserved', 'destination': str(destination)})
                continue
            output = stage / destination.name
            arguments = list(action[1:])
            arguments[arguments.index('--header') + 1] = str(output)
            if '-s' not in arguments:
                arguments += ['-s', str(root / 'src')]
            command = [str(root / 'with-tools.sh'), 'python'] + arguments
            process = subprocess.run(command, cwd=root, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, timeout=60)
            (stage / (name + '.log')).write_text(process.stdout)
            if process.returncode or not output.is_file():
                raise RuntimeError(name + ' generator failed: ' + process.stdout)
            with destination.open('xb') as target:
                target.write(output.read_bytes())
            report['headers'].append({'name': name, 'status': 'generated_and_installed',
                                      'destination': str(destination), 'content': output.read_text(), 'command': command})
        report['status'] = 'original_version_headers_prepared'
    except Exception as error:
        report['error'] = str(error)
    (stage / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('Report:', stage / 'result.json')
    return 0 if report['status'] == 'original_version_headers_prepared' else 1


if __name__ == '__main__':
    raise SystemExit(main())
