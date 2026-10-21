#!/usr/bin/env python3
"""Download pinned Clang and amd64 sysroot into a new directory; never extract."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import tempfile
import urllib.request

CLANG = 'https://commondatastorage.googleapis.com/chromium-browser-clang/Linux_x64/clang-344066-1.tgz'
SYSROOT_SHA1 = 'e7c53f04bd88d29d075bfd1f62b073aeb69cbe09'
SYSROOT = 'https://commondatastorage.googleapis.com/chrome-linux-sysroot/toolchain/' + SYSROOT_SHA1 + '/debian_sid_amd64_sysroot.tar.xz'


def verify_sha1(actual, expected):
    if expected is not None and actual != expected:
        raise ValueError('SHA-1 mismatch; do not extract')


def fetch(url, path, expected=None):
    sha1, sha256 = hashlib.sha1(), hashlib.sha256()
    size = 0
    with urllib.request.urlopen(url, timeout=30) as response, path.open('xb') as output:
        if not response.geturl().startswith('https://'):
            raise ValueError('Non-HTTPS redirect refused')
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > 1024 ** 3:
                raise ValueError('Archive exceeds 1 GiB limit')
            output.write(chunk)
            sha1.update(chunk)
            sha256.update(chunk)
    verify_sha1(sha1.hexdigest(), expected)
    return {'bytes': size, 'sha1': sha1.hexdigest(), 'sha256': sha256.hexdigest(),
            'expected_sha1': expected, 'integrity': 'sha1_matches_historical_metadata' if expected else 'no_independent_expected_digest; HTTPS_versioned_artifact_only'}


def inspect(path):
    counts = Counter()
    unsafe = []
    examples = []
    with tarfile.open(path) as archive:
        for entry in archive:
            counts[str(entry.type)] += 1
            if len(examples) < 15:
                examples.append(entry.name)
            name = PurePosixPath(entry.name)
            if name.is_absolute() or '..' in name.parts:
                unsafe.append(entry.name)
    return {'member_types': dict(counts), 'first_members': examples, 'unsafe_member_names': unsafe[:20],
            'note': 'Manifest inspection only; link targets and extraction policy still require review'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    args = parser.parse_args()
    src = args.workspace.resolve() / 'src'
    clang_source = (src / 'tools/clang/scripts/update.py').read_text()
    if not re.search(r"^CLANG_REVISION\s*=\s*'344066'", clang_source, re.M) or not re.search(r'^CLANG_SUB_REVISION\s*=\s*1\s*$', clang_source, re.M):
        raise SystemExit('Clang metadata differs; inspect before downloading')
    metadata = json.loads((src / 'build/linux/sysroot_scripts/sysroots.json').read_text())['sid_amd64']
    if metadata['Sha1Sum'] != SYSROOT_SHA1 or metadata['Tarball'] != 'debian_sid_amd64_sysroot.tar.xz':
        raise SystemExit('Sysroot metadata differs')
    root = Path(tempfile.mkdtemp(prefix='minethrottle71-toolchain-download-'))
    print('NEW directory (retained):', root, flush=True)
    report = {'artifacts': [], 'extraction': 'not run', 'build': 'not run', 'chromium_modified': False}
    for name, url, expected in [('clang-344066-1.tgz', CLANG, None), ('debian_sid_amd64_sysroot.tar.xz', SYSROOT, SYSROOT_SHA1)]:
        item = {'name': name, 'url': url, 'path': str(root / name), 'status': 'incomplete'}
        print('Downloading:', url, flush=True)
        try:
            item.update(fetch(url, root / name, expected))
            item['manifest'] = inspect(root / name)
            item['status'] = 'downloaded_and_manifest_read'
        except Exception as error:
            item['error'] = str(error)
        report['artifacts'].append(item)
        (root / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(item, indent=2), flush=True)
    print('Report:', root / 'result.json')
    return 0 if all(item['status'] == 'downloaded_and_manifest_read' for item in report['artifacts']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
