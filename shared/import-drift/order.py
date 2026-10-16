#!/usr/bin/env python3
"""Plan dependency-first source reading without executing the inspected Python."""

import argparse
import importlib.util
import json
from pathlib import Path
import sys


SCOPE = ('Reading waves describe explicit static local imports, not a Python execution '
         'or initialization order. Cyclic modules stay together; their member order is '
         'alphabetical only. Missing imports, parse failures, collisions, dynamic '
         'loading and implicit package initialization can hide dependencies. '
         'Conditional imports are included even when never executed. Warnings cover '
         'the entire scanned root, including modules outside a selected closure. '
         'Inspect the warnings and source hashes before acting on this plan.')


def load_budget():
    import budget
    return budget


def plan(report, starts=None):
    """Condense the mapper's cyclic SCCs, then peel dependency-free waves.

    ``report`` is a complete Import Map result. Its iterative SCC traversal
    reports all cyclic components; every other module is a singleton component.
    No source reads or imports occur in this function.
    """
    records = {record['module']: record for record in report['modules']}
    starts = sorted(set(starts or []))
    for name in starts:
        if name not in records:
            raise ValueError('unknown local module: ' + name)
    graph = {name: set() for name in records}
    for edge in report['edges']:
        graph[edge['from']].add(edge['to'])

    selected = set(records) if not starts else set(starts)
    pending = list(starts)
    while pending:
        for target in graph[pending.pop()]:
            if target not in selected:
                selected.add(target)
                pending.append(target)

    components = [sorted(group) for group in report['cycles'] if group[0] in selected]
    grouped = {name for group in components for name in group}
    components.extend([name] for name in sorted(selected - grouped))
    components.sort()
    membership = {name: group[0] for group in components for name in group}
    dependencies = {group[0]: set() for group in components}
    dependents = {group[0]: set() for group in components}
    for source in sorted(selected):
        for target in graph[source]:
            left, right = membership[source], membership[target]
            if left != right:
                dependencies[left].add(right)
                dependents[right].add(left)

    remaining = {key: len(value) for key, value in dependencies.items()}
    ready = sorted(key for key, count in remaining.items() if count == 0)
    waves, wave_by_group = [], {}
    while ready:
        number = len(waves) + 1
        waves.append({'number': number, 'groups': ready})
        following = set()
        for key in ready:
            wave_by_group[key] = number
            for dependent in dependents[key]:
                remaining[dependent] -= 1
                if remaining[dependent] == 0:
                    following.add(dependent)
        ready = sorted(following)
    if len(wave_by_group) != len(components):
        raise ValueError('inconsistent map: ungrouped cycle prevents a complete plan')

    groups = []
    for members in components:
        key = members[0]
        groups.append({'id': key, 'wave': wave_by_group[key],
                       'cyclic': len(members) > 1 or key in graph[key],
                       'modules': [{'module': name, 'path': records[name]['path'],
                                    'entrypoint': records[name]['entrypoint']}
                                   for name in members],
                       'dependencies': sorted(dependencies[key])})
    groups.sort(key=lambda group: (group['wave'], group['id']))

    # Index import sites once, rather than rescanning all statements per edge.
    evidence = {}
    for source in sorted(selected):
        record = records[source]
        for item in record['imports']:
            target = item.get('resolved')
            if target in graph[source]:
                evidence.setdefault((source, target), []).append(
                    {'path': record['path'], 'line': item['line'], 'target': item['target']})
    edges = []
    for source in sorted(selected):
        for target in sorted(graph[source]):
            sites = evidence.get((source, target))
            if not sites:
                raise ValueError('missing source evidence: ' + source + ' -> ' + target)
            edges.append({'from': source, 'to': target,
                          'from_group': membership[source], 'to_group': membership[target],
                          'sites': sorted(sites, key=lambda site: (site['path'], site['line'], site['target']))})
    return {'selection': {'from': starts, 'mode': 'dependency_closure' if starts else 'all'},
            'waves': waves, 'groups': groups, 'edges': edges,
            'issues': report['issues'], 'cycles': report['cycles'],
            'dynamic_imports': [{'module': record['module'], 'path': record['path'], 'line': line}
                                for record in report['modules']
                                for line in record['dynamic_import_lines']],
            'summary': dict(report['summary'], selected_module_count=len(selected),
                            selected_edge_count=len(edges), group_count=len(groups),
                            wave_count=len(waves)), 'scope': SCOPE}


def format_text(result):
    summary = result['summary']
    lines = [f"Reading plan: {summary['selected_module_count']} of {summary['module_count']} modules, "
             f"{summary['group_count']} groups, {summary['wave_count']} dependency-first waves"]
    if result['selection']['from']:
        lines.append('Dependency closure from: ' + ', '.join(result['selection']['from']))
    by_id = {group['id']: group for group in result['groups']}
    for wave in result['waves']:
        lines.append(f"Wave {wave['number']}:")
        for key in wave['groups']:
            group = by_id[key]
            lines.append('  Group ' + key + (' [cycle: review together]' if group['cyclic'] else ''))
            for module in group['modules']:
                suffix = ' [entry point]' if module['entrypoint'] else ''
                lines.append(f"    {module['module']} ({module['path']}){suffix}")
            if group['dependencies']:
                lines.append('    Depends on groups: ' + ', '.join(group['dependencies']))
    if not result['groups']:
        lines.append('No mapped modules; check the import root and inventory.')
    lines.append(f"Warnings across scanned root: {len(result['issues'])} issues, "
                 f"{len(result['dynamic_imports'])} dynamic calls, {len(result['cycles'])} cyclic components")
    for issue in result['issues']:
        lines.append(f"  {issue['path']}:{issue.get('line') or '?'}: {issue['type']} "
                     + str(issue.get('target', issue.get('detail', ''))))
    for item in result['dynamic_imports']:
        lines.append(f"  {item['path']}:{item['line']}: dynamic import call")
    for cycle in result['cycles']:
        lines.append('  Cycle: ' + ', '.join(cycle))
    lines.append(SCOPE)
    return '\n'.join(lines)


def main(argv=None):
    budget = load_budget()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path, help='explicit import root within current workspace')
    parser.add_argument('--from', dest='starts', action='append', metavar='MODULE',
                        help='restrict plan to this module and its dependencies; repeatable')
    parser.add_argument('--json', action='store_true', help='include source evidence and snapshot hashes')
    parser.add_argument('--strict', action='store_true', help='exit 1 for warnings or cycles anywhere in scan')
    for name, value in budget.DEFAULTS.items():
        parser.add_argument('--max-' + name.replace('_', '-'), type=int, default=value, dest=name)
    args = parser.parse_args(argv)
    try:
        scan = budget.scan(args.root, {name: getattr(args, name) for name in budget.DEFAULTS})
        result = dict(plan(scan['map'], args.starts), status='complete',
                      inventory=scan['inventory'], limits=scan['limits'], collection_scope=scan['scope'])
    except (OSError, ValueError, RuntimeError, RecursionError) as exc:
        error = exc.evidence if isinstance(exc, budget.BudgetExceeded) else {
            'type': 'scan_error', 'detail': str(exc)}
        if args.json:
            print(json.dumps({'status': 'refused', 'error': error}, indent=2))
        else:
            print('import-order: ' + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else format_text(result))
    warnings = result['issues'] or result['dynamic_imports'] or result['cycles']
    return int(bool(args.strict and warnings))


if __name__ == '__main__':
    sys.exit(main())
