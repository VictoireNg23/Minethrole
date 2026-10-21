#!/usr/bin/env python3
"""Prepare checksum-pinned Chromium test fonts; no build or test execution."""
import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
import urllib.request


def extract_fonts(archive, destination):
    with tarfile.open(archive) as tar:
        entries, names, expanded = [], set(), 0
        for entry in tar:
            name = PurePosixPath(entry.name)
            if str(name) == '.' and entry.isdir():
                continue
            if name.is_absolute() or '..' in name.parts or not name.parts or name.parts[0] != 'test_fonts':
                raise ValueError('Unexpected font archive path: ' + entry.name)
            if not (entry.isfile() or entry.isdir()) or str(name) in names:
                raise ValueError('Unsupported font archive entry: ' + entry.name)
            names.add(str(name))
            expanded += entry.size if entry.isfile() else 0
            if expanded > 1024 ** 3:
                raise ValueError('Expanded fonts exceed 1 GiB')
            entries.append(entry)
        for entry in entries:
            path = destination / entry.name
            if entry.isdir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(entry) as source, path.open('xb') as target:
                    shutil.copyfileobj(source, target)
                path.chmod(0o644)
        return {'entries': len(entries), 'expanded_bytes': expanded}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--run', required=True, type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    run = args.run.resolve(strict=True)
    if not (workspace / 'preparation.json').is_file() or not (run / 'manifest.json').is_file():
        raise SystemExit('Expected isolated workspace and persistent run')
    definitions = ast.parse((workspace / 'src/DEPS').read_text())
    action = None
    for node in definitions.body:
        if isinstance(node, ast.Assign) and any(isinstance(n, ast.Name) and n.id == 'hooks' for n in node.targets):
            for item in node.value.elts:
                try:
                    hook = ast.literal_eval(item)
                except (ValueError, TypeError):
                    continue
                if hook.get('name') == 'test_fonts':
                    action = hook['action']
    if not action or action[action.index('--bucket') + 1] != 'chromium-fonts' or action[action.index('-s') + 1] != 'src/third_party/test_fonts/test_fonts.tar.gz.sha1':
        raise SystemExit('Unexpected historical font hook')
    expected = (workspace / 'src/third_party/test_fonts/test_fonts.tar.gz.sha1').read_text().strip()
    if len(expected) != 40 or any(c not in '0123456789abcdef' for c in expected):
        raise SystemExit('Invalid font SHA-1 metadata')
    target = workspace / 'src/third_party/test_fonts/test_fonts'
    if target.exists() or target.is_symlink() or target.parent.resolve() != target.parent:
        raise SystemExit('Refused occupied or symlinked font target; inspect it first')
    local = Path(tempfile.mkdtemp(prefix='minethrottle71-test-fonts-'))
    logs = Path(tempfile.mkdtemp(prefix='test-fonts-', dir=run / 'logs'))
    result = {'status': 'incomplete', 'local_directory': str(local), 'expected_sha1': expected,
              'build': 'not run', 'native_tests_execution': 'not run'}
    print('New local staging:', local, flush=True)
    try:
        url = 'https://storage.googleapis.com/chromium-fonts/' + expected
        result['url'] = url
        archive = local / 'test_fonts.tar.gz'
        sha1, sha256 = hashlib.sha1(), hashlib.sha256()
        size = 0
        with urllib.request.urlopen(url, timeout=30) as response, archive.open('xb') as output:
            if not response.geturl().startswith('https://'):
                raise ValueError('Non-HTTPS redirect refused')
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > 512 * 1024 ** 2:
                    raise ValueError('Font download exceeds 512 MiB')
                sha1.update(chunk)
                sha256.update(chunk)
                output.write(chunk)
        if sha1.hexdigest() != expected:
            raise ValueError('Historical font SHA-1 mismatch')
        result.update(bytes=size, sha256=sha256.hexdigest())
        result.update(extract_fonts(archive, local))
        if not (local / 'test_fonts/Ahem.ttf').is_file():
            raise ValueError('Ahem.ttf absent after extraction')
        target.symlink_to(local / 'test_fonts', target_is_directory=True)
        result.update(status='historical_test_fonts_prepared', target=str(target))
    except Exception as error:
        result['error'] = str(error)
    (logs / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('Report:', logs / 'result.json')
    return 0 if result['status'] == 'historical_test_fonts_prepared' else 1


if __name__ == '__main__':
    raise SystemExit(main())
