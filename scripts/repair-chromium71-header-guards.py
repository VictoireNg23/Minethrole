#!/usr/bin/env python3
"""Regenerate our recorded headers using original relative paths; optionally replace with backups."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile


def valid_guards(text):
    guards = re.findall(r'^#(?:ifndef|define)\s+(\S+)', text, re.M)
    return bool(guards) and all(re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', name) for name in guards)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('previous_report', type=Path)
    parser.add_argument('--replace-recorded-generated-headers', action='store_true', help='Replace only exact outputs recorded in previous report, preserving backups')
    args = parser.parse_args()
    root = args.workspace.resolve()
    previous = json.loads(args.previous_report.read_text())
    if previous.get('status') != 'original_version_headers_prepared':
        raise SystemExit('Expected original header generation report')
    tools = Path(json.loads((root / 'preparation.json').read_text())['tools']).resolve()
    stage = Path(tempfile.mkdtemp(prefix='header-guard-repair-', dir=root))
    result = {'status': 'incomplete', 'directory': str(stage), 'headers': [], 'build': 'not run'}
    expected = {'gpu_lists_version': 'src/gpu/config/gpu_lists_version.h', 'lastchange_skia': 'src/skia/ext/skia_commit_hash.h'}
    try:
        if {h['name'] for h in previous['headers']} != set(expected):
            raise ValueError('Expected exactly two known generated headers')
        for item in previous['headers']:
            relative = expected[item['name']]
            destination = root / relative
            if item.get('status') != 'generated_and_installed' or Path(item['destination']) != destination or destination.is_symlink() or destination.read_text() != item['content']:
                raise ValueError('Destination differs from our recorded output; preserve and inspect')
            output = stage / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            # Use environment launcher without with-tools.sh's workspace chdir.
            cmd = [str(tools / 'with-env.sh'), 'python', str(root / 'src/build/util/lastchange.py')]
            if item['name'] == 'gpu_lists_version':
                cmd += ['-m', 'GPU_LISTS_VERSION', '--revision-id-only', '-s', str(root / 'src')]
            else:
                cmd += ['-m', 'SKIA_COMMIT_HASH', '-s', str(root / 'src/third_party/skia')]
            cmd += ['--header', relative]
            process = subprocess.run(cmd, cwd=stage, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
            (stage / (item['name'] + '.log')).write_text(process.stdout)
            if process.returncode or not output.is_file() or not valid_guards(output.read_text()):
                raise RuntimeError('Header regeneration/guard validation failed: ' + process.stdout)
            # Compare actual version define independently of generated guard naming.
            macro = 'GPU_LISTS_VERSION' if item['name'] == 'gpu_lists_version' else 'SKIA_COMMIT_HASH'
            pattern = r'^#define ' + macro + r' .*$'
            if re.findall(pattern, item['content'], re.M) != re.findall(pattern, output.read_text(), re.M):
                raise ValueError('Version metadata changed; no replacement')
            backup = stage / (destination.name + '.before')
            backup.write_bytes(destination.read_bytes())
            result['headers'].append({'destination': str(destination), 'staged': str(output), 'backup': str(backup), 'content': output.read_text()})
        if args.replace_recorded_generated_headers:
            # Recheck all files immediately before replacements.
            for item in previous['headers']:
                destination = Path(item['destination'])
                if destination.is_symlink() or destination.read_text() != item['content']:
                    raise ValueError('Destination changed during preparation')
            for item in result['headers']:
                # Keep staged copy and backups for review; write only known generated outputs.
                Path(item['destination']).write_bytes(Path(item['staged']).read_bytes())
            result['status'] = 'recorded_header_guards_repaired'
        else:
            result['status'] = 'corrected_headers_prepared_no_replacement'
    except Exception as error:
        result['error'] = str(error)
    (stage / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', stage / 'result.json')
    return 0 if result['status'] != 'incomplete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
