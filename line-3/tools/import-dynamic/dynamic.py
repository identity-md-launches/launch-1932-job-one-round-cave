#!/usr/bin/env python3
"""Inventory dynamic-import call syntax without executing inspected Python code."""
import argparse
import ast
import importlib.util
import json
from pathlib import Path
import sys

SCOPE = ('Syntactic candidates only: bindings, scope, control flow, rebinding and runtime '
         'search paths are not evaluated. Aliases are collected file-wide, including '
         'conditional and nested imports; a match may be shadowed or precede its binding. '
         'Only direct __import__, importlib.import_module, builtins.__import__ and '
         'explicit aliases of these are recognized. getattr, exec, wrapper functions '
         'and other loaders can be missed. Literal names are not evidence that a call '
         'runs or succeeds. Local candidates are exact source-name matches, not graph '
         'edges. No package discovery, source execution or environment reads occur.')


def load_budget():
    path = Path(__file__).resolve().parents[1] / 'import-budget' / 'budget.py'
    spec = importlib.util.spec_from_file_location('line3_dynamic_budget', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def spelling(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.value.id + '.' + node.attr
    return None


def argument(call, position, keyword, default=None):
    """Never guess positional bindings after a starred argument or ** mapping."""
    matches = [item.value for item in call.keywords if item.arg == keyword]
    unpacked = any(item.arg is None for item in call.keywords)
    starred = any(isinstance(item, ast.Starred) for item in call.args[:position + 1])
    positional = call.args[position] if len(call.args) > position and not starred else None
    if unpacked or starred or len(matches) > 1 or (positional is not None and matches):
        return {'kind': 'unknown_arguments'}
    value = positional if positional is not None else matches[0] if matches else None
    if value is None:
        return {'kind': 'default', 'value': default}
    if isinstance(value, ast.Constant) and type(value.value) in (str, int, type(None)):
        return {'kind': 'literal', 'value': value.value}
    return {'kind': 'computed', 'syntax': type(value).__name__}


def aliases(tree):
    found = {'__import__': {'__import__'}, 'importlib.import_module': {'import_module'},
             'builtins.__import__': {'__import__'}}
    evidence = []
    for node in ast.walk(tree):
        additions = []
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name == 'importlib':
                    additions.append(((item.asname or item.name) + '.import_module', 'import_module'))
                elif item.name == 'builtins':
                    additions.append(((item.asname or item.name) + '.__import__', '__import__'))
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            for item in node.names:
                if (node.module, item.name) in {('importlib', 'import_module'), ('builtins', '__import__')}:
                    additions.append((item.asname or item.name, item.name))
        for name, api in additions:
            found.setdefault(name, set()).add(api)
            evidence.append({'line': node.lineno, 'spelling': name, 'api': api})
    return found, sorted(evidence, key=lambda item: (item['line'], item['spelling'], item['api']))


def classify(name, api, call, catalog):
    if name['kind'] not in ('literal', 'default'):
        return None, 'computed_or_unbound_arguments'
    target = name.get('value')
    if not isinstance(target, str) or not target:
        return None, 'invalid_or_missing_literal_name'
    if api == '__import__':
        level = argument(call, 4, 'level', 0)
        if level['kind'] not in ('literal', 'default') or type(level.get('value')) is not int or level['value'] != 0:
            return None, 'relative_or_unknown_level'
        if target.startswith('.'):
            return None, 'invalid_absolute_name'
    elif target.startswith('.'):
        package = argument(call, 1, 'package')
        if package['kind'] != 'literal' or not isinstance(package.get('value'), str) or not package['value']:
            return None, 'relative_context_unknown'
        try:
            target = importlib.util.resolve_name(target, package['value'])
        except (ImportError, ValueError):
            return None, 'invalid_relative_name'
    paths = catalog.get(target, [])
    return target, ('ambiguous_local_sources' if len(paths) > 1 else
                    'local_source_candidate' if paths else 'nonlocal_or_missing')


def inspect_sources(sources, mapper):
    catalog = {}
    for path in sorted(sources):
        name = mapper.module_name(Path(path))
        if name:
            catalog.setdefault(name, []).append(path)
    calls, issues, alias_evidence = [], [], []
    for path, source in sorted(sources.items()):
        try:
            tree = ast.parse(source, filename=path)
        except (SyntaxError, UnicodeError, ValueError) as exc:
            issues.append({'path': path, 'type': 'parse_error',
                           'line': getattr(exc, 'lineno', None), 'detail': str(exc)})
            continue
        names, bindings = aliases(tree)
        alias_evidence.extend(dict(item, path=path) for item in bindings)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            callee = spelling(node.func)
            if callee not in names:
                continue
            apis = sorted(names[callee])
            name = argument(node, 0, 'name')
            target, kind = (classify(name, apis[0], node, catalog) if len(apis) == 1
                            else (None, 'ambiguous_api_alias'))
            item = {'path': path, 'line': node.lineno, 'column': node.col_offset,
                    'callee': callee, 'api_candidates': apis, 'binding_verified': False,
                    'name_argument': name, 'classification': kind,
                    'target_candidate': target, 'local_paths': catalog.get(target, [])}
            calls.append(item)
    calls.sort(key=lambda item: (item['path'], item['line'], item['column']))
    return {'calls': calls, 'issues': issues, 'alias_evidence': alias_evidence,
            'summary': {'call_sites': len(calls), 'parse_issues': len(issues),
                        'local_candidates': sum(c['classification'] == 'local_source_candidate' for c in calls)}}


def analyze(root, limits=None):
    budget = load_budget()
    mapper = budget.load_mapper()
    limits = dict(budget.DEFAULTS if limits is None else limits)
    sources, inventory = budget.collect(root, limits, mapper.SKIP_DIRS)
    return dict(inspect_sources(sources, mapper), status='complete', limits=limits,
                inventory=inventory, scope=SCOPE, collection_scope=budget.SCOPE)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--strict', action='store_true', help='exit 1 if any candidate or parse issue exists')
    budget = load_budget()
    for name, default in budget.DEFAULTS.items():
        parser.add_argument('--max-' + name.replace('_', '-'), dest=name, type=int, default=default)
    args = parser.parse_args(argv)
    try:
        result = analyze(args.root, {name: getattr(args, name) for name in budget.DEFAULTS})
    except (OSError, ValueError, RuntimeError, RecursionError) as exc:
        print(json.dumps({'status': 'refused', 'error': getattr(exc, 'evidence',
                         {'type': 'scan_error', 'detail': str(exc)})}, indent=2))
        return 2
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for call in result['calls']:
            print(f"{call['path']}:{call['line']}:{call['column']} {call['callee']} — "
                  f"{call['classification']} {call['target_candidate']!r}")
        for issue in result['issues']:
            print('Issue: ' + json.dumps(issue))
        print(json.dumps(result['summary'], sort_keys=True))
        print(SCOPE)
    return int(bool(args.strict and (result['calls'] or result['issues'])))


if __name__ == '__main__':
    sys.exit(main())
