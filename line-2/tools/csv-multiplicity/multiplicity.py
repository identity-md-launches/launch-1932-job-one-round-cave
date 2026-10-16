#!/usr/bin/env python3
"""Compare exact CSV row multiplicities within keys, without pairing identities."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys


def _engine():
    source = Path(__file__).resolve().parents[1] / 'csv-reconcile' / 'reconcile.py'
    spec = importlib.util.spec_from_file_location('multiplicity_reconciler', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


engine = _engine()


def compare(before, after, keys):
    """Count complete row variants. Occurrence lists are evidence, not matches."""
    if not keys or any(not key for key in keys) or len(set(keys)) != len(keys):
        raise engine.InputError('provide distinct, nonempty key columns')
    before_header, before_groups, before_count = engine.load_table(before, keys)
    after_header, after_groups, after_count = engine.load_table(after, keys)
    before_columns, after_columns = set(before_header), set(after_header)
    if before_columns != after_columns:
        raise engine.InputError(
            'schema mismatch: full-row comparison requires the same column names; '
            'only in before: ' + json.dumps(sorted(before_columns - after_columns)) +
            '; only in after: ' + json.dumps(sorted(after_columns - before_columns)))
    columns = sorted(before_columns)
    summary = {
        'before_records': before_count, 'after_records': after_count,
        'key_groups': 0, 'duplicate_key_groups': 0, 'empty_key_groups': 0,
        'retained_copies': 0, 'before_surplus_copies': 0, 'after_surplus_copies': 0,
    }
    groups = []

    def occurrences(rows):
        variants = {}
        for row in rows:
            value = tuple(row['values'][column] for column in columns)
            variants.setdefault(value, []).append(row['record'])
        return variants

    for key in sorted(before_groups.keys() | after_groups.keys()):
        before_rows = before_groups.get(key, [])
        after_rows = after_groups.get(key, [])
        before_variants, after_variants = occurrences(before_rows), occurrences(after_rows)
        empty_columns = [column for column, value in zip(keys, key) if value == '']
        duplicate = len(before_rows) > 1 or len(after_rows) > 1
        group_counts = {'retained_copies': 0, 'before_surplus_copies': 0,
                        'after_surplus_copies': 0}
        variants = []
        for value in sorted(before_variants.keys() | after_variants.keys()):
            before_records = before_variants.get(value, [])
            after_records = after_variants.get(value, [])
            bc, ac = len(before_records), len(after_records)
            counts = {'retained_copies': min(bc, ac),
                      'before_surplus_copies': max(bc - ac, 0),
                      'after_surplus_copies': max(ac - bc, 0)}
            variants.append({'values': dict(zip(columns, value)),
                             'before_count': bc, 'after_count': ac,
                             'before_records': before_records, 'after_records': after_records,
                             **counts})
            for name, count in counts.items():
                group_counts[name] += count
                summary[name] += count
        groups.append({'key': dict(zip(keys, key)), 'duplicate_key': duplicate,
                       'empty_key_columns': empty_columns,
                       'before_count': len(before_rows), 'after_count': len(after_rows),
                       **group_counts, 'variants': variants})
        summary['key_groups'] += 1
        summary['duplicate_key_groups'] += int(duplicate)
        summary['empty_key_groups'] += int(bool(empty_columns))
    return {'format': 'csv-multiplicity/v1', 'keys': list(keys), 'columns': columns,
            'multiset_equal': not (summary['before_surplus_copies'] or
                                   summary['after_surplus_copies']),
            'identity_matching': False, 'summary': summary, 'groups': groups}


def render_text(report):
    # Every input-derived string is JSON quoted, including terminal controls.
    def quoted(value):
        return json.dumps(value, ensure_ascii=True, sort_keys=True)

    state = 'equal' if report['multiset_equal'] else 'different'
    lines = ['CSV row multisets: ' + state,
             'Keys: ' + quoted(report['keys']),
             'Columns: ' + quoted(report['columns']),
             'Summary: ' + quoted(report['summary'])]
    for group in report['groups']:
        lines.extend(['', 'Key: ' + quoted(group['key']),
                      'Duplicate key: ' + ('yes' if group['duplicate_key'] else 'no'),
                      'Empty key columns: ' + quoted(group['empty_key_columns'])])
        for variant in group['variants']:
            lines.append('  Row: ' + quoted(variant['values']))
            lines.append('    Counts: before {before_count}; after {after_count}; '
                         'retained {retained_copies}; before surplus {before_surplus_copies}; '
                         'after surplus {after_surplus_copies}.'.format(**variant))
            lines.append('    Before records: ' + quoted(variant['before_records']) +
                         '; after records: ' + quoted(variant['after_records']))
    lines.append('Retained copies describe equal row values, not surviving identities. '
                 'No occurrences paired; no updates inferred.')
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', help='baseline UTF-8 CSV within the current directory')
    parser.add_argument('after', help='candidate UTF-8 CSV within the current directory')
    parser.add_argument('--key', action='append', required=True, help='repeat for a composite key')
    parser.add_argument('--format', choices=('json', 'text'), default='json')
    parser.add_argument('--fail-on-ambiguous', action='store_true',
                        help='return 1 when any key is duplicated or empty')
    args = parser.parse_args(argv)
    try:
        report = compare(args.before, args.after, args.key)
    except (OSError, ValueError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 2
    print(render_text(report) if args.format == 'text' else
          json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2))
    ambiguous = (report['summary']['duplicate_key_groups'] or
                 report['summary']['empty_key_groups'])
    return 0 if report['multiset_equal'] and not (args.fail_on_ambiguous and ambiguous) else 1


if __name__ == '__main__':
    sys.exit(main())
