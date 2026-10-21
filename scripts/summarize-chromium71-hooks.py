#!/usr/bin/env python3
"""Print compact hook definitions using AST only; execute no DEPS code."""
import argparse
import ast
import json
from pathlib import Path


def value(node, source):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return {'expression': ast.get_source_segment(source, node)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    if not (root / 'preparation.json').is_file():
        raise SystemExit('Expected prepared isolated workspace')
    for relative in ('src/DEPS', 'src/v8/DEPS'):
        source = (root / relative).read_text()
        tree = ast.parse(source)
        print('\n===', relative, '===')
        for assignment in tree.body:
            if not isinstance(assignment, ast.Assign):
                continue
            names = [n.id for n in assignment.targets if isinstance(n, ast.Name)]
            if not set(names).intersection({'hooks', 'pre_deps_hooks', 'hooks_os'}):
                continue
            print('Assignment:', ', '.join(names))
            for node in ast.walk(assignment.value):
                if not isinstance(node, ast.Dict):
                    continue
                fields = {k.value: v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant) and isinstance(k.value, str)}
                if 'action' in fields:
                    print(json.dumps({key: value(fields[key], source) for key in ('name', 'condition', 'action') if key in fields}, ensure_ascii=False))
    print('\nEND: definitions only; no hooks, downloads, installation or build executed.')


if __name__ == '__main__':
    main()
