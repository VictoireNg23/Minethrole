#!/usr/bin/env python3
"""Report non-regular archive entries without extracting or executing anything."""
import argparse
import collections
import hashlib
from pathlib import Path
import tarfile


def inspect(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    print('Archive:', path)
    print('SHA-256:', digest.hexdigest())
    counts = collections.Counter()
    with tarfile.open(path, mode='r:*') as archive:
        print('Git archive comment:', repr(archive.pax_headers.get('comment')))
        for member in archive:
            kind = ('file' if member.isfile() else 'directory' if member.isdir()
                    else 'symlink' if member.issym() else 'hardlink' if member.islnk() else 'special')
            counts[kind] += 1
            if kind not in ('file', 'directory'):
                print('Entry:', repr(member.name), 'type:', kind, 'target:', repr(member.linkname))
    print('Counts:', dict(counts))
    print('END: inspection only; no archive entry extracted, followed or executed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    inspect(parser.parse_args().archive)


if __name__ == '__main__':
    main()
