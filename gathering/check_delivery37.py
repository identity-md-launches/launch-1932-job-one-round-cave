#!/usr/bin/env python3
"""Offline structure and scope checks for Gathering 37; no visual certification."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from check_delivery import Gallery, jpeg_dimensions, png_dimensions


def main():
    wall = Path('artifacts/gathering/wall-v17.png').read_bytes()
    assert wall == Path('artifacts/gathering/wall.png').read_bytes()
    assert png_dimensions(wall) == (1254, 1254)
    assert wall[24:26] == bytes((8, 2))
    digest = hashlib.sha256(wall).hexdigest()
    jpg = Path('dist/gathering/37.jpg').read_bytes()
    assert jpeg_dimensions(jpg) == (512, 512) and len(jpg) < 100000
    record = json.loads(Path('dist/gathering/37.json').read_text())
    assert set(record) == {'name', 'image', 'attributes'}
    assert record['image'] == 'https://api.imd.fun/artifacts/' + digest
    attrs = {a['trait_type']: a['value'] for a in record['attributes']}
    assert len(record['attributes']) == len(attrs) == 6
    assert set(attrs) == {'Cave', 'Wall', 'Number', 'Left behind', 'Meaning', 'One thing'}
    assert attrs['Cave'] == 'Ice' and attrs['Wall'] == 'Gathering'
    assert type(attrs['Number']) is int and attrs['Number'] == 37
    assert attrs['One thing'] == 'Gathering'
    assert json.loads(Path('dist/goals.json').read_text()) == [
        {'line': i, 'goal': Path(f'line-{i}/GOAL.md').read_text().strip()} for i in range(1, 5)]

    content = Path('dist/index.html').read_text()
    gallery = Gallery(content)
    records = {p.relative_to('dist').as_posix(): json.loads(p.read_text())
               for p in Path('dist').glob('*/[0-9][0-9].json')}
    assert len(content.encode()) < 100000
    assert len(gallery.records) == len(records) == 185
    assert set(gallery.records) == set(records)
    assert len(gallery.images) == 85
    assert not set(gallery.tags) & {'script', 'iframe', 'link'}
    assert all(re.fullmatch(r'data:image/jpeg;base64,[A-Za-z0-9+/=]+', src)
               for src in gallery.images)
    for href in gallery.links:
        if href.startswith('#'):
            assert f'id="{href[1:]}"' in content
        elif not href.startswith('https://'):
            assert (Path('dist') / href).is_file(), href
    for name in ('gathering', 'line-1', 'line-2', 'line-3', 'line-4'):
        painted = [key for key in gallery.records if key.startswith(name+'/')
                   and records[key]['name'] != 'Not painted yet']
        assert painted == sorted(painted, reverse=True)
        for n in range(2, 22):
            path = Path('dist', name, f'{n:02}.json')
            assert json.loads(path.read_text()) == {
                'name': 'Not painted yet',
                'image': 'https://api.imd.fun/artifacts/b5e794cb2c70bd232230e389707698c69c2080786d606a13b39f9315c9a90799',
                'attributes': [{'trait_type': 'Cave', 'value': 'Ice'}]}
            assert not path.with_suffix('.jpg').exists()

    image = json.loads(Path('gathering/image-checks37.json').read_text())
    assert image['png']['sha256'] == digest
    assert image['png']['dimensions'] == [1254,1254]
    assert image['jpeg']['dimensions'] == [512,512]
    assert image['preservation']['changed_pixels'] > 0
    assert image['preservation']['outside_rectangle_changed_pixels'] == 0
    assert image['visual_review_completed'] and image['unmet_visual_requirements'] == []
    tests = json.loads(Path('gathering/test-runs37.json').read_text())
    assert tests['ok'] and tests['line_tests'] == 626
    assert tests['shared_tests'] == 114 and tests['gathering_tests'] == 8
    assert tests['sources_unchanged_after_checks']
    trials = json.loads(Path('gathering/current-checks37.json').read_text())
    assert trials['ok'] and len(trials['results']) == 10
    assert all(row['passed'] for row in trials['results'])
    assert Path('gathering/COINS.md').read_text().splitlines()[0] == 'none'
    assert not Path('gathering/coin-order.json').exists()
    assert not Path('gathering/deploy-order.json').exists()

    restricted = ['line-1','line-2','line-3','line-4','dist/line-1','dist/line-2',
                  'dist/line-3','dist/line-4']
    assert not subprocess.run(['git','diff','HEAD','--',*restricted],
                              capture_output=True,check=True).stdout
    changed = subprocess.run(['git','diff','--name-only','HEAD'],
                             capture_output=True,text=True,check=True).stdout.splitlines()
    added = subprocess.run(['git','ls-files','--others','--exclude-standard'],
                           capture_output=True,text=True,check=True).stdout.splitlines()
    for name in set(changed+added):
        if name.startswith('test/scratch/') or name.startswith('artifacts/gathering/'):
            continue
        assert name.split('/')[0] in ('gathering','shared','dist'), name
        assert Path(name).is_file() and Path(name).stat().st_size < 100000, name
    baseline = json.loads(Path('test/scratch/scope37.json').read_text())
    assert baseline == {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for i in range(1,5) for p in Path(f'line-{i}').rglob('*') if p.is_file()}
    report = {'ok':True,'png':{'format':'PNG','mode':'RGB','dimensions':[1254,1254],
                               'bytes':len(wall),'sha256':digest},
              'jpeg':{'format':'JPEG','dimensions':[512,512],'bytes':len(jpg)},
              'gallery_records':185,'painted_previews':85,'placeholders':100,
              'gallery_bytes':len(content.encode()),'line_paths_unchanged':True,
              'tool_suites':48,'cli_trials':10,'unmet_visual_requirements':[]}
    Path('gathering/delivery-checks37.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
