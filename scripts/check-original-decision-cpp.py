#!/usr/bin/env python3
"""Compile original score expressions in a standalone arithmetic harness, not Chromium."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def extract(text):
    arrays = [re.search(r'double\s+' + name + r'\[4\]\[3\]\s*=\s*\{.*?\};', text, re.S).group()
              for name in ('baseline_value', 'baseline_stddev', 'baseline_normalized')]
    cosine = re.search(r'double Cos\(double \*speed, uint32_t mode, double norm\)\{.*?\n\}', text, re.S).group()
    accumulation = re.search(r'k \+= \(speeds\[j \+ mode \* num_injected_globals_\].*?;', text).group()
    average = re.search(r'k /= num_injected_globals_;', text).group()
    condition = re.search(r'if\((cos >= Cosine_threshold && k >= -1 \* Sigma_threshold)\)', text).group(1)
    return arrays + [cosine, accumulation, average, condition]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('readiness_report', type=Path)
    args = parser.parse_args()
    report_path = args.readiness_report.resolve()
    readiness = json.loads(report_path.read_text())
    if readiness.get('status') != 'original_decision_settings_confirmed' or readiness.get('mismatches'):
        parser.error('Original decision settings must be confirmed')
    compiler = shutil.which('c++')
    if not compiler:
        parser.error('System C++ compiler missing')
    patch = Path(__file__).resolve().parents[1] / 'patches/v8.patch'
    if hashlib.sha256(patch.read_bytes()).hexdigest() != '72c3adef6f566e7de6b6b7f0d1c6a12f0384098be3601fbcbe2272f1861ee563':
        parser.error('Unexpected original patch')
    original = '\n'.join(line[1:] for line in patch.read_text().splitlines()
                         if line.startswith('+') and not line.startswith('+++'))
    source_path = args.workspace.resolve() / 'src/v8/src/wasm/module-compiler.cc'
    expected = extract(original)
    actual = extract(source_path.read_text())
    if actual != expected:
        parser.error('Score expressions differ from original patch')
    arrays = '\n'.join(actual[:3])
    cosine, accumulation, average, condition = actual[3:]
    source = '''#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
using std::sqrt;
''' + arrays + '\n' + cosine + '''
int main() {
  const uint32_t num_injected_globals_ = 3;
  const double Cosine_threshold = 0.99, Sigma_threshold = 3;
  int failures = 0;
  std::cout << std::setprecision(17);
  for (uint32_t mode = 0; mode < 4; ++mode) {
    for (int input = 0; input < 3; ++input) {
      double speeds[12] = {}, k = 0.0, sum = 0.0;
      for (uint32_t j = 0; j < 3; ++j) {
        speeds[j + mode * 3] = input == 0 || (input == 2 && j == 0) ? baseline_value[mode][j] : 0;
      }
      for (uint32_t j = 0; j < num_injected_globals_; ++j) {
        sum += pow(speeds[j + mode * num_injected_globals_], 2.0);
''' + accumulation + '''
      }
''' + average + '''
      double norm = sqrt(sum);
      double cos = Cos(speeds + mode * num_injected_globals_, mode, norm);
      bool positive = ''' + condition + ''';
      bool passed = positive == (input == 0);
      failures += !passed;
      std::cout << mode << " " << input << " " << cos << " " << k << " " << positive << " " << passed << "\\n";
    }
  }
  return failures ? 1 : 0;
}
'''
    local = Path(tempfile.mkdtemp(prefix='minethrottle71-decision-cpp-'))
    saved = Path(tempfile.mkdtemp(prefix='decision-cpp-', dir=report_path.parent.parent))
    cpp = local / 'score-check.cc'
    cpp.write_text(source)
    shutil.copy2(cpp, saved / cpp.name)
    command = [compiler, '-std=c++14', '-O2', str(cpp), '-o', str(local / 'score-check')]
    compile_result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=60)
    (saved / 'compile.log').write_text(compile_result.stdout)
    execution = None
    if compile_result.returncode == 0:
        execution = subprocess.run([str(local / 'score-check')], stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, timeout=10)
        (saved / 'stdout.log').write_text(execution.stdout)
        print(execution.stdout, end='')
    passed = execution is not None and execution.returncode == 0 and len(execution.stdout.splitlines()) == 12
    report = dict(status='original_cpp_score_checks_passed' if passed else 'original_cpp_score_checks_failed',
                  readiness_report=str(report_path), original_expressions_verified=True,
                  compile_command=command, compile_exit=compile_result.returncode,
                  execution_exit=execution.returncode if execution else None,
                  local_directory=str(local), harness_sha256=hashlib.sha256(cpp.read_bytes()).hexdigest(),
                  chromium_modified=False, chromium_execution='not run', defense_enabled=False,
                  dataset_execution='not run', classification='not performed',
                  limits='Standalone original score expressions only; not the complete Chromium sampling and defense branch')
    (saved / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Status:', report['status'])
    print('Report:', saved / 'result.json')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
