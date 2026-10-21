#!/usr/bin/env python3
"""Pinned historical gclient sync, opt-in network, no hooks or build.

Default: validate and print the plan. --sync enables Git/CIPD downloads into the
new workspace. Partial progress and logs are retained on failure.
"""
import argparse
import ast
import json
import os
from pathlib import Path, PurePosixPath
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

CHROMIUM = 'c2bec8045f7ad3ece1c5d80236183a21c1fac3f5'
V8 = 'b5a5d900a5385d6429edefb11ece72bfa649ca47'
TOOLS = 'c6a8d114b060f5f68637e8897712a24252402377'
OPTIONS = ['-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
           '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-c', 'remote.origin.promisor=false']


def environment(workspace):
    env = os.environ.copy()
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_CACHE_PATH'):
        env.pop(name, None)
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0',
               DEPOT_TOOLS_UPDATE='0', GCLIENT_PY3='0')
    count = int(env.get('GIT_CONFIG_COUNT', '0'))
    for key, value in [('core.hooksPath', '/dev/null'), ('core.fsmonitor', 'false'), ('gc.auto', '0'), ('maintenance.auto', 'false')]:
        env['GIT_CONFIG_KEY_' + str(count)] = key
        env['GIT_CONFIG_VALUE_' + str(count)] = value
        count += 1
    env['GIT_CONFIG_COUNT'] = str(count)
    return env


def check_checkout(path, revision, env):
    command = ['git', '--no-optional-locks', *OPTIONS, '-C', str(path)]
    head = subprocess.check_output(command + ['rev-parse', 'HEAD'], env=env, timeout=30).decode().strip()
    if head != revision:
        raise ValueError('Unexpected HEAD: ' + str(path))
    for kind in ([], ['--cached']):
        result = subprocess.run(command + ['diff', *kind, '--quiet', '--no-ext-diff', '--no-textconv', '--ignore-submodules=all'],
                                env=env, timeout=90)
        if result.returncode != 0:
            raise ValueError('Tracked changes or unavailable diff; preserve and inspect: ' + str(path))


def validate_solution(text):
    tree = ast.parse(text)
    if (len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assign)
            or len(tree.body[0].targets) != 1 or not isinstance(tree.body[0].targets[0], ast.Name)
            or tree.body[0].targets[0].id != 'solutions'):
        raise ValueError('Unexpected .gclient structure; no overwrite attempted')
    expected = [{'name': 'src', 'url': 'https://chromium.googlesource.com/chromium/src.git',
                 'managed': False, 'custom_deps': {}, 'custom_vars': {}}]
    if ast.literal_eval(tree.body[0].value) != expected:
        raise ValueError('Unexpected .gclient solution settings; stopping')


def sync_arguments():
    return ['sync', '--verbose', '--nohooks', '--noprehooks', '--jobs=4',
            '--revision', 'src@' + CHROMIUM, '--revision', 'src/v8@' + V8]


CACHE_PROBE = """import sys, json
sys.path.insert(0, sys.argv[1])
import git_cache
try:
    cache_path = git_cache.Mirror.GetCachePath()
except RuntimeError:
    cache_path = None
print('MINETHROTTLE_CACHE_PROBE=' + json.dumps({'cache_path': cache_path}))
"""


def validate_cache_probe(text):
    prefix = 'MINETHROTTLE_CACHE_PROBE='
    records = [json.loads(line[len(prefix):]) for line in text.splitlines() if line.startswith(prefix)]
    if len(records) != 1 or 'cache_path' not in records[0]:
        raise ValueError('Historical cache probe output incomplete')
    if records[0]['cache_path'] not in (None, ''):
        raise ValueError('Historical depot_tools still selects a Git mirror cache; sync not launched')
    return records[0]


def check_origin(path, expected, env):
    command = ['git', '--no-optional-locks', *OPTIONS, '-C', str(path), 'config', '--get', 'remote.origin.url']
    actual = subprocess.check_output(command, env=env, timeout=15).decode().strip()
    if actual.rstrip('/') != expected.rstrip('/'):
        raise ValueError('Unexpected origin in ' + str(path) + '; existing configuration left untouched')


