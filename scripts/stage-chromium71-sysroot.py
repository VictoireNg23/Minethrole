#!/usr/bin/env python3
"""Extract the SHA-1 pinned amd64 sysroot into a NEW directory only."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import shutil
import tarfile
import tempfile

EXPECTED = 'e7c53f04bd88d29d075bfd1f62b073aeb69cbe09'


def safe_name(name):
    normalized = posixpath.normpath(name)
    if normalized.startswith('/') or normalized == '..' or normalized.startswith('../'):
        raise ValueError('Path leaves sysroot: ' + name)
    return normalized


def extract(archive, destination):
    with tarfile.open(archive) as tar:
        members = {}
        expanded = 0
        for entry in tar:
            name = safe_name(entry.name)
            if name == '.' and entry.isdir():
                continue
            if name == '.' or name in members or not (entry.isdir() or entry.isfile() or entry.issym()):
                raise ValueError('Unsupported/duplicate entry: ' + entry.name)
            expanded += entry.size if entry.isfile() else 0
            if expanded > 4 * 1024 ** 3:
                raise ValueError('Expanded files exceed 4 GiB limit')
            members[name] = entry
        links = set(name for name, entry in members.items() if entry.issym())
        for name, entry in members.items():
            if any(str(parent) in links for parent in PurePosixPath(name).parents):
                raise ValueError('Entry below a symbolic link: ' + name)
            if entry.issym():
                if entry.linkname.startswith('/'):
                    raise ValueError('Absolute symbolic link: ' + name)
                safe_name(posixpath.join(posixpath.dirname(name), entry.linkname))
                # Reject traversal through intermediate symlinks in a target;
                # lexical normalization alone would not model that traversal.
                current = []
                for part in (PurePosixPath(name).parent / entry.linkname).parts:
                    if part == '.':
                        continue
                    if part == '..':
                        if current:
                            current.pop()
                    else:
                        current.append(part)
                    prefix = '/'.join(current)
                    if prefix in links and prefix != safe_name(posixpath.join(posixpath.dirname(name), entry.linkname)):
                        raise ValueError('Symbolic link target traverses another link: ' + name)
        destination.mkdir()  # Refuses any pre-existing extraction directory.
        for name, entry in members.items():
            target = destination / name
            if entry.issym():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if entry.isdir():
                target.mkdir(exist_ok=True)
            else:
                with tar.extractfile(entry) as source, target.open('xb') as output:
                    shutil.copyfileobj(source, output)
                target.chmod(entry.mode & 0o777)
        for name in sorted(links):
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(members[name].linkname)
        return {'entries': len(members), 'symbolic_links': len(links), 'expanded_file_bytes': expanded}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('download_report', type=Path)
    args = parser.parse_args()
    download = json.loads(args.download_report.read_text())
    item = next(i for i in download['artifacts'] if i['name'] == 'debian_sid_amd64_sysroot.tar.xz')
    archive = Path(item['path'])
    if item['status'] != 'downloaded_and_manifest_read' or hashlib.sha1(archive.read_bytes()).hexdigest() != EXPECTED:
        raise SystemExit('Refused: sysroot incomplete or historical SHA-1 mismatch')
    root = Path(tempfile.mkdtemp(prefix='minethrottle71-sysroot-stage-'))
    result = {'status': 'incomplete', 'directory': str(root), 'expected_sha1': EXPECTED,
              'chromium_modified': False, 'build': 'not run'}
    print('NEW directory (retained):', root, flush=True)
    try:
        destination = root / 'debian_sid_amd64-sysroot'
        result.update(extract(archive, destination))
        result['sysroot'] = str(destination)
        result['status'] = 'historical_sysroot_extracted'
    except Exception as error:
        result['error'] = str(error)
    (root / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', root / 'result.json')
    return 0 if result['status'] == 'historical_sysroot_extracted' else 1


if __name__ == '__main__':
    raise SystemExit(main())
