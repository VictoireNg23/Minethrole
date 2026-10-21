#!/usr/bin/env python3
"""Stage and link historical Node/WebUI archives without overwriting existing files."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile

ARTIFACTS = {
    'node_linux64': ('node-linux-x64', 'src/third_party/node/linux/node-linux-x64', 'src/third_party/node/linux/node-linux-x64.tar.gz.sha1'),
    'webui_node_modules': ('node_modules', 'src/third_party/node/node_modules', 'src/third_party/node/node_modules.tar.gz.sha1'),
}


def extract_plain(archive, stage, expected_root):
    with tarfile.open(archive) as tar:
        entries = []
        names = set()
        expanded = 0
        for member in tar:
            name = PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts or not name.parts or name.parts[0] != expected_root:
                raise ValueError('Unexpected archive path: ' + member.name)
            if not (member.isfile() or member.isdir()) or str(name) in names:
                raise ValueError('Special entry or duplicate: ' + member.name)
            names.add(str(name))
            expanded += member.size if member.isfile() else 0
            if expanded > 512 * 1024 ** 2:
                raise ValueError('Expanded files exceed 512 MiB')
            entries.append(member)
        for member in entries:
            path = stage / member.name
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as source, path.open('xb') as output:
                    shutil.copyfileobj(source, output)
                path.chmod(member.mode & 0o777)
        return {'entries': len(entries), 'expanded_bytes': expanded}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('download_report', type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    if not (root / 'preparation.json').is_file():
        raise SystemExit('Expected isolated workspace')
    artifacts = {item['name']: item for item in json.loads(args.download_report.read_text())['artifacts']}
    for name, (prefix, relative, metadata) in ARTIFACTS.items():
        item = artifacts[name]
        expected = (root / metadata).read_text().strip()
        if item.get('status') != 'downloaded_sha1_verified_manifest_read' or hashlib.sha1(Path(item['path']).read_bytes()).hexdigest() != expected:
            raise SystemExit('Historical archive checksum mismatch: ' + name)
        destination = root / relative
        if destination.exists() or destination.is_symlink() or destination.parent.resolve() != destination.parent:
            raise SystemExit('Refused occupied or symlinked destination: ' + str(destination))
    stage = Path(tempfile.mkdtemp(prefix='minethrottle71-node-stage-'))
    report = {'status': 'incomplete', 'directory': str(stage), 'artifacts': {}, 'links': [], 'build': 'not run'}
    print('NEW directory (retained):', stage, flush=True)
    try:
        for name, (prefix, relative, metadata) in ARTIFACTS.items():
            report['artifacts'][name] = extract_plain(Path(artifacts[name]['path']), stage, prefix)
        process = subprocess.run([str(stage / 'node-linux-x64/bin/node'), '--version'], cwd=stage,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=15)
        report.update(node_version=process.stdout.strip(), node_exit_code=process.returncode)
        if process.returncode or process.stdout.strip() != 'v8.9.1':
            raise ValueError('Historical Node version check failed')
        if not (stage / 'node_modules/polymer-bundler/lib/bin/polymer-bundler').is_file():
            raise ValueError('Expected WebUI bundler absent')
        for name, (prefix, relative, metadata) in ARTIFACTS.items():
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(stage / prefix, target_is_directory=True)
            report['links'].append({'source': str(stage / prefix), 'destination': str(destination)})
        report['status'] = 'historical_node_and_webui_staged_and_linked'
    except Exception as error:
        report['error'] = str(error)
    (stage / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('Report:', stage / 'result.json')
    return 0 if report['status'] == 'historical_node_and_webui_staged_and_linked' else 1


if __name__ == '__main__':
    raise SystemExit(main())
