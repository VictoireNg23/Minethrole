#!/usr/bin/env python3
"""Inspect pinned Clang/sysroot downloader metadata without running it."""
import argparse
import json
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    if not (root / 'preparation.json').is_file():
        raise SystemExit('Expected isolated prepared workspace')
    src = root / 'src'
    for relative in ('tools/clang/scripts/update.py', 'build/linux/sysroot_scripts/install-sysroot.py', 'third_party/binutils/download.py'):
        path = src / relative
        print('\n===', relative, '===')
        lines = path.read_text().splitlines()
        selected = set()
        # Include headers/default versions and context for URL, extraction and replacement operations.
        selected.update(range(min(85, len(lines))))
        for i, line in enumerate(lines):
            if re.search(r'https?://|CLANG_REVISION|CLANG_SUB_REVISION|PACKAGE_VERSION|CDS_URL|rmtree|unlink|rename|def (Download|Update|Install|Get)|tarfile|extractall|sysroots.json', line):
                selected.update(range(max(0, i - 2), min(len(lines), i + 6)))
        previous = -2
        for i in sorted(selected):
            if i != previous + 1:
                print('...')
            print('%d: %s' % (i + 1, lines[i]))
            previous = i
    path = src / 'build/linux/sysroot_scripts/sysroots.json'
    print('\n=== sysroots.json amd64/x64 entries ===')
    if path.exists():
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            for key, value in data.items():
                if 'amd64' in key.lower() or 'x64' in key.lower():
                    print(json.dumps({key: value}, indent=2))
        else:
            print('Unexpected JSON shape; manual inspection required')
    else:
        print('File absent; inspect downloader metadata above')
    print('\nEND: read-only source inspection; no download, extraction, hook or build.')


if __name__ == '__main__':
    main()
