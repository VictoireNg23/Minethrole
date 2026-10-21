#!/usr/bin/env python3
"""Prepare new historical Chromium/V8 checkouts using borrowed local objects.

No source fetch, gclient sync, hooks, patch application or build. The new clones
remain dependent on the original object stores, which must be retained.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

CHROMIUM = 'c2bec8045f7ad3ece1c5d80236183a21c1fac3f5'
V8 = 'b5a5d900a5385d6429edefb11ece72bfa649ca47'
TOOLS = 'c6a8d114b060f5f68637e8897712a24252402377'
PATCH_HASHES = {'v8.patch': '72c3adef6f566e7de6b6b7f0d1c6a12f0384098be3601fbcbe2272f1861ee563',
                'content.patch': '7401d2c063f7b4f5b3239dd7b2eb61e3b005123dda6395d1a7e17626e5b06b22'}
OPTIONS = ['-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
           '-c', 'gc.auto=0', '-c', 'maintenance.auto=false']


def environment():
    env = os.environ.copy()
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        env.pop(name, None)
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    return env


def run(args, timeout=900, capture=False):
    return subprocess.run(args, env=environment(), check=True, timeout=timeout,
                          stdout=subprocess.PIPE if capture else None,
                          text=True)


def verify_source(source, revision):
    command = ['git', '--no-optional-locks', '--no-replace-objects', *OPTIONS, '-C', str(source)]
    # Disable any source promisor remotes for local object checks.
    for remote in run(command + ['remote'], timeout=15, capture=True).stdout.splitlines():
        command += ['-c', 'remote.' + remote + '.promisor=false']
    top = run(command + ['rev-parse', '--show-toplevel'], timeout=30, capture=True).stdout.strip()
    if Path(top).resolve() != source:
        raise ValueError('Not a separate source repository: ' + str(source))
    run(command + ['cat-file', '-e', revision + '^{commit}'], timeout=90)


def clone_local(source, destination, revision, remote):
    """Never changes source or populates a nonempty destination."""
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError('Destination already contains files: ' + str(destination))
    print('Creating local shared clone:', source, '->', destination, flush=True)
    run(['git', *OPTIONS, 'clone', '--local', '--shared', '--no-checkout', '--no-tags',
         '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
         '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-c', 'core.autocrlf=false', '-c', 'submodule.recurse=false',
         str(source), str(destination)])
    git = ['git', *OPTIONS, '-C', str(destination)]
    # Only the newly created clone is checked out; no force or clean command.
    run(git + ['checkout', '--no-recurse-submodules', '--detach', revision])
    actual = run(git + ['rev-parse', 'HEAD'], timeout=30, capture=True).stdout.strip()
    if actual != revision:
        raise ValueError('Unexpected checkout revision: ' + actual)
    run(git + ['remote', 'set-url', 'origin', remote], timeout=30)
    alternates = destination / '.git/objects/info/alternates'
    if not alternates.is_file():
        raise ValueError('Expected borrowed object store metadata missing')
    return {'source': str(source), 'destination': str(destination), 'revision': actual,
            'borrowed_object_stores': alternates.read_text().splitlines()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--tools-root', required=True, type=Path)
    parser.add_argument('--temporary-parent', type=Path, default=Path('/tmp'))
    args = parser.parse_args()
    project = args.project.resolve(strict=True)
    tools = args.tools_root.resolve(strict=True)
    parent = args.temporary_parent.resolve(strict=True)
    if json.loads((tools / 'provenance.json').read_text())['revision'] != TOOLS:
        raise ValueError('Unexpected historical tools revision')
    if not os.access(tools / 'with-env.sh', os.X_OK):
        raise ValueError('Historical tools launcher unavailable')
    patches = {}
    for name, expected in PATCH_HASHES.items():
        patches[name] = (project / 'patches' / name).read_bytes()
        if hashlib.sha256(patches[name]).hexdigest() != expected:
            raise ValueError('Original patch fingerprint differs: ' + name)
    source = (project / 'chromium/src').resolve(strict=True)
    v8_source = (source / 'v8').resolve(strict=True)
    verify_source(source, CHROMIUM)
    verify_source(v8_source, V8)
    free = shutil.disk_usage(parent).free
    print('Available bytes on destination filesystem:', free, flush=True)
    if free < 20 * 1024 ** 3:
        raise ValueError('Less than 20 GiB free for this initial checkout step; stopping before creation')
    root = Path(tempfile.mkdtemp(prefix='minethrottle71-work-', dir=parent))
    print('NEW WORKSPACE (retained on failure):', root, flush=True)
    records = []
    manifest = {'chromium': CHROMIUM, 'v8': V8, 'tools': str(tools),
                'clones': records, 'status': 'preparation_incomplete',
                'source_fetch': 'not run', 'dependency_sync': 'not run',
                'patch_application': 'not run', 'build': 'not run'}
    report = root / 'preparation.json'
    report.write_text(json.dumps(manifest, indent=2) + '\n')
    records.append(clone_local(source, root / 'src', CHROMIUM, 'https://chromium.googlesource.com/chromium/src.git'))
    report.write_text(json.dumps(manifest, indent=2) + '\n')
    records.append(clone_local(v8_source, root / 'src/v8', V8, 'https://chromium.googlesource.com/v8/v8.git'))
    report.write_text(json.dumps(manifest, indent=2) + '\n')
    for name, patch in patches.items():
        patch_file = root / name
        patch_file.write_bytes(patch)
        destination = root / ('src/v8' if name == 'v8.patch' else 'src')
        command = ['git', *OPTIONS, '-C', str(destination), 'apply', '--check']
        if name == 'content.patch':
            command += ['--directory=content']
        print('Checking original patch context:', name, flush=True)
        run(command + [str(patch_file)], timeout=90)
    # An unmanaged, exactly pinned solution is prepared as data only. Never
    # execute .gclient nor gclient during this preparation step.
    solution = [{'name': 'src', 'url': 'https://chromium.googlesource.com/chromium/src.git',
                 'managed': False, 'custom_deps': {}, 'custom_vars': {}}]
    (root / '.gclient').write_text('solutions = ' + repr(solution) + '\n')
    launcher = root / 'with-tools.sh'
    launcher.write_text('#!/usr/bin/env bash\nset -euo pipefail\ncd ' + shlex.quote(str(root)) +
                        '\nexec ' + shlex.quote(str(tools / 'with-env.sh')) + ' "$@"\n')
    launcher.chmod(0o755)
    manifest['status'] = 'initial_checkouts_prepared_context_checks_passed'
    report.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))
    print('PASS: initial historical checkouts only; dependencies and compiler toolchain are NOT ready.')
    print('Retain original object stores and tools directory. No patch applied, sync, hooks or build run.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('FAILED / INCOMPLETE:', error, flush=True)
        raise SystemExit(1)
