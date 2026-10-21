#!/usr/bin/env python3
"""Link staged historical tools into the isolated workspace without replacements."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile


def link_new(source, destination):
    if destination.is_symlink():
        if destination.resolve() == source.resolve():
            return 'existing_matching_link'
        raise ValueError('Refused occupied symbolic link: ' + str(destination))
    if destination.exists():
        raise ValueError('Refused occupied destination: ' + str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(source, target_is_directory=source.is_dir())
    return 'created'


def load(path, status):
    data = json.loads(path.read_text())
    if data.get('status') != status:
        raise ValueError('Unexpected report status: ' + str(path))
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('gn_report', type=Path)
    parser.add_argument('clang_report', type=Path)
    parser.add_argument('sysroot_report', type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    if not (root / 'preparation.json').is_file():
        raise SystemExit('Expected isolated prepared workspace')
    gn = load(args.gn_report, 'historical_gn_verified_and_version_checked')
    clang = load(args.clang_report, 'clang_staged_version_checked_sysroot_links_inspected')
    sysroot = load(args.sysroot_report, 'historical_sysroot_extracted')
    gn_path = Path(gn['directory']).resolve() / 'gn'
    clang_path = Path(clang['directory']).resolve() / 'clang'
    sysroot_path = Path(sysroot['sysroot']).resolve()
    expected_gn = (root / 'src/buildtools/linux64/gn.sha1').read_text().strip()
    if hashlib.sha1(gn_path.read_bytes()).hexdigest() != expected_gn:
        raise SystemExit('GN checksum changed')
    if clang.get('clang_exit') != 0 or not (clang_path / 'bin/clang').is_file():
        raise SystemExit('Clang not ready')
    if sysroot.get('expected_sha1') != 'e7c53f04bd88d29d075bfd1f62b073aeb69cbe09' or not (sysroot_path / 'usr/include').is_dir():
        raise SystemExit('Sysroot not ready')
    pairs = [(gn_path, root / 'src/buildtools/linux64/gn'),
             (clang_path, root / 'src/third_party/llvm-build/Release+Asserts'),
             (sysroot_path, root / 'src/build/linux/debian_sid_amd64-sysroot')]
    # Check every destination before making any link.
    for source, destination in pairs:
        if source == destination.resolve() and destination.is_symlink():
            continue
        if destination.exists() or destination.is_symlink():
            raise SystemExit('Refused occupied destination: ' + str(destination))
        if destination.parent.resolve() != destination.parent:
            raise SystemExit('Refused symlink in destination parent: ' + str(destination))
    logs = Path(tempfile.mkdtemp(prefix='tools-link-', dir=root))
    result = {'status': 'incomplete', 'links': [], 'hooks': 'not run', 'build': 'not run'}
    try:
        for source, destination in pairs:
            action = link_new(source, destination)
            result['links'].append({'source': str(source), 'destination': str(destination), 'action': action})
        result['status'] = 'historical_tool_links_prepared'
    except (OSError, ValueError) as error:
        result['error'] = str(error)
    (logs / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', logs / 'result.json')
    return 0 if result['status'] == 'historical_tool_links_prepared' else 1


if __name__ == '__main__':
    raise SystemExit(main())
