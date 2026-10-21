#!/usr/bin/env python3
"""Extract verified downloaded Clang in a new directory; inspect sysroot links only."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import shutil
import subprocess
import tarfile
import tempfile


def safe_name(name):
    normalized = posixpath.normpath(name)
    if normalized.startswith('/') or normalized == '..' or normalized.startswith('../'):
        raise ValueError('Unsafe archive path: ' + name)
    return normalized


def extract_clang(archive, destination):
    with tarfile.open(archive) as tar:
        members = {}
        for entry in tar:
            name = safe_name(entry.name)
            if name in members or name == '.' or not (entry.isfile() or entry.isdir() or entry.issym()):
                raise ValueError('Unsupported or duplicate Clang entry: ' + entry.name)
            members[name] = entry
        links = {}
        for name, entry in members.items():
            if any(str(parent) in members and members[str(parent)].issym() for parent in PurePosixPath(name).parents):
                raise ValueError('Symlink ancestor: ' + name)
            if entry.issym():
                if entry.linkname.startswith('/'):
                    raise ValueError('Absolute Clang link: ' + name)
                links[name] = safe_name(posixpath.join(posixpath.dirname(name), entry.linkname))
        for name, target in links.items():
            seen = {name}
            while target in links:
                if target in seen:
                    raise ValueError('Cyclic Clang link: ' + name)
                seen.add(target)
                target = links[target]
            if target not in members:
                raise ValueError('Missing Clang link target: ' + target)
        destination.mkdir()
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
        for name, entry in members.items():
            if entry.issym():
                (destination / name).symlink_to(entry.linkname)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('download_report', type=Path)
    args = parser.parse_args()
    report = json.loads(args.download_report.read_text())
    artifacts = {item['name']: item for item in report['artifacts']}
    root = Path(tempfile.mkdtemp(prefix='minethrottle71-clang-stage-'))
    result = {'status': 'incomplete', 'directory': str(root), 'sysroot_extracted': False, 'build': 'not run'}
    print('NEW directory (retained):', root, flush=True)
    try:
        for name in ('clang-344066-1.tgz', 'debian_sid_amd64_sysroot.tar.xz'):
            item = artifacts[name]
            if item['status'] != 'downloaded_and_manifest_read' or hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('Archive changed or incomplete: ' + name)
        extract_clang(Path(artifacts['clang-344066-1.tgz']['path']), root / 'clang')
        process = subprocess.run([str(root / 'clang/bin/clang'), '--version'], cwd=root,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=15)
        result.update(clang_version=process.stdout, clang_exit=process.returncode)
        with tarfile.open(artifacts['debian_sid_amd64_sysroot.tar.xz']['path']) as tar:
            links = [{'name': e.name, 'target': e.linkname} for e in tar if e.issym() or e.islnk()]
        result['sysroot_link_count'] = len(links)
        result['sysroot_absolute_links'] = [e for e in links if e['target'].startswith('/')][:25]
        result['sysroot_link_examples'] = links[:20]
        (root / 'sysroot-links.json').write_text(json.dumps(links, indent=2) + '\n')
        if process.returncode:
            raise RuntimeError('Historical Clang failed to start')
        result['status'] = 'clang_staged_version_checked_sysroot_links_inspected'
    except Exception as error:
        result['error'] = str(error)
    (root / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', root / 'result.json')
    return 0 if result['status'] != 'incomplete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
