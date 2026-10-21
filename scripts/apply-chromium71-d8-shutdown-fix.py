#!/usr/bin/env python3
"""Apply a separate d8 shutdown adaptation; preserve original MineThrottle patches."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

PATCH_SHA256 = '52b887813a9351dca6e606e6732686f4ca8f7ef775a25b920f2ffea3e53d9da4'


def git(repo, *args):
    result = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(repo)] + list(args),
                            env=dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1'),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError(result.stdout)
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('adaptation_patch', type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    v8 = root / 'src/v8'
    if not (root / 'preparation.json').is_file():
        raise SystemExit('Expected isolated workspace')
    patch = args.adaptation_patch.resolve()
    if hashlib.sha256(patch.read_bytes()).hexdigest() != PATCH_SHA256:
        raise SystemExit('Adaptation patch checksum differs')
    logs = Path(tempfile.mkdtemp(prefix='d8-shutdown-fix-', dir=root))
    result = {'status': 'incomplete', 'adaptation_patch_sha256': PATCH_SHA256,
              'original_patches_modified': False, 'compilation': 'not run'}
    try:
        if git(v8, 'rev-parse', 'HEAD') != 'b5a5d900a5385d6429edefb11ece72bfa649ca47':
            raise ValueError('Unexpected historical V8 HEAD')
        git(v8, 'diff', '--exit-code', 'HEAD', '--', 'src/d8.cc')
        if (v8 / 'src/d8.cc').is_symlink():
            raise ValueError('Refused symlink source')
        git(v8, 'apply', '--check', str(patch))
        (logs / 'd8.cc.before').write_bytes((v8 / 'src/d8.cc').read_bytes())
        git(v8, 'apply', str(patch))
        result['status'] = 'd8_shutdown_adaptation_applied_rebuild_required'
        (logs / 'd8.diff').write_text(git(v8, 'diff', '--', 'src/d8.cc') + '\n')
    except Exception as error:
        result['error'] = str(error)
    (logs / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', logs / 'result.json')
    return 0 if result['status'] != 'incomplete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
