#!/usr/bin/env python3
"""Run three native BPF regression tests as the dedicated non-root user."""
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
import xml.etree.ElementTree as ET

EXPECTED = {'BaselinePolicy.Clone3ReturnsEnosys', 'BaselinePolicy.CreateThread', 'BaselinePolicy.DisallowedCloneFlagCrashes'}


def read_test_results(path):
    root = ET.parse(path).getroot()
    cases = []
    for case in root.iter('testcase'):
        cases.append({'name': case.get('classname', '') + '.' + case.get('name', ''),
                      'status': case.get('status'), 'failures': len(case.findall('failure')),
                      'errors': len(case.findall('error')), 'skipped': len(case.findall('skipped'))})
    passed = (len(cases) == len(EXPECTED) and {c['name'] for c in cases} == EXPECTED and
              all(c['status'] == 'run' and not (c['failures'] or c['errors'] or c['skipped']) for c in cases))
    return cases, passed


def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage-report', required=True, type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Controller requires root; tests run through runuser as the dedicated account')
    stage = json.loads(args.stage_report.read_text())
    if stage.get('status') != 'nonroot_browser_test_staged_not_launched' or stage.get('user') != 'minethrottle-test' or not stage.get('clone3_adaptation'):
        raise SystemExit('Expected clone3-adapted browser/test staging report')
    account = pwd.getpwnam(stage['user'])
    if account.pw_uid == 0 or account.pw_uid != stage['uid'] or account.pw_gid != stage['gid']:
        raise SystemExit('Dedicated account identity changed')
    binary = Path(stage['sandbox_test_binary'])
    digest = hashlib.sha256()
    with binary.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != stage['sandbox_test_binary_sha256']:
        raise SystemExit('Native test binary checksum differs')
    run = Path(stage['results_run']).resolve(strict=True)
    saved = Path(tempfile.mkdtemp(prefix='sandbox-native-', dir=run / 'raw'))
    local = Path(tempfile.mkdtemp(prefix='sandbox-native-', dir=Path(stage['session_directory'])))
    os.chown(local, account.pw_uid, account.pw_gid)
    xml_path = local / 'gtest-results.xml'
    command = ['/usr/sbin/runuser', '-u', stage['user'], '--', str(binary), '--single-process-tests',
               '--gtest_filter=' + ':'.join(sorted(EXPECTED)), '--gtest_output=xml:' + str(xml_path)]
    result = {'status': 'incomplete', 'command': command, 'test_binary_sha256': digest.hexdigest(),
              'stage_report': str(args.stage_report.resolve()), 'results_directory': str(saved),
              'local_directory': str(local), 'browser_started': False, 'dataset_execution': 'not run'}
    print('Persistent results:', saved, flush=True)
    with (saved / 'stdout.log').open('w+') as log:
        process = subprocess.Popen(command, cwd=local, env=dict(os.environ, HOME=str(local)),
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True, preexec_fn=no_core)
        timeout = False
        try:
            process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            timeout = True
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        log.seek(0)
        text = log.read()
    result.update(exit_code=process.returncode, timeout=timeout, stdout_tail=text[-10000:])
    try:
        if xml_path.is_symlink():
            raise ValueError('Refused symlink test XML')
        cases, all_passed = read_test_results(xml_path)
        shutil.copyfile(xml_path, saved / 'gtest-results.xml')
        result['test_cases'] = cases
        result['status'] = 'three_native_bpf_tests_passed' if not timeout and process.returncode == 0 and all_passed else 'native_bpf_tests_failed_or_incomplete'
    except (OSError, ValueError, ET.ParseError) as error:
        result.update(status='native_bpf_tests_failed_or_incomplete', error=str(error))
    (saved / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', saved / 'result.json')
    return 0 if result['status'] == 'three_native_bpf_tests_passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
