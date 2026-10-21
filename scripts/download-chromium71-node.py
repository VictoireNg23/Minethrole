#!/usr/bin/env python3
"""Download checksum-pinned historical Node and WebUI modules; do not extract."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tarfile
import tempfile
import urllib.request


def hook_artifacts(source):
    result = {}
    wanted = {'src/third_party/node/linux/node-linux-x64.tar.gz.sha1',
              'src/third_party/node/node_modules.tar.gz.sha1'}
    for assignment in ast.parse(source).body:
        if not isinstance(assignment, ast.Assign) or not any(isinstance(n, ast.Name) and n.id == 'hooks' for n in assignment.targets):
            continue
        for entry in assignment.value.elts:
            try:
                hook = ast.literal_eval(entry)
            except (ValueError, TypeError):
                continue
            action = hook.get('action', [])
            for path in wanted:
                if path in action and '--bucket' in action:
                    bucket = action[action.index('--bucket') + 1]
                    if bucket not in ('chromium-nodejs/8.9.1', 'chromium-nodejs'):
                        raise ValueError('Unexpected historical Node bucket')
                    result[path] = {'name': hook.get('name'), 'bucket': bucket}
    if set(result) != wanted:
        raise ValueError('Could not identify both original Node hooks')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    args = parser.parse_args()
    root = args.workspace.resolve()
    if not (root / 'preparation.json').is_file():
        raise SystemExit('Expected isolated workspace')
    definitions = hook_artifacts((root / 'src/DEPS').read_text())
    stage = Path(tempfile.mkdtemp(prefix='minethrottle71-node-download-'))
    print('NEW directory (retained):', stage, flush=True)
    report = {'artifacts': [], 'extraction': 'not run', 'build': 'not run'}
    for path, definition in definitions.items():
        item = dict(definition, metadata=path, status='incomplete')
        try:
            expected = (root / path).read_text().strip()
            if not re.fullmatch('[0-9a-f]{40}', expected):
                raise ValueError('Invalid SHA-1 metadata')
            filename = Path(path).name[:-5]
            archive = stage / filename
            url = 'https://storage.googleapis.com/' + definition['bucket'] + '/' + expected
            item.update(path=str(archive), expected_sha1=expected, url=url)
            print('Downloading:', url, flush=True)
            sha1, sha256 = hashlib.sha1(), hashlib.sha256()
            size = 0
            with urllib.request.urlopen(url, timeout=30) as response, archive.open('xb') as output:
                if not response.geturl().startswith('https://'):
                    raise ValueError('Non-HTTPS redirect')
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > 512 * 1024 ** 2:
                        raise ValueError('Archive exceeds 512 MiB limit')
                    output.write(chunk)
                    sha1.update(chunk)
                    sha256.update(chunk)
            if sha1.hexdigest() != expected:
                raise ValueError('Historical SHA-1 mismatch')
            types, first, absolute = Counter(), [], []
            with tarfile.open(archive) as tar:
                for entry in tar:
                    types[str(entry.type)] += 1
                    if len(first) < 12:
                        first.append(entry.name)
                    if entry.issym() and entry.linkname.startswith('/'):
                        absolute.append({'name': entry.name, 'target': entry.linkname})
            item.update(status='downloaded_sha1_verified_manifest_read', bytes=size,
                        sha256=sha256.hexdigest(), member_types=dict(types), first_members=first,
                        absolute_links=absolute[:20])
        except Exception as error:
            item['error'] = str(error)
        report['artifacts'].append(item)
        (stage / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(item, indent=2), flush=True)
    print('Report:', stage / 'result.json')
    return 0 if all(i['status'] == 'downloaded_sha1_verified_manifest_read' for i in report['artifacts']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
