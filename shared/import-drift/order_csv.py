#!/usr/bin/env python3
"""Export dependency reading waves as exact keyed CSV for offline review."""
import argparse
import csv
import io
import json
import sys
import budget
import import_map
import order
import reconcile

COLUMNS = ('module', 'path', 'group', 'wave', 'cyclic', 'dependencies', 'source_sha256')


def snapshot(root, starts=None, limits=None):
    scan = budget.scan(root, limits, mapper=import_map)
    if any(i['type'] == 'module_collision' for i in scan['map']['issues']):
        raise ValueError('module collision prevents unique CSV keys')
    result = order.plan(scan['map'], starts)
    hashes = {i['path']: i['sha256'] for i in scan['inventory']['manifest']}
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator='\n')
    writer.writeheader()
    for group in result['groups']:
        for module in group['modules']:
            writer.writerow({'module': module['module'], 'path': module['path'],
                             'group': group['id'], 'wave': group['wave'],
                             'cyclic': str(group['cyclic']).lower(),
                             'dependencies': json.dumps(group['dependencies'], ensure_ascii=True, separators=(',', ':')),
                             'source_sha256': hashes[module['path']]})
    evidence = dict(result, schema='reading-order-csv/v1', inventory=scan['inventory'],
                    limits=scan['limits'], collection_scope=scan['scope'])
    return stream.getvalue(), evidence


def compare(before, after):
    for path in (before, after):
        columns, groups, _ = reconcile.load_table(path, ('module',))
        if columns != list(COLUMNS):
            raise ValueError('expected reading-order-csv/v1 columns')
        if any(not key[0] or len(rows) != 1 for key, rows in groups.items()):
            raise ValueError('module keys must be unique and nonempty')
    return reconcile.reconcile(before, after, ('module',))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    snap = commands.add_parser('snapshot')
    snap.add_argument('root')
    snap.add_argument('--from', dest='starts', action='append')
    for name, default in budget.DEFAULTS.items():
        snap.add_argument('--max-' + name.replace('_', '-'), type=int, default=default, dest=name)
    diff = commands.add_parser('compare')
    diff.add_argument('before')
    diff.add_argument('after')
    args = parser.parse_args(argv)
    try:
        if args.command == 'snapshot':
            text, evidence = snapshot(args.root, args.starts, {k: getattr(args, k) for k in budget.DEFAULTS})
            print(json.dumps(evidence, ensure_ascii=True, separators=(',', ':')), file=sys.stderr)
            sys.stdout.write(text)
            return int(bool(evidence['issues'] or evidence['cycles'] or evidence['dynamic_imports']))
        result = compare(args.before, args.after)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return int(not result['equal'])
    except (OSError, ValueError, RuntimeError, RecursionError) as error:
        print(json.dumps({'schema': 'reading-order-csv/v1', 'status': 'refused', 'error': str(error)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
