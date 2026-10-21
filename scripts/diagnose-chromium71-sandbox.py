#!/usr/bin/env python3
"""Inspect sandbox prerequisites; open no page and change no file permissions."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess


def run(command):
    print('\nCommand:', command, flush=True)
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, timeout=15)
        print(result.stdout[:10000])
        print('exit:', result.returncode)
    except (OSError, subprocess.TimeoutExpired) as error:
        print('Observation unavailable:', error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build_directory', type=Path)
    args = parser.parse_args()
    directory = args.build_directory.resolve()
    print('Effective UID:', os.geteuid())
    for path in ('/proc/sys/kernel/unprivileged_userns_clone', '/proc/sys/user/max_user_namespaces',
                 '/proc/sys/kernel/apparmor_restrict_unprivileged_userns'):
        try:
            print(path + ':', Path(path).read_text().strip())
        except OSError as error:
            print(path + ': unavailable:', error)
    for name in ('runuser', 'unshare', 'namei', 'setfacl', 'useradd'):
        print(name + ':', shutil.which(name))
    for name in ('chrome', 'chrome_sandbox', 'chrome-sandbox'):
        path = directory / name
        print(name, 'exists:', path.exists())
    if shutil.which('namei'):
        run(['namei', '-l', str(directory / 'chrome')])
    if shutil.which('getent'):
        run(['getent', 'passwd', 'nobody'])
        run(['getent', 'passwd', 'minethrottle-test'])
    if os.geteuid() == 0 and shutil.which('runuser') and shutil.which('unshare'):
        # Ephemeral user namespace probe, without touching project files.
        run(['runuser', '-u', 'nobody', '--', 'unshare', '--user', '--map-root-user', '/usr/bin/true'])
    print('\nEND: no browser page, installation, chmod, account creation or patch change performed.')


if __name__ == '__main__':
    main()
