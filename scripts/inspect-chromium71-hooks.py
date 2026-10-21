#!/usr/bin/env python3
"""Inspect historical hook definitions and tool files without executing them."""
import argparse
import ast
import json
from pathlib import Path
import subprocess
import os


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('sync_report', type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    report = json.loads(args.sync_report.read_text())
    if report.get('status') != 'sync_exit_zero_primary_heads_verified_nohooks' or report.get('process', {}).get('underlying_exit_code') != 0:
        raise SystemExit('Refused: successful nohooks sync report required')
    src = root / 'src'
    for relative in ('DEPS', 'v8/DEPS'):
        print('\n=== Hook source:', relative, '===')
        source = (src / relative).read_text()
        tree = ast.parse(source)
        found = False
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ('hooks', 'pre_deps_hooks', 'hooks_os') for t in node.targets):
                found = True
                segment = ast.get_source_segment(source, node)
                print(segment[:48000])
                if len(segment) > 48000:
                    print('TRUNCATED; inspect file before proceeding')
        if not found:
            print('No top-level hook assignment found')
    print('\n=== Tool files: existence only; no execution ===')
    for relative in ('build/linux/debian_sid_amd64-sysroot', 'build/linux/debian_stretch_amd64-sysroot',
                     'third_party/llvm-build/Release+Asserts/bin/clang', 'buildtools/linux64/gn',
                     'third_party/node/linux/node-linux-x64/bin/node', 'build/install-build-deps.sh',
                     'build/linux/sysroot_scripts/install-sysroot.py', 'tools/clang/scripts/update.py'):
        path = src / relative
        print(relative, 'exists=' + str(path.exists()), 'symlink=' + str(path.is_symlink()))
    print('\n=== Local disk space ===')
    st = os.statvfs(root)
    print('Available bytes:', st.f_bavail * st.f_frsize)
    print('\n=== System development package states (no installation) ===')
    packages = ['libgtk-3-dev', 'libnss3-dev', 'libasound2-dev', 'libcups2-dev', 'libdbus-1-dev',
                'libx11-dev', 'libxss-dev', 'libxtst-dev', 'libpci-dev', 'libglib2.0-dev']
    try:
        result = subprocess.run(['dpkg-query', '-W', '-f=${Package} ${db:Status-Abbrev}\n'] + packages,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        print(result.stdout)
        print('dpkg-query exit:', result.returncode, '(missing packages may yield nonzero)')
    except (OSError, subprocess.TimeoutExpired) as error:
        print('Observation unavailable:', error)
    print('END: no hooks, network, installation, patch application or build executed.')


if __name__ == '__main__':
    main()
