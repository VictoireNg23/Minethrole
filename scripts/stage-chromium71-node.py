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
    parser.add_argument('--reuse-stage-report', type=Path, help='Reuse extraction stopped before links were created')
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
    reuse = args.reuse_stage_report is not None
    if reuse:
        previous = json.loads(args.reuse_stage_report.read_text())
        if previous.get('status') != 'incomplete' or previous.get('links') != [] or previous.get('error') != 'Expected WebUI bundler absent':
            raise SystemExit('Unexpected previous staging report; inspect manually')
        stage = Path(previous['directory']).resolve()
        if stage != args.reuse_stage_report.resolve().parent:
            raise SystemExit('Staging report directory differs')
    else:
        stage = Path(tempfile.mkdtemp(prefix='minethrottle71-node-stage-'))
    report = {'status': 'incomplete', 'directory': str(stage), 'artifacts': {}, 'links': [], 'build': 'not run'}
    logs = Path(tempfile.mkdtemp(prefix='node-stage-validation-', dir=stage))
    print('Staging directory (retained):', stage, flush=True)
    try:
        for name, (prefix, relative, metadata) in ARTIFACTS.items():
            if not reuse:
                report['artifacts'][name] = extract_plain(Path(artifacts[name]['path']), stage, prefix)
            else:
                report['artifacts'][name] = {'reused_from_report': str(args.reuse_stage_report.resolve())}
        process = subprocess.run([str(stage / 'node-linux-x64/bin/node'), '--version'], cwd=stage,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=15)
        report.update(node_version=process.stdout.strip(), node_exit_code=process.returncode)
        if process.returncode or process.stdout.strip() != 'v8.9.1':
            raise ValueError('Historical Node version check failed')
        package = stage / 'node_modules/polymer-bundler'
        metadata = json.loads((package / 'package.json').read_text())
        entry = metadata.get('bin', {}).get('polymer-bundler')
        if entry != 'lib/bin/polymer-bundler.js' or not (package / entry).is_file():
            raise ValueError('Expected package entry point absent or changed')
        # Chromium passes the extensionless name; test Node resolution unchanged.
        bundler = subprocess.run([str(stage / 'node-linux-x64/bin/node'), str(package / 'lib/bin/polymer-bundler'), '--help'],
                                 cwd=stage, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        (logs / 'bundler-help.log').write_text(bundler.stdout)
        report.update(bundler_version=metadata.get('version'), bundler_help_exit_code=bundler.returncode, bundler_help_output=bundler.stdout[-4000:])
        if bundler.returncode:
            raise ValueError('Original extensionless bundler invocation failed; no links installed')
        for name, (prefix, relative, metadata) in ARTIFACTS.items():
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(stage / prefix, target_is_directory=True)
            report['links'].append({'source': str(stage / prefix), 'destination': str(destination)})
        report['status'] = 'historical_node_and_webui_staged_and_linked'
    except Exception as error:
        report['error'] = str(error)
    (logs / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('Report:', logs / 'result.json')
    return 0 if report['status'] == 'historical_node_and_webui_staged_and_linked' else 1


if __name__ == '__main__':
    raise SystemExit(main())
