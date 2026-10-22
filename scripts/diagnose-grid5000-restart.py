#!/usr/bin/env python3
"""Read-only recovery inventory after node restart; no build, checkout or execution."""
import hashlib
import json
import platform
from pathlib import Path
import shutil

BASE = Path('/srv/storage/killerdroid@storage3.rennes.grid5000.fr/datasets/Andromatch_Paper/SOK_WebAsssembly_2025_Grid5000/DualGraphWasm/Dataset_Dynamic')
RUN = BASE / 'resultats_minethrottle/run-20261021T150736Z-u4tlcbi3'
PATHS = [BASE, BASE / 'tests/Minethrole-reproduction.GPLllk', RUN, BASE / 'Data/Swamped_10_',
         Path('/tmp/minethrottle71-work-rwkni3hv'), Path('/tmp/minethrottle71-tools-li2ldh40'),
         Path('/tmp/minethrottle71-browser-test-_ysw60o_'),
         Path('/tmp/minethrottle71-clang-stage-ytr8ddcf'),
         Path('/tmp/minethrottle71-sysroot-stage-vgj9pyhu'),
         Path('/tmp/minethrottle71-gn-jz9srypw')]
print('Host:', platform.node())
for path in PATHS:
    print(json.dumps({'path': str(path), 'exists': path.exists(), 'symlink': path.is_symlink()}))
for name in ['synthetic-nosandbox-q2ijdkvx', 'synthetic-cpu-audit-4mxrylts', 'decision-readiness-brpgr8zj']:
    path = RUN / 'raw' / name / 'result.json'
    if path.is_file():
        try:
            result = json.loads(path.read_text())
            print(json.dumps({'report': str(path), 'status': result.get('status')}))
        except (OSError, ValueError) as error:
            print('Report unreadable:', path, str(error))
work = Path('/tmp/minethrottle71-work-rwkni3hv')
source = work / 'src/v8/src/wasm/module-compiler.cc'
if source.is_file():
    text = source.read_text()
    print(json.dumps({'source': str(source), 'defense_true_present': 'bool is_defensive = true;' in text,
                      'decision_trace_present': 'MINETHROTTLE_DECISION module=' in text}))
for path in [Path('/tmp/minethrottle71-browser-test-_ysw60o_/browser/chrome'),
             work / 'src/out/MineThrottle71-config-cp8f0qce/chrome']:
    if path.is_file():
        digest = hashlib.sha256()
        with path.open('rb') as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b''):
                digest.update(chunk)
        print(json.dumps({'binary': str(path), 'sha256': digest.hexdigest()}))
print('System commands:', {name: shutil.which(name) for name in ['git', 'python2', 'ninja', 'ccache', 'gperf', 'bison', 'c++', 'runuser']})
print('END: read-only inspection; no recovery mutation or browser execution')