def terminate(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def logged_command(command, cwd, env, logfile, timeout):
    """Stream combined output, preserve real exit status, stop only our group."""
    started = time.monotonic()
    status = 'finished'
    with logfile.open('xb') as output:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            try:
                while selector.get_map():
                    if time.monotonic() - started >= timeout:
                        status = 'timeout'
                        terminate(process)
                        break
                    for key, _ in selector.select(timeout=1):
                        data = os.read(key.fileobj.fileno(), 65536)
                        if not data:
                            selector.unregister(key.fileobj)
                        else:
                            output.write(data)
                            output.flush()
                            print(data.decode(errors='replace'), end='', flush=True)
                if process.poll() is None:
                    process.wait(timeout=max(0.1, timeout - (time.monotonic() - started)))
            except subprocess.TimeoutExpired:
                status = 'timeout'
                terminate(process)
            except KeyboardInterrupt:
                status = 'interrupted'
                terminate(process)
        process.stdout.close()
        code = process.wait()
    return {'status': status, 'underlying_exit_code': code,
            'elapsed_seconds': round(time.monotonic() - started, 2), 'log': str(logfile)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('seed_report', type=Path)
    parser.add_argument('--sync', action='store_true', help='Explicitly enable network synchronization')
    parser.add_argument('--timeout', type=int, default=3600)
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error('--timeout must be positive')
    workspace = args.workspace.resolve(strict=True)
    manifest = json.loads((workspace / 'preparation.json').read_text())
    tools = Path(manifest['tools']).resolve(strict=True)
    if json.loads((tools / 'provenance.json').read_text())['revision'] != TOOLS:
        raise ValueError('Historical tools revision mismatch')
    if os.environ.get('VPYTHON_BYPASS'):
        raise ValueError('VPYTHON_BYPASS must not be enabled for this test')
    validate_solution((workspace / '.gclient').read_text())
    env = environment(workspace)
    check_checkout(workspace / 'src', CHROMIUM, env)
    check_checkout(workspace / 'src/v8', V8, env)
    check_origin(workspace / 'src', 'https://chromium.googlesource.com/chromium/src.git', env)
    check_origin(workspace / 'src/v8', 'https://chromium.googlesource.com/v8/v8.git', env)
    seeds = json.loads(args.seed_report.read_text())
    if seeds.get('status') != 'local_pass_completed_not_dependency_readiness':
        raise ValueError('Local seed pass incomplete')
    for entry in seeds['entries']:
        if entry['status'] in ('local_clone_prepared', 'existing_exact_checkout_untouched'):
            path = PurePosixPath(entry['path'])
            if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != 'src':
                raise ValueError('Unexpected seed path')
            check_checkout(workspace / str(path), entry['revision'], env)
            if 'remote' in entry:
                check_origin(workspace / str(path), entry['remote'], env)
        elif entry['status'] in ('occupied_destination_untouched', 'destination_symlink_deferred', 'destination_outside_workspace'):
            raise ValueError('Unresolved destination conflict in seed report: ' + entry['path'])
    gclient = tools / 'depot_tools/gclient'
    prefix = [str(workspace / 'with-tools.sh'), str(gclient)]
    command = prefix + sync_arguments()
    print('Planned command:', json.dumps(command), flush=True)
    if not args.sync:
        print('PLAN ONLY. Add --sync to enable downloads; no gclient or network operation run.')
        return 0
    free = shutil.disk_usage(workspace).free
    print('Available destination bytes:', free, flush=True)
    if free < 100 * 1024 ** 3:
        raise ValueError('Less than 100 GiB free before dependency downloads; stopping')
    logs = Path(tempfile.mkdtemp(prefix='sync-nohooks-', dir=workspace))
    result_file = logs / 'result.json'
    state = {'command': command, 'status': 'checking_cli', 'hooks': 'disabled', 'pre_hooks': 'disabled',
             'build': 'not run', 'git_mirror_policy': 'disabled; historical resolver must confirm',
             'result_file': str(result_file)}
    result_file.write_text(json.dumps(state, indent=2) + '\n')
    print('Diagnostic directory:', logs, flush=True)
    help_result = logged_command(prefix + ['sync', '--help'], workspace, env, logs / 'sync-help.log', 60)
    help_text = (logs / 'sync-help.log').read_text(errors='replace')
    if help_result['status'] != 'finished' or help_result['underlying_exit_code'] != 0 or not all(flag in help_text for flag in ('--nohooks', '--noprehooks', '--revision')):
        state.update(status='cli_check_failed', cli=help_result)
        result_file.write_text(json.dumps(state, indent=2) + '\n')
        print('Sync NOT launched: CLI checks incomplete. Report:', result_file)
        return 1
    state['status'] = 'checking_historical_cache_resolver'
    result_file.write_text(json.dumps(state, indent=2) + '\n')
    probe = logged_command([str(workspace / 'with-tools.sh'), 'python', '-c', CACHE_PROBE,
                            str(tools / 'depot_tools')], workspace, env, logs / 'cache-probe.log', 60)
    state['cache_probe_process'] = probe
    try:
        if probe['status'] != 'finished' or probe['underlying_exit_code'] != 0:
            raise ValueError('Historical cache resolver probe failed')
        state['cache_probe'] = validate_cache_probe((logs / 'cache-probe.log').read_text(errors='replace'))
    except ValueError as error:
        state.update(status='cache_probe_failed_sync_not_launched', reason=str(error))
        result_file.write_text(json.dumps(state, indent=2) + '\n')
        print(json.dumps(state, indent=2))
        return 1
    state['status'] = 'sync_running'
    result_file.write_text(json.dumps(state, indent=2) + '\n')
    result = logged_command(command, workspace, env, logs / 'sync.log', args.timeout)
    state.update(status='sync_failed_or_incomplete', process=result)
    if result['status'] == 'finished' and result['underlying_exit_code'] == 0:
        state['status'] = 'sync_exit_zero_heads_not_yet_verified'
        result_file.write_text(json.dumps(state, indent=2) + '\n')
        check_checkout(workspace / 'src', CHROMIUM, env)
        check_checkout(workspace / 'src/v8', V8, env)
        state['status'] = 'sync_exit_zero_primary_heads_verified_nohooks'
    result_file.write_text(json.dumps(state, indent=2) + '\n')
    print(json.dumps(state, indent=2))
    print('Report:', result_file)
    print('Do not run hooks or build before reviewing results. Retain original borrowed object stores.')
    return 0 if state['status'] == 'sync_exit_zero_primary_heads_verified_nohooks' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('FAILED / INCOMPLETE:', error, flush=True)
        raise SystemExit(1)
