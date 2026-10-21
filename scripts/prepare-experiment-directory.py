#!/usr/bin/env python3
"""Create a unique persistent experiment directory; never run or modify the dataset."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def prepare(dataset, results_root, code, build_report=None):
    dataset = dataset.resolve(strict=True)
    if not dataset.is_dir():
        raise ValueError('Dataset path is not a directory')
    if results_root.is_symlink():
        raise ValueError('Results root must not be a symbolic link')
    parent = results_root.parent.resolve(strict=True)
    results_root = parent / results_root.name
    if results_root == dataset or dataset in results_root.parents or results_root in dataset.parents:
        raise ValueError('Keep results separate from the dataset tree')
    results_root.mkdir(exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('run-%Y%m%dT%H%M%SZ-'), dir=results_root))
    for name in ('logs', 'raw', 'summaries', 'provenance', 'fixtures'):
        (root / name).mkdir()
    manifest = {'created_utc': datetime.now(timezone.utc).isoformat(), 'dataset': str(dataset),
                'results_directory': str(root), 'code_directory': str(code.resolve()),
                'status': 'prepared_no_execution', 'dataset_modified': False,
                'browser_started': False, 'binary_storage': 'unchanged; current build remains in /tmp'}
    try:
        manifest['code_revision'] = subprocess.check_output(['git', '-C', str(code), 'rev-parse', 'HEAD'], text=True, timeout=15).strip()
        changes = subprocess.check_output(['git', '-C', str(code), 'status', '--porcelain', '--untracked-files=no'], text=True, timeout=15)
        manifest['code_has_tracked_changes'] = bool(changes.strip())
    except (OSError, subprocess.SubprocessError) as error:
        manifest['code_provenance_error'] = str(error)
    for name in ('chromium71.json', 'original.json'):
        source = code / 'config' / name
        if source.is_file():
            shutil.copyfile(source, root / 'provenance' / name)
    if build_report:
        data = json.loads(build_report.read_text())
        manifest['build_report_source'] = str(build_report.resolve())
        manifest['build_status'] = data.get('status')
        manifest['binary_sha256'] = data.get('binary_sha256')
        shutil.copyfile(build_report, root / 'provenance/chrome-build-report.json')
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return root, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True, type=Path)
    parser.add_argument('--results-root', required=True, type=Path)
    parser.add_argument('--build-report', type=Path)
    args = parser.parse_args()
    root, manifest = prepare(args.dataset, args.results_root, Path(__file__).resolve().parents[1], args.build_report)
    print(json.dumps(manifest, indent=2))
    print('Results directory:', root)
    print('Manifest:', root / 'manifest.json')


if __name__ == '__main__':
    main()
