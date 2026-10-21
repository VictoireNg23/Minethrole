#!/usr/bin/env python3
"""Describe host requirements from observed imports; never classify mining or execute Wasm."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import subprocess
import tempfile


def describe(row):
    imports = row.get('imports', [])
    requirements, evidence = set(), []
    namespaces = sorted({item['module'] for item in imports})
    for namespace in namespaces:
        names = sorted({item['name'] for item in imports if item['module'] == namespace})
        if namespace in ('wasi_snapshot_preview1', 'wasi_unstable'):
            tag = 'wasi_host_required'
        elif namespace in ('go', 'gojs'):
            tag = 'go_runtime_glue_required'
        elif namespace == 'wbg' or namespace.startswith(('./', '../')):
            tag = 'javascript_bindings_required'
        elif namespace in ('global', 'Math'):
            tag = 'named_host_bindings_required'
        else:
            tag = 'unresolved_host_namespace'
        requirements.add(tag)
        evidence.append({'namespace': namespace, 'import_names': names, 'interpretation': tag})
    emscripten = sorted({item['module'] + '.' + item['name'] for item in imports
                         if item['name'].startswith(('emscripten_', '_emscripten_', 'invoke_', '___syscall', '__syscall'))
                         or item['name'] in ('abortOnCannotGrowMemory', 'enlargeMemory', 'getTotalMemory', 'setTempRet0', 'getTempRet0')})
    if emscripten:
        requirements.add('emscripten_glue_indicated')
    if not imports:
        requirements.add('no_imports_observed')
    functions = [item for item in row.get('exports', []) if item['kind'] == 0]
    conventional = [item for item in functions if item['name'] in ('_start', '_initialize', 'main', '_main')]
    return {'relative_path': row['relative_path'], 'sha256': row.get('sha256'),
            'metadata_status': row['status'], 'host_requirements': sorted(requirements),
            'import_evidence': evidence, 'emscripten_name_evidence': emscripten,
            'exported_functions': functions, 'start_function_index': row.get('start'),
            'conventional_entry_names': conventional,
            'execution_readiness': 'not established; arguments, initialization and semantics require inspection',
            'mining_entry_point': 'not established', 'detection': 'not performed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', required=True, type=Path)
    args = parser.parse_args()
    inventory = args.inventory.resolve(strict=True)
    summary = json.loads((inventory / 'summary.json').read_text())
    if summary.get('status') != 'inventory_completed_no_execution':
        raise SystemExit('Completed static inventory required')
    root = Path(tempfile.mkdtemp(prefix='hosts-', dir=inventory.parent))
    tags, statuses = Counter(), Counter()
    hashes = Counter()
    count = 0
    with (inventory / 'modules.jsonl').open() as source, (root / 'modules-hosts.jsonl').open('x') as output:
        for line in source:
            row = json.loads(line)
            statuses[row['status']] += 1
            if row.get('sha256'):
                hashes[row['sha256']] += 1
            item = describe(row)
            if row['status'] != 'metadata_parsed_not_validated':
                item['host_requirements'] = ['metadata_unavailable_do_not_infer']
                item['import_evidence'] = []
            tags.update(item['host_requirements'])
            count += 1
            output.write(json.dumps(item, ensure_ascii=False) + '\n')
    code = Path(__file__).resolve().parents[1]
    reference = code / 'docs/dataset1_s-inventaire.csv'
    with reference.open(newline='') as source:
        reference_hashes = Counter(row['sha256'] for row in csv.DictReader(source))
    result = {'status': 'host_requirements_described_no_execution', 'modules': count,
              'host_requirement_counts_overlapping': dict(tags), 'metadata_statuses': dict(statuses),
              'dataset1_s_comparison': {'reference_rows': sum(reference_hashes.values()),
                                       'matching_file_occurrences': sum((hashes & reference_hashes).values()),
                                       'same_sha256_multiset': hashes == reference_hashes,
                                       'note': 'Same bytes do not establish labels or executable mining entry points'},
              'inventory_source': str(inventory), 'output_directory': str(root),
              'code_revision': subprocess.check_output(['git', '-C', str(code), 'rev-parse', 'HEAD'], text=True, timeout=15).strip(),
              'wasm_execution': 'not run', 'detection': 'not performed',
              'limits': 'Host hints from import names only; groups overlap; browser-only behavior and entry semantics not proven'}
    (root / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', root / 'summary.json')


if __name__ == '__main__':
    main()
