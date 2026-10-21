#!/usr/bin/env python3
"""Apply a separate Blink/Bison include adaptation; preserve original MineThrottle patches."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

PATCH_SHA256 = '0e9df1fc7f21ef392fef3dd1a27e603d2149d22eb57f501084a65acd34e3639f'


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
    v8 = root / 'src'
    if not (root / 'preparation.json').is_file():
        raise SystemExit('Expected isolated workspace')
    patch = args.adaptation_patch.resolve()
    if hashlib.sha256(patch.read_bytes()).hexdigest() != PATCH_SHA256:
        raise SystemExit('Adaptation patch checksum differs')
    logs = Path(tempfile.mkdtemp(prefix='bison-include-fix-', dir=root))
    result = {'status': 'incomplete', 'adaptation_patch_sha256': PATCH_SHA256,
              'original_patches_modified': False, 'compilation': 'not run'}
    try:
        if git(v8, 'rev-parse', 'HEAD') != 'c2bec8045f7ad3ece1c5d80236183a21c1fac3f5':
            raise ValueError('Unexpected historical Chromium HEAD')
        git(v8, 'diff', '--exit-code', 'HEAD', '--', 'third_party/blink/renderer/build/scripts/rule_bison.py')
        if (v8 / 'third_party/blink/renderer/build/scripts/rule_bison.py').is_symlink():
            raise ValueError('Refused symlink source')
        git(v8, 'apply', '--check', str(patch))
        (logs / 'rule_bison.py.before').write_bytes((v8 / 'third_party/blink/renderer/build/scripts/rule_bison.py').read_bytes())
        git(v8, 'apply', str(patch))
        result['status'] = 'bison_include_adaptation_applied_rebuild_required'
        (logs / 'rule_bison.diff').write_text(git(v8, 'diff', '--', 'third_party/blink/renderer/build/scripts/rule_bison.py') + '\n')
    except Exception as error:
        result['error'] = str(error)
    (logs / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', logs / 'result.json')
    return 0 if result['status'] != 'incomplete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
