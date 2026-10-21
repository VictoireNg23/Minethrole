#!/usr/bin/env python3
"""Check both original patches before applying them to isolated historical sources."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

PATCHES = [('v8.patch', 'src/v8', 'b5a5d900a5385d6429edefb11ece72bfa649ca47', '72c3adef6f566e7de6b6b7f0d1c6a12f0384098be3601fbcbe2272f1861ee563', []),
           ('content.patch', 'src', 'c2bec8045f7ad3ece1c5d80236183a21c1fac3f5', '7401d2c063f7b4f5b3239dd7b2eb61e3b005123dda6395d1a7e17626e5b06b22', ['--directory=content'])]


def git(repo, args):
    process = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', '-C', str(repo)] + args,
                             env=dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1'),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90)
    if process.returncode:
        raise RuntimeError('git %s\n%s' % (' '.join(args), process.stdout + process.stderr))
    return process.stdout.strip()


def affected_paths(data, prefix=''):
    paths = []
    for line in data.decode().splitlines():
        if line.startswith('+++ b/'):
            path = Path(prefix) / line[6:]
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('Unsafe patch path')
            paths.append(str(path))
    if not paths:
        raise ValueError('No affected paths')
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('gn_report', type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    if not (root / 'preparation.json').is_file():
        raise SystemExit('Expected isolated prepared workspace')
    if json.loads(args.gn_report.read_text()).get('status') != 'gn_generation_passed_unpatched':
        raise SystemExit('Successful unpatched GN report required')
    logs = Path(tempfile.mkdtemp(prefix='original-patches-', dir=root))
    result = {'status': 'incomplete', 'applied': [], 'compilation': 'not run'}
    try:
        for name, relative, revision, checksum, options in PATCHES:
            repo = root / relative
            patch = root / name
            data = patch.read_bytes()
            if hashlib.sha256(data).hexdigest() != checksum:
                raise ValueError('Original patch fingerprint differs: ' + name)
            if git(repo, ['rev-parse', 'HEAD']) != revision:
                raise ValueError('Historical revision differs: ' + relative)
            paths = affected_paths(data, 'content' if name == 'content.patch' else '')
            git(repo, ['diff', '--exit-code', 'HEAD', '--'] + paths)
            for path in paths:
                if (repo / path).is_symlink():
                    raise ValueError('Affected file is a symbolic link: ' + path)
            git(repo, ['apply', '--check'] + options + [str(patch)])
        result['preflight'] = 'both_original_patches_passed'
        for name, relative, revision, checksum, options in PATCHES:
            git(root / relative, ['apply'] + options + [str(root / name)])
            result['applied'].append(name)
            (logs / (name + '.diffstat')).write_text(git(root / relative, ['diff', '--stat']) + '\n')
        result['status'] = 'original_patches_applied_compilation_unvalidated'
    except Exception as error:
        result['error'] = str(error)
    (logs / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', logs / 'result.json')
    return 0 if len(result['applied']) == 2 else 1


if __name__ == '__main__':
    raise SystemExit(main())
