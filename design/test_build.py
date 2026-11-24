"""Checks build.load_entries on throwaway v2 project files. Run: python3 design/test_build.py"""
import pathlib, sys, tempfile
sys.dont_write_bytecode = True  # keep design/ free of __pycache__
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build import load_entries

BASE = 'title = "{}"\ndrawing_no = "{}"\nperiod = "{}"\nstatus = "{}"\nsummary = "x"\n'
FEATURED = BASE.format('Big', 'AC-02-BIG', '2024 — PRESENT', 'ACTIVE') + '''tags = ["HCI"]
link = "https://example.com"
[featured]
nav = "BIG"
field = "FIELD"
drawing = "img/a.svg"
photo = "img/b.jpg"
keep_drawing_colours = true
overview = """
One
two.

Three.
"""
[specs]
technologies = ["T"]
highlights_label = "SKILLS"
highlights = ["H"]
[specs.details]
CATEGORY = "Cat"
[specs.table]
"Size" = "1 mm"
[notes]
title = "Add-ins"
text = "P1\\n\\nP2"
[[notes.cards]]
name = "N"
repo = "R"
workspace = "W"
text = "B"
[[gallery]]
caption = "KIT"
image = "img/b.jpg"
alt = "Kit"
[reference]
text = "See it."
button = "GO"
'''


def rejects(name, text, msg):
    put(name, text)
    try:
        load_entries(d / 'projects')
        raise AssertionError(f'{name} was accepted')
    except SystemExit as x:
        assert msg in str(x), x
    (d / 'projects' / name).unlink()


with tempfile.TemporaryDirectory() as tmp:
    d = pathlib.Path(tmp)
    (d / 'projects').mkdir()
    (d / 'img').mkdir()
    for n in ('a.svg', 'b.jpg', 'v.jpg'):
        (d / 'img' / n).write_text('x')
    put = lambda name, text: (d / 'projects' / name).write_text(text, encoding='utf-8')
    put('old.toml', BASE.format('Old', 'AC-L01', '2020', 'DONE'))
    put('now.toml', BASE.format('Now', 'AC-L02', '2024 — PRESENT', 'ACTIVE'))
    put('gone.toml', BASE.format('Gone', 'AC-V01', '2023', 'ABANDONED') + '[void]\ncarried_into = "Big"\nfeeds = "big"\nphoto = "img/v.jpg"\n')
    put('hidden.toml', 'draft = true\nwhatever = 1\n')
    put('big.toml', FEATURED)
    put('_template.toml', 'ignored = true\n')
    entries = load_entries(d / 'projects')
    assert [e['id'] for e in entries] == ['big', 'now', 'old', 'gone'], entries
    assert [e['group'] for e in entries] == ['active', 'active', 'released', 'void'], entries
    assert entries[3] == {'title': 'Gone', 'dwg': 'AC-V01', 'period': '2023', 'status': 'ABANDONED', 'desc': 'x', 'tags': [],
                          'carried': 'Big', 'feeds': 'big', 'img': 'img/v.jpg', 'id': 'gone', 'group': 'void'}, entries[3]
    assert entries[0] == {
        'title': 'Big', 'dwg': 'AC-02-BIG', 'period': '2024 — PRESENT', 'status': 'ACTIVE', 'desc': 'x', 'tags': ['hci'],
        'link': 'https://example.com', 'num': '02', 'short': 'BIG', 'field': 'FIELD', 'img': 'img/a.svg', 'photo': 'img/b.jpg',
        'raw': True, 'overview': ['One two.', 'Three.'],
        'details': [{'k': 'PERIOD', 'v': '2024 — PRESENT'}, {'k': 'CATEGORY', 'v': 'Cat'}],
        'tech': ['T'], 'thirdLabel': 'SKILLS', 'third': ['H'], 'table': [['Size', '1 mm']],
        'notesTitle': 'Add-ins', 'prose': ['P1', 'P2'], 'cards': [{'name': 'N', 'repo': 'R', 'ws': 'W', 'body': 'B'}],
        'gallery': [{'cap': 'FIG. 2 — KIT', 'src': 'img/b.jpg', 'alt': 'Kit'}],
        'linkText': 'See it.', 'linkLabel': 'GO', 'id': 'big', 'group': 'active'}, entries[0]

    rejects('x.toml', FEATURED.replace('[specs.table]', '[specs.tabel]'), 'x.toml: unknown key "specs.tabel"')
    rejects('x.toml', FEATURED.replace('CATEGORY', 'Started'), 'specs.details "Started" is already shown')
    rejects('x.toml', BASE.format('X', 'AC-L09', '2020', 'FAILED'), 'drawing_no "AC-L09" must look like AC-Vnn')
    rejects('x.toml', FEATURED.replace('img/a.svg', 'img/nope.svg'), 'image "img/nope.svg" is not a file')
    rejects('x.toml', BASE.format('X', 'AC-L09', '2020', 'DONE') + '[specs]\n[specs.table]\nA = "1"\n', '[specs] only works with [featured]')
    rejects('x.toml', BASE.format('X', 'AC-L09', '2020', 'ACTIVE') + '[void]\ncause = "SCOPE"\n', '[void] is only for PAUSED and later')
    rejects('x.toml', FEATURED.replace('button = "GO"\n', ''), '[reference] needs a button label')
    rejects('x.toml', FEATURED.replace('text = "P1\\n\\nP2"\n', '').split('[[notes.cards]]')[0] + '[[gallery]]' + FEATURED.split('[[gallery]]')[1], '[notes] needs text or')
    rejects('x.toml', BASE.format('X', 'AC-L01', '2026', 'SHIPPED'), 'status "SHIPPED"')
    rejects('x.toml', BASE.format('X', 'AC-L01', '2026', 'DONE'), 'share drawing_no "AC-L01"')
print('build checks pass')
