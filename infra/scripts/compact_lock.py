"""Keep generated uv lockfiles under the project line cap without dropping data."""

import argparse
import tomllib
from pathlib import Path


def compact(source):
    result = []
    pending = []
    for line in source.splitlines():
        if pending:
            pending.append(line.strip())
            if line.strip() == ']':
                result.append(' '.join(pending))
                pending = []
        elif line.rstrip().endswith('= ['):
            pending.append(line.strip())
        else:
            result.append(line)
    if pending:
        raise ValueError('Unclosed TOML array')
    output = '\n'.join(result) + '\n'
    if tomllib.loads(source) != tomllib.loads(output):
        raise ValueError('Lockfile compaction changed metadata')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', nargs='?', default='uv.lock')
    path = Path(parser.parse_args().path)
    path.write_text(compact(path.read_text()))
    print(f'{path}: {len(path.read_text().splitlines())} lines; all lock metadata preserved')
