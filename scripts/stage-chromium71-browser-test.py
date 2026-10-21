#!/usr/bin/env python3
"""Stage a private non-root browser test, without launching Chromium or touching dataset."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tempfile

USER = 'minethrottle-test'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def runtime_entries(output):
    names = {'chrome', 'chrome_crashpad_handler', 'locales', 'swiftshader', 'resources'}
    return sorted((path for path in output.iterdir() if path.name in names or
                   (path.is_file() and path.suffix in ('.pak', '.bin', '.dat', '.so'))), key=lambda p: p.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--create-dedicated-user', action='store_true', help='Explicitly create minethrottle-test system account if absent')
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Staging requires root on the compute node; browser will run separately as a dedicated user')
    run = args.run.resolve(strict=True)
    initial = json.loads((run / 'manifest.json').read_text())
    build = json.loads((run / 'provenance/chrome-build-report.json').read_text())
    if build.get('status') != 'chrome_build_passed':
        raise SystemExit('Successful Chromium build required')
    command = build['command']
    output = Path(command[command.index('-C') + 1]).resolve(strict=True)
    if digest(output / 'chrome') != build['binary_sha256']:
        raise SystemExit('Chromium binary differs from recorded build')
    created = False
    try:
        account = pwd.getpwnam(USER)
        # Do not appropriate an existing account for experiments.
        raise SystemExit('Account already exists; inspect previous staging report instead of creating another environment')
    except KeyError:
        if not args.create_dedicated_user:
            raise SystemExit('Account absent; explicit --create-dedicated-user required')
    root = Path(tempfile.mkdtemp(prefix='minethrottle71-browser-test-'))
    print('NEW local staging directory (retained):', root, flush=True)
    record_file = tempfile.NamedTemporaryFile(prefix='browser-stage-', suffix='.json', dir=run / 'provenance', delete=False)
    record_file.close()
    report_path = Path(record_file.name)
    report = {'status': 'incomplete', 'directory': str(root), 'results_run': str(run), 'user': USER,
              'browser_started': False, 'dataset_execution': 'not run', 'shared_permissions_modified': False}
    try:
        subprocess.run(['/usr/sbin/useradd', '--system', '--no-create-home', '--home-dir', '/nonexistent',
                        '--shell', '/usr/sbin/nologin', '--user-group', USER], check=True, timeout=30)
        created = True
        account = pwd.getpwnam(USER)
        root.chmod(0o755)  # Only this new local directory, never an existing parent.
        bundle = root / 'browser'
        bundle.mkdir(mode=0o755)
        copied = []
        for source in runtime_entries(output):
            target = bundle / source.name
            if source.is_dir():
                shutil.copytree(source, target, symlinks=False)
            else:
                shutil.copyfile(source, target)
            copied.append(source.name)
        # Normalize permissions on the new copied bundle only; it stays root-owned.
        for directory, directories, files in os.walk(bundle):
            Path(directory).chmod(0o755)
            for name in files:
                path = Path(directory) / name
                path.chmod(0o755 if path.name in ('chrome', 'chrome_crashpad_handler') or path.suffix == '.so' else 0o644)
        if digest(bundle / 'chrome') != build['binary_sha256']:
            raise ValueError('Copied browser checksum differs')
        session = root / 'session'
        session.mkdir(mode=0o700)
        os.chown(session, account.pw_uid, account.pw_gid)
        for name in ('home', 'profile', 'raw'):
            path = session / name
            path.mkdir(mode=0o700)
            os.chown(path, account.pw_uid, account.pw_gid)
        report.update(status='nonroot_browser_test_staged_not_launched', uid=account.pw_uid, gid=account.pw_gid,
                      binary=str(bundle / 'chrome'), binary_sha256=build['binary_sha256'], copied_entries=copied,
                      session_directory=str(session), account_created=created)
    except Exception as error:
        report.update(error=str(error), account_created=created)
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('Report:', report_path)
    return 0 if report['status'] == 'nonroot_browser_test_staged_not_launched' else 1


if __name__ == '__main__':
    raise SystemExit(main())
