"""Preserve pnpm's YAML data as readable grouped JSON, which is valid YAML."""

import argparse
import json
from pathlib import Path

import yaml


def compact(source):
    data = yaml.safe_load(source)
    lines = ['{']
    for index, (key, value) in enumerate(data.items()):
        prefix = '  ' + json.dumps(key) + ': '
        suffix = ',' if index < len(data) - 1 else ''
        if isinstance(value, dict) and len(value) > 20:
            lines.append(prefix + '{')
            items = list(value.items())
            for offset in range(0, len(items), 3):
                group = items[offset:offset + 3]
                line = ', '.join(json.dumps(k) + ': ' + json.dumps(v, separators=(',', ':'))
                                 for k, v in group)
                lines.append('    ' + line + (',' if offset + 3 < len(items) else ''))
            lines.append('  }' + suffix)
        else:
            lines.append(prefix + json.dumps(value, separators=(',', ':')) + suffix)
    lines.append('}')
    output = '\n'.join(lines) + '\n'
    if yaml.safe_load(output) != data:
        raise ValueError('Compaction altered lockfile data')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', nargs='?', default='pnpm-lock.yaml')
    path = Path(parser.parse_args().path)
    path.write_text(compact(path.read_text()))
    print(f'{path}: {len(path.read_text().splitlines())} lines; all lock metadata preserved')
