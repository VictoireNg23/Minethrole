#!/usr/bin/env python3
"""Apply the separate clone3 ENOSYS compatibility adaptation; never disable seccomp."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

SHA256 = 'e34f34c120ebc3dd332bbb5bbdabdeb9a99208b66154241bd4a04cd87dc05f03'
FILES = ['sandbox/linux/seccomp-bpf-helpers/baseline_policy.cc',
         'sandbox/linux/seccomp-bpf-helpers/baseline_policy_unittest.cc']


def git(src, *args):
    process = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(src)] + list(args),
                             env=dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1'),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
    if process.returncode:
        raise RuntimeError(process.stdout)
    return process.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('adaptation_patch', type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    if not (root / 'preparation.json').is_file():
        raise SystemExit('Expected isolated workspace')
    src = root / 'src'
    patch = args.adaptation_patch.resolve()
    if hashlib.sha256(patch.read_bytes()).hexdigest() != SHA256:
        raise SystemExit('Unexpected adaptation patch checksum')
    logs = Path(tempfile.mkdtemp(prefix='clone3-compatibility-', dir=root))
    report = {'status': 'incomplete', 'adaptation_patch_sha256': SHA256,
              'original_minethrottle_patches_modified': False, 'sandbox_disabled': False, 'build': 'not run'}
    try:
        if git(src, 'rev-parse', 'HEAD') != 'c2bec8045f7ad3ece1c5d80236183a21c1fac3f5':
            raise ValueError('Unexpected Chromium revision')
        git(src, 'diff', '--exit-code', 'HEAD', '--', *FILES)
        for filename in FILES:
            path = src / filename
            if path.is_symlink():
                raise ValueError('Refused symlink source: ' + filename)
            (logs / (path.name + '.before')).write_bytes(path.read_bytes())
        git(src, 'apply', '--check', str(patch))
        git(src, 'apply', str(patch))
        (logs / 'clone3.diff').write_text(git(src, 'diff', '--', *FILES) + '\n')
        report['status'] = 'clone3_enosys_adaptation_applied_rebuild_required'
    except Exception as error:
        report['error'] = str(error)
    (logs / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('Report:', logs / 'result.json')
    return 0 if report['status'] != 'incomplete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
