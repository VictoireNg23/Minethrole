#!/usr/bin/env python3
"""Check compiled Chromium dependencies and --version only; open no browser page."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('build_report', type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    build = json.loads(args.build_report.read_text())
    if build.get('status') != 'chrome_build_passed' or build.get('exit_code') != 0:
        raise SystemExit('Successful chrome build required')
    command = build['command']
    output = Path(command[command.index('-C') + 1]).resolve()
    if not (root / 'preparation.json').is_file() or output.parent != root / 'src/out':
        raise SystemExit('Unexpected isolated build path')
    binary = output / 'chrome'
    digest = hashlib.sha256()
    with binary.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != build.get('binary_sha256'):
        raise SystemExit('Binary differs from successful build report')
    stage = Path(tempfile.mkdtemp(prefix='chrome-runtime-check-', dir=root))
    result = {'status': 'incomplete', 'binary_sha256': digest.hexdigest(),
              'browser_page': 'not opened', 'wasm_execution': 'not run', 'sandbox_disabled': False}
    try:
        libraries = subprocess.run(['/usr/bin/ldd', str(binary)], cwd=stage, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, timeout=30)
        (stage / 'ldd.log').write_text(libraries.stdout)
        result['ldd_exit_code'] = libraries.returncode
        result['missing_libraries'] = [line.strip() for line in libraries.stdout.splitlines() if 'not found' in line]
        if libraries.returncode or result['missing_libraries']:
            raise RuntimeError('Shared library check failed; inspect ldd.log before launching')
        version = subprocess.run([str(binary), '--version'], cwd=stage, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, timeout=15)
        (stage / 'version.log').write_text(version.stdout)
        result.update(version_exit_code=version.returncode, version_output=version.stdout.strip())
        if version.returncode:
            raise RuntimeError('chrome --version failed')
        result['status'] = 'chrome_dependencies_and_version_passed'
    except Exception as error:
        result['error'] = str(error)
    (stage / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', stage / 'result.json')
    return 0 if result['status'] == 'chrome_dependencies_and_version_passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
