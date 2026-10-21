#!/usr/bin/env python3
"""Export pinned local depot_tools to a new isolated directory; no bootstrap."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import tarfile
import tempfile

REVISION = 'c6a8d114b060f5f68637e8897712a24252402377'


def git_environment():
    env = os.environ.copy()
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        env.pop(key, None)
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    return env


def export_snapshot(source, revision, parent):
    command = ['git', '--no-optional-locks', '--no-replace-objects', '-C', str(source),
               '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null',
               '-c', 'gc.auto=0', '-c', 'maintenance.auto=false']
    remotes = subprocess.check_output(command + ['remote'], env=git_environment(), timeout=15).decode().splitlines()
    for remote in remotes:
        command += ['-c', 'remote.' + remote + '.promisor=false']
    subprocess.run(command + ['cat-file', '-e', revision + '^{commit}'], env=git_environment(), check=True, timeout=90)
    root = Path(tempfile.mkdtemp(prefix='minethrottle71-tools-', dir=parent))
    print('New directory (retained even on failure):', root, flush=True)
    archive = root / 'depot_tools.tar'
    with archive.open('xb') as output:
        subprocess.run(command + ['archive', '--format=tar', revision], env=git_environment(), stdout=output, check=True, timeout=90)
    destination = root / 'depot_tools'
    destination.mkdir()
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        # Conservative: refuse all links/special entries rather than following
        # an unexpected historical archive entry while writing new files.
        for member in members:
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or '.git' in path.parts or not (member.isdir() or member.isfile()):
                raise ValueError('Unsupported/unsafe archive entry: ' + member.name)
        for member in members:
            path = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as data, path.open('xb') as output:
                    while True:
                        chunk = data.read(1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
                path.chmod(0o755 if member.mode & 0o111 else 0o644)
    provenance = {'source': str(source), 'revision': revision,
                  'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                  'git_metadata': 'snapshot only, no .git; automatic updates must remain disabled',
                  'bootstrap': 'not run', 'gclient': 'not run'}
    (root / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    return root


def write_launchers(root, source, python2, ninja):
    bindir = root / 'bin'
    bindir.mkdir()
    (bindir / 'python').write_text('#!/bin/sh\nexec ' + shlex.quote(str(python2)) + ' "$@"\n')
    (bindir / 'python').chmod(0o755)
    (bindir / 'python2').symlink_to(python2)
    (bindir / 'ninja').symlink_to(ninja)
    # Preserve user PATH except the original depot_tools directory. The new
    # wrappers take precedence; no system links or profile files are changed.
    inherited = [item for item in os.environ.get('PATH', '/usr/bin:/bin').split(os.pathsep)
                 if item and Path(item).resolve() != source]
    path = os.pathsep.join([str(bindir), str(root / 'depot_tools')] + inherited)
    environment = ('# Generated isolated environment; no bootstrap is run by sourcing this file.\n'
                   'export DEPOT_TOOLS_UPDATE=0\nexport GCLIENT_PY3=0\n'
                   'export PYTHONDONTWRITEBYTECODE=1\nexport PATH=' + shlex.quote(path) + '\n')
    (root / 'env.sh').write_text(environment)
    launcher = root / 'with-env.sh'
    launcher.write_text('#!/usr/bin/env bash\nset -euo pipefail\nsource ' + shlex.quote(str(root / 'env.sh')) + '\nexec "$@"\n')
    launcher.chmod(0o755)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('existing_depot_tools', type=Path)
    parser.add_argument('--temporary-parent', type=Path, default=Path('/tmp'))
    args = parser.parse_args()
    source = args.existing_depot_tools.resolve(strict=True)
    python2, ninja = Path('/usr/bin/python2'), Path('/usr/bin/ninja')
    for tool in (python2, ninja):
        if not os.access(tool, os.X_OK):
            raise ValueError('Required system executable missing: ' + str(tool))
    root = export_snapshot(source, REVISION, args.temporary_parent.resolve(strict=True))
    write_launchers(root, source, python2, ninja)
    # Only system binaries and our tiny wrapper run. Never run gclient, fetch,
    # vpython, gn, update_depot_tools or a script from the exported snapshot.
    subprocess.run([str(root / 'with-env.sh'), 'python', '--version'], check=True, timeout=15)
    subprocess.run([str(root / 'with-env.sh'), 'ninja', '--version'], check=True, timeout=15)
    print('Prepared snapshot:', root / 'depot_tools')
    print('Environment file:', root / 'env.sh')
    print('Launcher:', root / 'with-env.sh')
    print('PASS: snapshot and Python/Ninja launchers prepared. Historical depot_tools compatibility NOT validated.')
    print('No CIPD bootstrap, gclient, hooks, source checkout or build executed.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError) as error:
        print('FAILED / INCOMPLETE:', error, flush=True)
        raise SystemExit(1)
