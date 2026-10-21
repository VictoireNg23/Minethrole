#!/usr/bin/env python3
"""Run a benign local no-Wasm page as the dedicated user and observe renderer sandbox."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import resource
import shutil
import signal
import subprocess
import tempfile
import time
import urllib.request


def parse_status(text):
    return {line.split(':', 1)[0]: line.split(':', 1)[1].strip() for line in text.splitlines() if ':' in line}


def descendants(pid):
    seen, queue = set(), [pid]
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        try:
            queue.extend(int(n) for n in Path('/proc/%d/task/%d/children' % (current, current)).read_text().split())
        except OSError:
            pass
    return seen


def process_start_ticks(stat):
    # comm may contain spaces/parentheses; field 22 follows the final closing ).
    return stat.rsplit(')', 1)[1].split()[19]


def renderer_state(pid):
    base = Path('/proc') / str(pid)
    try:
        fields = parse_status((base / 'status').read_text())
        return {'pid': pid, 'present': True, 'state': fields.get('State'), 'parent_pid': fields.get('PPid'),
                'uid': fields.get('Uid'), 'start_ticks': process_start_ticks((base / 'stat').read_text()),
                'command': (base / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')}
    except (OSError, IndexError) as error:
        return {'pid': pid, 'present': False, 'error': str(error)}


def observe(pid):
    try:
        base = Path('/proc') / str(pid)
        command = (base / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
        if '--type=renderer' not in command:
            return None
        fields = parse_status((base / 'status').read_text())
        return {'pid': pid, 'command': command, 'uid': fields.get('Uid'),
                'start_ticks': process_start_ticks((base / 'stat').read_text()),
                'seccomp': fields.get('Seccomp'), 'no_new_privs': fields.get('NoNewPrivs'),
                'user_namespace': os.readlink(base / 'ns/user')}
    except OSError:
        return None


def select_debug_targets(commands, binary):
    selected = {}
    for pid, argv in sorted(commands):
        if not argv.startswith(str(binary) + ' '):
            continue
        role = 'renderer' if '--type=renderer ' in argv + ' ' else 'browser' if '--type=' not in argv else None
        if role and role not in selected:
            selected[role] = pid
    return [(selected[role], role) for role in ('browser', 'renderer') if role in selected]


def debugger_command(pid, role, resume_startup=False):
    command = [shutil.which('gdb'), '-nx', '-nh', '--batch', '-p', str(pid), '-ex', 'set pagination off']
    if resume_startup and role == 'renderer':
        # Chromium 71's startup dialog explicitly installs a SIGUSR1 unpause handler.
        command += ['-ex', 'handle SIGUSR1 nostop noprint pass', '-ex', 'signal SIGUSR1']
    return command + ['-ex', 'p $_siginfo', '-ex', 'info registers orig_rax rax rip',
                      '-ex', 'thread apply all bt 15', '-ex', 'detach']


def limited_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage-report', required=True, type=Path)
    parser.add_argument('--diagnostic-cdp', action='store_true', help='Observe localhost DevTools targets; intentional stop, no passing verdict')
    parser.add_argument('--diagnostic-gdb', action='store_true', help='Capture live browser/renderer stacks during the CDP diagnostic')
    parser.add_argument('--diagnostic-renderer-startup', action='store_true', help='Pause renderer using Chromium startup switch, attach GDB then unpause with SIGUSR1')
    args = parser.parse_args()
    if args.diagnostic_renderer_startup and not args.diagnostic_gdb:
        raise SystemExit('--diagnostic-renderer-startup requires --diagnostic-gdb')
    if args.diagnostic_gdb and (not args.diagnostic_cdp or not shutil.which('gdb')):
        raise SystemExit('--diagnostic-gdb requires --diagnostic-cdp and installed GDB')
    if os.geteuid() != 0:
        raise SystemExit('Run the controller as root; Chromium itself is launched as the dedicated user')
    stage = json.loads(args.stage_report.read_text())
    if stage.get('status') != 'nonroot_browser_test_staged_not_launched' or stage.get('user') != 'minethrottle-test':
        raise SystemExit('Expected dedicated browser staging report')
    account = pwd.getpwnam(stage['user'])
    if account.pw_uid != stage['uid'] or account.pw_uid == 0:
        raise SystemExit('Dedicated account identity differs')
    binary = Path(stage['binary'])
    digest = hashlib.sha256()
    with binary.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != stage['binary_sha256']:
        raise SystemExit('Browser checksum differs')
    run = Path(stage['results_run']).resolve(strict=True)
    saved = Path(tempfile.mkdtemp(prefix='browser-ready-', dir=run / 'raw'))
    local = Path(tempfile.mkdtemp(prefix='ready-', dir=Path(stage['session_directory'])))
    for name in ('home', 'profile', 'cache'):
        path = local / name
        path.mkdir(mode=0o700)
        os.chown(path, account.pw_uid, account.pw_gid)
    fixture = Path(__file__).resolve().parents[1] / 'tests/fixtures/browser-ready.html'
    page = local / 'browser-ready.html'
    shutil.copyfile(fixture, page)
    page.chmod(0o644)
    os.chown(local, account.pw_uid, account.pw_gid)
    env = dict(os.environ, HOME=str(local / 'home'), XDG_CONFIG_HOME=str(local / 'home'), XDG_CACHE_HOME=str(local / 'cache'))
    command = ['/usr/sbin/runuser', '-u', stage['user'], '--', str(binary),
               '--headless', '--disable-gpu', '--disable-dev-shm-usage', '--no-first-run',
               '--no-default-browser-check', '--disable-background-networking', '--disable-component-update',
               '--disable-extensions', '--disable-sync', '--metrics-recording-only',
               '--user-data-dir=' + str(local / 'profile'), '--dump-dom', page.as_uri()]
    if args.diagnostic_cdp:
        command.remove('--dump-dom')
        command += ['--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0', '--enable-logging=stderr']
    if args.diagnostic_renderer_startup:
        command.append('--renderer-startup-dialog')
    report = {'status': 'incomplete', 'command': command, 'binary_sha256': digest.hexdigest(),
              'local_directory': str(local), 'results_directory': str(saved),
              'wasm_execution': 'not run', 'dataset_execution': 'not run', 'sandbox_disabled_by_command': False}
    print('Persistent results:', saved, flush=True)
    samples = {}
    target_snapshots = []
    diagnostic_stop = False
    last_probe = 0.0
    gdb_captures = []
    gdb_done = False
    gdb_selection = {}
    with (saved / 'stdout.html').open('w+') as stdout, (saved / 'stderr.log').open('w+') as stderr:
        process = subprocess.Popen(command, cwd=local, env=env, stdout=stdout, stderr=stderr,
                                   start_new_session=True, preexec_fn=limited_core)
        timed_out = False
        started = time.monotonic()
        try:
            while process.poll() is None:
                for pid in descendants(process.pid):
                    sample = observe(pid)
                    if sample:
                        samples[pid] = sample
                if args.diagnostic_cdp:
                    elapsed = time.monotonic() - started
                    port_file = local / 'profile/DevToolsActivePort'
                    if elapsed - last_probe >= 0.5 and port_file.is_file():
                        last_probe = elapsed
                        try:
                            port = int(port_file.read_text().splitlines()[0])
                            if not 1 <= port <= 65535:
                                raise ValueError('Invalid debugger port')
                            with urllib.request.urlopen('http://127.0.0.1:%d/json/list' % port, timeout=1) as response:
                                targets = json.load(response)
                            target_snapshots.append({'elapsed': round(elapsed, 2), 'targets': targets})
                        except (OSError, ValueError) as error:
                            target_snapshots.append({'elapsed': round(elapsed, 2), 'error': str(error)})
                    if args.diagnostic_gdb and not gdb_done and elapsed >= (1 if args.diagnostic_renderer_startup else 3):
                        gdb_done = True
                        candidates, scan_errors = [], []
                        current_descendants = descendants(process.pid)
                        known_states = []
                        for pid, observed in samples.items():
                            state = renderer_state(pid)
                            state['still_descendant'] = pid in current_descendants
                            state['identity_matches'] = state.get('start_ticks') == observed.get('start_ticks') and state.get('uid') == observed.get('uid')
                            known_states.append(state)
                            if state['present'] and state['identity_matches'] and '--type=renderer' in state.get('command', ''):
                                candidates.append((pid, state['command']))
                        for pid in current_descendants:
                            try:
                                proc = Path('/proc') / str(pid)
                                argv = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
                                candidates.append((pid, argv))
                            except OSError as error:
                                scan_errors.append({'pid': pid, 'error': str(error)})
                        targets = select_debug_targets(candidates, binary)
                        gdb_selection = {'selected': targets, 'known_renderer_states': known_states, 'scan_errors': scan_errors,
                                         'renderer_selected': any(role == 'renderer' for _, role in targets)}
                        for pid, role in targets:
                            if args.diagnostic_renderer_startup and role != 'renderer':
                                continue
                            logfile = saved / ('gdb-%s-%d.log' % (role, pid))
                            capture = {'pid': pid, 'role': role, 'log': str(logfile)}
                            try:
                                debugger = subprocess.run(debugger_command(pid, role, args.diagnostic_renderer_startup),
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=15)
                                logfile.write_text(debugger.stdout)
                                capture.update(exit_code=debugger.returncode, output_tail=debugger.stdout[-12000:],
                                               signal_details=[line for line in debugger.stdout.splitlines()
                                                   if any(token in line for token in ('received signal', '_sigsys', '_syscall', 'si_signo', 'si_syscall', 'orig_rax'))])
                            except subprocess.TimeoutExpired as error:
                                output_bytes = error.stdout or b''
                                text = output_bytes.decode(errors='replace') if isinstance(output_bytes, bytes) else output_bytes
                                logfile.write_text(text)
                                capture.update(status='debugger_timeout', output_tail=text[-12000:])
                            gdb_captures.append(capture)
                    if elapsed >= 6:
                        diagnostic_stop = True
                        break
                if time.monotonic() - started > 20:
                    timed_out = True
                    break
                time.sleep(0.05)
        finally:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        stdout.seek(0)
        output = stdout.read()
        stderr.seek(0)
        errors = stderr.read()
    report.update(exit_code=process.returncode, timeout=timed_out,
                  page_marker_present='MINETHROTTLE_BROWSER_READY</pre>' in output,
                  renderer_samples=list(samples.values()), stderr_tail=errors[-5000:])
    sandbox_observed = any(item['seccomp'] == '2' and item['no_new_privs'] == '1' and
                           item['uid'] and int(item['uid'].split()[1]) == account.pw_uid and
                           '--no-sandbox' not in item['command'] for item in samples.values())
    report['renderer_seccomp_and_nonroot_observed'] = sandbox_observed
    if args.diagnostic_cdp:
        report.update(renderer_startup_pause_requested=args.diagnostic_renderer_startup, gdb_selection=gdb_selection, gdb_captures=gdb_captures, devtools_target_snapshots=target_snapshots, intentional_diagnostic_stop=diagnostic_stop,
                      page_title_marker_observed=any(target.get('title') == 'MINETHROTTLE_BROWSER_READY'
                          for snapshot in target_snapshots for target in snapshot.get('targets', [])))
    if not timed_out and process.returncode == 0 and report['page_marker_present'] and sandbox_observed:
        report['status'] = 'benign_page_nonroot_renderer_sandbox_observed'
    else:
        report['status'] = 'browser_ready_failed_or_incomplete'
    if args.diagnostic_cdp:
        report['status'] = 'diagnostic_capture_only_not_browser_ready_validation'
    (saved / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('Report:', saved / 'result.json')
    return 0 if report['status'] == 'benign_page_nonroot_renderer_sandbox_observed' else 1


if __name__ == '__main__':
    main()
