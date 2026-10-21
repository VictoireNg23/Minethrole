#!/usr/bin/env python3
"""Read an existing log and print bounded, numbered error contexts."""
import argparse
import re
from collections import deque

ERROR = re.compile(r'fatal:|\berror:|traceback \(most recent call last\)|returned non-zero|preservation.*(?:blocked|refus)|\b(?:exception|failed|failure)\b', re.I)


def contexts(lines, radius=4, limit=40):
    before = deque(maxlen=radius)
    through = emitted = matches = 0
    for number, line in enumerate(lines, 1):
        if ERROR.search(line):
            matches += 1
            if matches <= limit:
                for previous, text in before:
                    if previous > emitted:
                        yield previous, text
                        emitted = previous
                through = number + radius
        if number <= through and number > emitted:
            yield number, line
            emitted = number
        before.append((number, line))
    yield None, 'Error matches: %d; contexts limited to first %d matches.' % (matches, limit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log')
    args = parser.parse_args()
    print('Log:', args.log)
    with open(args.log, encoding='utf-8', errors='replace') as log:
        for number, line in contexts(log):
            print(('%d: ' % number if number is not None else '') + line.rstrip()[:2000])


if __name__ == '__main__':
    main()
