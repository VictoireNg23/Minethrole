#!/usr/bin/env python3
"""Try GN generation in a NEW output directory using the authors' build arguments."""
import argparse
import hashlib
import os
import json
from pathlib import Path
import subprocess
import tempfile

BUILD_ARGS = 'cc_wrapper="ccache" use_jumbo_build=true is_debug=false enable_nacl=false'


def gn_command(workspace, output):
    src = workspace / "src"
    return [str(workspace / "with-tools.sh"), str(src / "buildtools/linux64/gn"),
            "gen", str(output), "--root=" + str(src), "--args=" + BUILD_ARGS]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('tools_report', type=Path)
    parser.add_argument('--patch-report', type=Path, help='Require verified original patches and label generation as patched')
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    report = json.loads(args.tools_report.read_text())
    if report.get('status') != 'historical_tool_links_prepared':
        raise SystemExit('Tool integration not confirmed')
    src = workspace / 'src'
    patched = args.patch_report is not None
    if patched:
        patch_report = json.loads(args.patch_report.read_text())
        if patch_report.get('status') != 'original_patches_applied_compilation_unvalidated' or set(patch_report.get('applied', [])) != {'v8.patch', 'content.patch'}:
            raise SystemExit('Successful application of both original patches required')
        for name, relative, checksum, options in [
            ('v8.patch', 'v8', '72c3adef6f566e7de6b6b7f0d1c6a12f0384098be3601fbcbe2272f1861ee563', []),
            ('content.patch', '', '7401d2c063f7b4f5b3239dd7b2eb61e3b005123dda6395d1a7e17626e5b06b22', ['--directory=content'])]:
            patch = workspace / name
            if hashlib.sha256(patch.read_bytes()).hexdigest() != checksum:
                raise SystemExit('Original patch fingerprint changed: ' + name)
            check = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(src / relative), 'apply', '--reverse', '--check'] + options + [str(patch)],
                                   env=dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1'),
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
            if check.returncode:
                raise SystemExit('Applied patch check failed: ' + name + '\n' + check.stdout)
    for link in report['links']:
        destination = Path(link['destination'])
        if not destination.is_symlink() or destination.resolve() != Path(link['source']).resolve():
            raise SystemExit('Tool link changed: ' + str(destination))
    out = src / 'out'
    out.mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='MineThrottle71-config-', dir=out))
    logs = Path(tempfile.mkdtemp(prefix='gn-config-', dir=workspace))
    if not (src / '.gn').is_file():
        raise SystemExit('Missing src/.gn; inspect source checkout before configuring')
    command = gn_command(workspace, output)
    result = {'status': 'incomplete', 'command': command, 'output_directory': str(output),
              'log': str(logs / 'gn.log'), 'patches': 'original patches verified applied' if patched else 'not applied by this script',
              'compilation': 'not run', 'purpose': 'patched build configuration' if patched else 'unpatched build configuration readiness check'}
    print('NEW output directory:', output, flush=True)
    print('Command:', json.dumps(command), flush=True)
    with (logs / 'gn.log').open('w+') as log:
        try:
            process = subprocess.run(command, cwd=src, stdout=log, stderr=subprocess.STDOUT, timeout=180)
            result['exit_code'] = process.returncode
            result['status'] = ('gn_generation_passed_patched' if patched else 'gn_generation_passed_unpatched') if process.returncode == 0 else 'gn_generation_failed'
        except subprocess.TimeoutExpired:
            result['status'] = 'gn_generation_timeout'
        except OSError as error:
            result['error'] = str(error)
        log.seek(0)
        print(log.read()[-24000:], flush=True)
    (logs / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', logs / 'result.json')
    return 0 if result['status'] in ('gn_generation_passed_unpatched', 'gn_generation_passed_patched') else 1


if __name__ == '__main__':
    raise SystemExit(main())
