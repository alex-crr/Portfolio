"""Rebuild ../index.html from portfolio.dc.html (the editable design source).

1. Reads ../projects/*.toml (one file per project, see _template.toml), checks
   them and writes them into the ENTRIES block of portfolio.dc.html.
2. The bundle in index.html holds a compiled copy of the dc page as a JSON
   string. Only the part after </helmet> is replaced; the bundle's own head
   (inlined fonts, runtime) is kept.
Run: python3 design/build.py   (Python 3.11+ for tomllib)
"""
import json, re, sys, pathlib, tomllib

here = pathlib.Path(__file__).parent
root = here.parent

# status -> lookup group. PAUSED and after go to the void sheet.
STATUS = {'ACTIVE': 'active', 'LAUNCHED': 'released', 'DONE': 'released',
          'PAUSED': 'void', 'ABANDONED': 'void', 'FAILED': 'void', 'SUPERSEDED': 'void', 'HANDED OVER': 'void'}
REQUIRED = ('title', 'dwg', 'period', 'status', 'desc')
KNOWN = set(REQUIRED) | {
    'tags', 'link', 'partners', 'draft', 'why', 'cause', 'carried', 'feeds', 'img',
    'num', 'short', 'field', 'photo', 'raw', 'overview', 'details', 'tech', 'thirdLabel', 'third', 'table',
    'prose', 'notesTitle', 'cards', 'learnIntro', 'learnings', 'learnOutro', 'gallery', 'linkText', 'linkLabel'}


def load_entries(folder):
    entries, errors = [], []
    for f in sorted(pathlib.Path(folder).glob('*.toml')):
        if f.name.startswith('_'):
            continue
        try:
            e = tomllib.loads(f.read_text(encoding='utf-8'))
        except tomllib.TOMLDecodeError as x:
            errors.append(f'{f.name}: {x}')
            continue
        if e.pop('draft', False):
            continue
        errors += [f'{f.name}: missing "{k}"' for k in REQUIRED if k not in e]
        if e.get('status') not in STATUS:
            errors.append(f'{f.name}: status "{e.get("status")}" is not one of {", ".join(STATUS)}')
        if not isinstance(e.get('tags', []), list):
            errors.append(f'{f.name}: tags must be a list, like tags = ["hci"]')
        for k in sorted(set(e) - KNOWN):
            print(f'warning: {f.name}: unknown field "{k}" is ignored by the page')
        e['id'] = f.stem
        e['group'] = STATUS.get(e.get('status'))
        e['tags'] = [str(t).lower() for t in e.get('tags', [])] if isinstance(e.get('tags', []), list) else []
        entries.append(e)
    for key in ('dwg', 'num'):
        seen = {}
        for e in entries:
            if e.get(key):
                if e[key] in seen:
                    errors.append(f'{e["id"]}.toml and {seen[e[key]]}.toml share {key} "{e[key]}"')
                seen[e[key]] = e['id']
    ids = {e['id'] for e in entries}
    errors += [f'{e["id"]}.toml: feeds "{e["feeds"]}" matches no project file' for e in entries if e.get('feeds') and e['feeds'] not in ids]
    if errors:
        sys.exit('projects/ has errors, nothing was built:\n  ' + '\n  '.join(errors))

    def order(e):  # group, featured first (by num), then most recent: PRESENT, last year, first year
        p = str(e['period'])
        ys = [int(y) for y in re.findall(r'\d{4}', p)] or [0]
        end = 9999 if 'PRESENT' in p.upper() else ys[-1]
        rank = {'active': 0, 'released': 1, 'void': 2}[e['group']]
        return (rank, e['status'] == 'PAUSED', 'num' not in e, e.get('num', ''), -end, -ys[0], e['title'].lower())
    entries.sort(key=order)
    return entries


def build():
    entries = load_entries(root / 'projects')
    tags = {}
    for e in entries:
        for t in e['tags']:
            tags[t] = tags.get(t, 0) + 1
    print(f'{len(entries)} projects; tags:', ', '.join(f'{t} {n}' for t, n in sorted(tags.items())))

    src_path = here / 'portfolio.dc.html'
    src = src_path.read_text(encoding='utf-8')
    BLOCK = re.compile(r'(// @entries:start[^\n]*\n).*?(// @entries:end)', re.S)
    if not BLOCK.search(src):
        sys.exit('portfolio.dc.html has lost its // @entries:start and // @entries:end lines')
    data = 'const ENTRIES = [\n' + ',\n'.join('  ' + json.dumps(e, ensure_ascii=False) for e in entries) + '\n];\n'
    src = BLOCK.sub(lambda m: m.group(1) + data.replace('</', '<\\/') + m.group(2), src)
    src_path.write_text(src, encoding='utf-8')

    idx = root / 'index.html'
    bundle = idx.read_text(encoding='utf-8')

    TPL = re.compile(r'(<script type="__bundler/template"[^>]*>)(.*?)(</script>)', re.S)
    tpl = json.loads(TPL.search(bundle).group(2))

    body = src.split('</helmet>', 1)[1]
    markup, script = body.split('<script type="text/x-dc"', 1)
    # the bundler's compile step: camelCase attrs -> sc-camel-kebab, no </img>
    markup = re.sub(r' ([a-z]+[A-Z][A-Za-z]*)=',
                    lambda m: ' sc-camel-' + re.sub(r'[A-Z]', lambda x: '-' + x.group().lower(), m.group(1)) + '=',
                    markup).replace('</img>', '').replace('</input>', '')
    tpl = tpl.split('</helmet>', 1)[0] + '</helmet>' + markup + '<script type="text/x-dc"' + script.replace(' data-dc-script data-props', ' data-dc-script="" data-props', 1)

    bundle = TPL.sub(lambda m: m.group(1) + json.dumps(tpl).replace('</', '<\\/') + m.group(3), bundle)
    idx.write_text(bundle, encoding='utf-8')
    print('index.html rebuilt,', len(bundle), 'bytes')


if __name__ == '__main__':
    build()
