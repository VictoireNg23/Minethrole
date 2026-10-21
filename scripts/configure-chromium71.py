#!/usr/bin/env python3
"""Try GN generation in a NEW output directory using the authors' build arguments."""
import argparse
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
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    report = json.loads(args.tools_report.read_text())
    if report.get('status') != 'historical_tool_links_prepared':
        raise SystemExit('Tool integration not confirmed')
    src = workspace / 'src'
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
              'log': str(logs / 'gn.log'), 'patches': 'not applied by this script',
              'compilation': 'not run', 'purpose': 'unpatched build configuration readiness check'}
    print('NEW output directory:', output, flush=True)
    print('Command:', json.dumps(command), flush=True)
    with (logs / 'gn.log').open('w+') as log:
        try:
            process = subprocess.run(command, cwd=src, stdout=log, stderr=subprocess.STDOUT, timeout=180)
            result['exit_code'] = process.returncode
            result['status'] = 'gn_generation_passed_unpatched' if process.returncode == 0 else 'gn_generation_failed'
        except subprocess.TimeoutExpired:
            result['status'] = 'gn_generation_timeout'
        except OSError as error:
            result['error'] = str(error)
        log.seek(0)
        print(log.read()[-24000:], flush=True)
    (logs / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', logs / 'result.json')
    return 0 if result['status'] == 'gn_generation_passed_unpatched' else 1


if __name__ == '__main__':
    raise SystemExit(main())
