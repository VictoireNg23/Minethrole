#!/usr/bin/env python3
"""Check original patch contexts on local historical blobs, never on worktrees.

Creates a NEW diagnostic directory and leaves it in place. No fetch, checkout,
patch application, source installation or compilation. Requires Python 3 + Git.
"""
import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile

CHROMIUM = 'c2bec8045f7ad3ece1c5d80236183a21c1fac3f5'
V8 = 'b5a5d900a5385d6429edefb11ece72bfa649ca47'
PATCHES = {
    'v8.patch': '72c3adef6f566e7de6b6b7f0d1c6a12f0384098be3601fbcbe2272f1861ee563',
    'content.patch': '7401d2c063f7b4f5b3239dd7b2eb61e3b005123dda6395d1a7e17626e5b06b22',
}


def environment():
    result = os.environ.copy()
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY',
                 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        result.pop(name, None)
    result.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1',
                  GIT_TERMINAL_PROMPT='0', LC_ALL='C')
    return result


def git_command(repo):
    command = ['git', '--no-optional-locks', '--no-replace-objects', '-C', str(repo),
               '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null',
               '-c', 'gc.auto=0', '-c', 'maintenance.auto=false']
    remotes = subprocess.run(command + ['remote'], env=environment(),
                             capture_output=True, check=True, timeout=15).stdout.decode().splitlines()
    for remote in remotes:
        command.extend(['-c', 'remote.' + remote + '.promisor=false'])
    return command


def touched_paths(patch):
    paths = re.findall(rb'^diff --git a/([^\n ]+) b/([^\n ]+)$', patch, re.M)
    if not paths:
        raise ValueError('No supported file headers in patch')
    result = []
    for before, after in paths:
        if before != after:
            raise ValueError('Renames are outside this diagnostic')
        path = PurePosixPath(before.decode('utf-8'))
        if path.is_absolute() or '..' in path.parts or not path.parts or '.git' in path.parts:
            raise ValueError('Unsafe patch path')
        result.append(path)
    return result


def extract_and_check(repo, revision, prefix, patch, destination, timeout):
    """destination must be a new directory beneath a new diagnostic root."""
    destination.mkdir(exist_ok=False)
    command = git_command(repo)
    subprocess.run(command + ['cat-file', '-e', revision + '^{commit}'],
                   env=environment(), check=True, timeout=timeout)
    for path in touched_paths(patch):
        output = destination.joinpath(*path.parts)
        output.parent.mkdir(parents=True, exist_ok=True)
        spec = revision + ':' + prefix + str(path)
        print('Extracting local blob:', spec, flush=True)
        # Git writes only this new file. Never materialize a symlink from Git.
        with output.open('xb') as stream:
            subprocess.run(command + ['show', spec], stdout=stream,
                           env=environment(), check=True, timeout=timeout)
    patch_copy = destination.parent / (destination.name + '.original.patch')
    with patch_copy.open('xb') as stream:
        stream.write(patch)
    env = environment()
    env['GIT_CEILING_DIRECTORIES'] = str(destination.parent)
    completed = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null',
                                'apply', '--check', '--verbose', str(patch_copy)],
                               cwd=destination, env=env, timeout=timeout)
    if completed.returncode != 0:
        raise RuntimeError('Patch context check FAILED: ' + destination.name)
    print('PASS context only:', destination.name, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path, help='Existing MineThrottle directory')
    parser.add_argument('--sources', choices=['chromium', 'chromium71'], default='chromium')
    parser.add_argument('--temporary-parent', type=Path, default=Path('/tmp'),
                        help='Existing writable directory; no existing files removed')
    parser.add_argument('--timeout', type=int, default=90, help='Seconds per Git read/check')
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error('--timeout must be positive')
    project = args.project.resolve(strict=True)
    source = project / args.sources / 'src'
    originals = {}
    # Verify both original patches before creating any export directory.
    for name, expected in PATCHES.items():
        patch = (project / 'patches' / name).read_bytes()
        if hashlib.sha256(patch).hexdigest() != expected:
            raise ValueError('Original patch fingerprint differs: ' + name + '; stop, no overwrite attempted')
        originals[name] = patch
    if not source.is_dir() or not (source / 'v8').is_dir():
        raise ValueError('Expected existing Chromium and V8 source directories')
    command = git_command(source)
    deps = subprocess.run(command + ['show', CHROMIUM + ':DEPS'], env=environment(),
                          capture_output=True, check=True, timeout=args.timeout).stdout
    pattern = rb'''["']v8_revision["']\s*:\s*["']([0-9a-f]{40})["']'''
    match = re.search(pattern, deps)
    if not match or match.group(1).decode() != V8:
        raise ValueError('Historical DEPS does not confirm expected V8; stop')
    root = Path(tempfile.mkdtemp(prefix='minethrottle71-patchcheck-', dir=args.temporary_parent))
    print('New diagnostic directory (retained):', root, flush=True)
    for name, repo, revision, prefix in [
            ('v8', source / 'v8', V8, ''),
            ('content', source, CHROMIUM, 'content/')]:
        extract_and_check(repo, revision, prefix, originals[name + '.patch'], root / name, args.timeout)
    print('PASS: both original patches match the exported historical file contexts.')
    print('No patch applied. This does NOT validate C++ compilation or runtime behavior.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print('FAILED / INCOMPLETE:', error, flush=True)
        raise SystemExit(1)
