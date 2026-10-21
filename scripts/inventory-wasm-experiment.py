#!/usr/bin/env python3
"""Inventory the dataset recorded in an experiment manifest, without execution."""
import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path
import subprocess
import tempfile
from wasm_metadata import inspect, UnsupportedFeature


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--max-file-mib', type=int, default=64)
    args = parser.parse_args()
    if not 1 <= args.max_file_mib <= 1024:
        raise SystemExit('Inspection file limit must be in 1..1024 MiB')
    run = args.run.resolve(strict=True)
    manifest = json.loads((run / 'manifest.json').read_text())
    dataset = Path(manifest['dataset']).resolve(strict=True)
    if not dataset.is_dir() or not (run / 'summaries').is_dir():
        raise SystemExit('Expected prepared experiment directory and dataset')
    step = Path(tempfile.mkdtemp(prefix='inventory-', dir=run / 'summaries'))
    statuses, namespaces, exported_names = Counter(), Counter(), Counter()
    count = 0
    print('New inventory directory:', step, flush=True)
    with (step / 'modules.jsonl').open('x') as details, (step / 'modules.csv').open('x', newline='') as table:
        fields = ['relative_path', 'status', 'bytes', 'sha256', 'imports', 'exports', 'start', 'error']
        writer = csv.DictWriter(table, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for directory, directories, files in os.walk(dataset, followlinks=False):
            directories[:] = sorted(d for d in directories if not (Path(directory) / d).is_symlink())
            for filename in sorted(files):
                if Path(filename).suffix.lower() != '.wasm':
                    continue
                path = Path(directory) / filename
                row = {'relative_path': str(path.relative_to(dataset))}
                try:
                    if path.is_symlink():
                        row['status'] = 'symlink_not_followed'
                    elif path.stat().st_size > args.max_file_mib * 1024 ** 2:
                        row.update(status='size_limit_not_inspected', bytes=path.stat().st_size)
                    else:
                        row.update(inspect(path.read_bytes()), status='metadata_parsed_not_validated')
                        namespaces.update(item['module'] for item in row['imports'])
                        exported_names.update(item['name'] for item in row['exports'] if item['kind'] == 0)
                except UnsupportedFeature as error:
                    row.update(status='unsupported_metadata', error=str(error))
                except (OSError, ValueError, IndexError) as error:
                    row.update(status='metadata_error', error=str(error))
                count += 1
                statuses[row['status']] += 1
                details.write(json.dumps(row, ensure_ascii=False) + '\n')
                writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value for key, value in row.items()})
    code = Path(__file__).resolve().parents[1]
    revision = subprocess.check_output(['git', '-C', str(code), 'rev-parse', 'HEAD'], text=True, timeout=15).strip()
    summary = {'status': 'inventory_completed_no_execution', 'dataset': str(dataset), 'wasm_candidates': count,
               'metadata_statuses': dict(statuses), 'common_import_namespaces': namespaces.most_common(20),
               'common_function_exports': exported_names.most_common(20), 'code_revision': revision,
               'output_directory': str(step), 'classification': 'not performed', 'wasm_execution': 'not run',
               'limits': 'Metadata reader only; not full validation or Chromium 71 compatibility verification'}
    (step / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    print('Report:', step / 'summary.json')


if __name__ == '__main__':
    main()
