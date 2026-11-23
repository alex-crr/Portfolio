"""Checks build.load_entries on throwaway project files. Run: python3 design/test_build.py"""
import pathlib, sys, tempfile
sys.dont_write_bytecode = True  # keep design/ free of __pycache__
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from build import load_entries

BASE = 'title = "{}"\ndwg = "{}"\nperiod = "{}"\nstatus = "{}"\ndesc = "x"\n'
with tempfile.TemporaryDirectory() as tmp:
    d = pathlib.Path(tmp)
    put = lambda name, text: (d / name).write_text(text, encoding='utf-8')
    put('old.toml', BASE.format('Old', 'AC-L01', '2020', 'DONE'))
    put('now.toml', BASE.format('Now', 'AC-L02', '2024 — PRESENT', 'ACTIVE'))
    put('gone.toml', BASE.format('Gone', 'AC-V01', '2023', 'ABANDONED'))
    put('hidden.toml', 'draft = true\n' + BASE.format('Hidden', 'AC-L03', '2026', 'ACTIVE'))
    put('_template.toml', 'ignored = true\n')
    entries = load_entries(d)
    assert [e['id'] for e in entries] == ['now', 'old', 'gone'], entries
    assert [e['group'] for e in entries] == ['active', 'released', 'void'], entries

    put('typo.toml', BASE.format('Typo', 'AC-L01', '2026', 'SHIPPED'))
    try:
        load_entries(d)
        raise AssertionError('a bad file was accepted')
    except SystemExit as x:
        assert 'status "SHIPPED"' in str(x) and 'share dwg "AC-L01"' in str(x), x
print('build checks pass')
