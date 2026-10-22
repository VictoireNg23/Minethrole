#!/usr/bin/env python3
"""Prepare a separately recorded native decision trace; no build or browser execution."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import difflib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('readiness_report', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = args.workspace.resolve()
    source = root / 'src/v8/src/wasm/module-compiler.cc'
    readiness_path = args.readiness_report.resolve()
    previous = json.loads(readiness_path.read_text())
    if previous.get('status') != 'original_decision_settings_confirmed' or previous.get('mismatches'):
        parser.error('Original settings report required')
    if not (root / 'preparation.json').is_file() or source.is_symlink():
        parser.error('Expected isolated workspace and regular V8 source')
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != previous.get('source_sha256'):
        parser.error('Source changed since readiness inspection; preserve and inspect')
    original = raw.decode()
    replacements = [
        ('bool is_defensive = false;', 'bool is_defensive = true;'),
        ('            cos = Cos((double *)(speeds + mode * num_injected_globals_), mode, norm);',
         '            cos = Cos((double *)(speeds + mode * num_injected_globals_), mode, norm);\n'
         '            fprintf(stderr, "MINETHROTTLE_DECISION module=%u profile=%u cpu_ms=%.17g cos=%.17g z=%.17g positive=%d\\n",\n'
         '                    i, mode, interval, cos, k,\n'
         '                    int(cos >= Cosine_threshold && k >= -1 * Sigma_threshold));')]
    modified = original
    for before, after in replacements:
        if modified.count(before) != 1:
            parser.error('Missing or ambiguous original trace anchor')
        modified = modified.replace(before, after, 1)
    version = subprocess.run(['git', '-C', str(root / 'src/v8'), 'rev-parse', 'HEAD'],
                             capture_output=True, text=True, check=True).stdout.strip()
    if version != 'b5a5d900a5385d6429edefb11ece72bfa649ca47':
        parser.error('Unexpected V8 revision')
    directory = Path(tempfile.mkdtemp(prefix='decision-trace-prepare-', dir=root))
    (directory / 'module-compiler.cc.before').write_bytes(raw)
    proposed = directory / 'module-compiler.cc.proposed'
    proposed.write_text(modified)
    patch = ''.join(difflib.unified_diff(original.splitlines(True), modified.splitlines(True),
                                        fromfile='a/src/wasm/module-compiler.cc',
                                        tofile='b/src/wasm/module-compiler.cc'))
    (directory / 'decision-trace.patch').write_text(patch)
    if args.apply:
        # Recheck before mutation; only the verified file is written.
        if source.read_bytes() != raw:
            parser.error('Source changed while preparing trace')
        source.write_text(modified)
    report = dict(status='decision_trace_applied_rebuild_required' if args.apply else 'decision_trace_prepared_not_applied',
                  source=str(source), source_before_sha256=hashlib.sha256(raw).hexdigest(),
                  source_after_sha256=hashlib.sha256(modified.encode()).hexdigest(),
                  adaptation_patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
                  readiness_report=str(readiness_path), backup=str(directory / 'module-compiler.cc.before'),
                  original_patch_files_modified=False, defensive_enabled_in_source=args.apply,
                  build='not run', browser_started=False, dataset_execution='not run',
                  warning='Diagnostic tracing changes timing. Native decision and original SIGUSR1 slowing are enabled after rebuild; use only benign fixtures. Existing staged collection binary remains separate.')
    (directory / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('Report:', directory / 'result.json')


if __name__ == '__main__':
    main()
