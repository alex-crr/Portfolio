"""Rebuild ../index.html from portfolio.dc.html (the editable design source).

1. Reads ../projects/*.toml (schema v2, one file per project, see _template.toml),
   checks them and translates them into the ENTRIES block of portfolio.dc.html,
   with the old keys the page reads. The build derives the column number (from
   drawing_no), the PERIOD details row, the FIG. numbers and the paragraphs.
   Any error stops the build, with every error listed.
2. Rewrites the page's <meta name="ext-resource-dependency"> tags from the
   local project images (featured drawing/photo, media images, void photos).
3. The bundle in index.html holds a compiled copy of the dc page as a JSON
   string. Only the part after </helmet> is replaced; the bundle's own head
   (inlined fonts, runtime) is kept.
Run: python3 design/build.py   (Python 3.11+ for tomllib)
"""
import html, json, re, sys, pathlib, tomllib, urllib.parse

here = pathlib.Path(__file__).parent
root = here.parent

# status -> lookup group. PAUSED and after go to the void sheet.
STATUS = {'ACTIVE': 'active', 'LAUNCHED': 'released', 'DONE': 'released',
          'PAUSED': 'void', 'ABANDONED': 'void', 'FAILED': 'void', 'SUPERSEDED': 'void', 'HANDED OVER': 'void'}
REQUIRED = ('title', 'drawing_no', 'period', 'status', 'summary')
# allowed keys: None = a value, {} = a table with free keys, {...} = a table, [{...}] = [[array of tables]]
KEYS = {k: None for k in REQUIRED + ('tags', 'link', 'partners_wanted', 'draft')} | {
    'featured': dict.fromkeys(('nav', 'field', 'drawing', 'photo', 'keep_drawing_colours', 'overview')),
    'specs': {'technologies': None, 'highlights_label': None, 'highlights': None, 'details': {}, 'table': {}},
    'learnings': dict.fromkeys(('intro', 'points', 'outro')),
    'notes': {'title': None, 'text': None, 'cards': [dict.fromkeys(('name', 'repo', 'workspace', 'text'))]},
    'media': [dict.fromkeys(('caption', 'src', 'alt'))],
    'reference': dict.fromkeys(('text', 'button')),
    'void': dict.fromkeys(('why', 'cause', 'carried_into', 'feeds', 'photo'))}
FEATURED = r'AC-\d\d-[A-Z0-9]+'
SHOWN = {'STARTED', 'DATE', 'PERIOD', 'STATUS', 'FIELD', 'TITLE'}  # already on the drawing sheet


def key_errors(d, known, path=''):
    out = []
    for k, v in d.items():
        sub, at = known.get(k, False), path + k
        if sub is False:
            out.append(f'unknown key "{at}"')
        elif isinstance(sub, list):
            if not (isinstance(v, list) and all(isinstance(x, dict) for x in v)):
                out.append(f'"{at}" must be [[{at}]] blocks')
            else:
                for i, x in enumerate(v, 1):
                    out += key_errors(x, sub[0], f'{at}[{i}].')
        elif sub is not None:
            if not isinstance(v, dict):
                out.append(f'"{at}" must be a [{at}] table')
            elif sub:
                out += key_errors(v, sub, at + '.')
    return out


def pick(src, names):  # copy present keys, renamed old -> new
    return {new: src[old] for old, new in names.items() if old in src}


def paras(text):  # blank line = new paragraph, other line breaks = one space
    return [re.sub(r'[ \t]*\n[ \t]*', ' ', p).strip() for p in re.split(r'\n[ \t]*\n', text) if p.strip()]


IMAGE, VIDEO = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg', '.avif'}, {'.mp4', '.webm'}
YOUTUBE = re.compile(r'https://(?:www\.|m\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([\w-]{11})')
web = lambda p: p.startswith(('https://', 'http://'))


def media_item(m, base, n, bad):
    """One [[media]] block -> one DOCUMENTATION item; n counts FIG. and DOC. numbers."""
    src, url = m['src'], urllib.parse.urlsplit(m['src'])
    ext = pathlib.PurePosixPath(url.path).suffix.lower()
    yt = YOUTUBE.match(src)
    kind = 'youtube' if yt else 'image' if ext in IMAGE else 'video' if ext in VIDEO else 'doc'
    label = 'DOC.' if kind == 'doc' else 'FIG.'
    n[label] += 1
    it = {'cap': f'{label} {n[label]} — {m["caption"]}', 'kind': kind, 'name': m['caption'],
          'src': f'https://www.youtube-nocookie.com/embed/{yt[1]}' if yt else src, 'alt': m.get('alt', m['caption'])}
    if kind == 'image' and 'alt' not in m:
        bad.append(f'media "{src}" is an image and needs alt (what it shows)')
    if kind == 'doc':
        q = base / src
        size = q.stat().st_size if not web(src) and q.is_file() else 0
        it['type'] = ext[1:].upper() if ext else 'LINK'
        it['meta'] = url.netloc if web(src) else f'{size / 1e6:.1f} MB' if size >= 1e6 else f'{-(-size // 1000)} KB'
    return it


def images(e):  # local images only: they become ext-resource-dependency metas
    return [x for x in (e.get('img'), e.get('photo'), *(g['src'] for g in e.get('gallery', []) if g['kind'] == 'image')) if x and not web(x)]


def to_entry(f, stem, base, bad):
    """One v2 file -> one ENTRIES object (old keys); problems go to bad."""
    status, dwg, fe, vo = f['status'], f['drawing_no'], f.get('featured'), f.get('void')
    group = STATUS.get(status)
    if group is None:
        bad.append(f'status "{status}" is not one of {", ".join(STATUS)}')
    tags = f.get('tags', [])
    if not isinstance(tags, list):
        bad.append('tags must be a list, like tags = ["hci"]')
        tags = []
    fmt, pat, why = (('AC-NN-XXX', FEATURED, 'it has [featured]') if fe is not None else
                     ('AC-Vnn', r'AC-V\d\d', f'no [featured] and status {status}') if group == 'void' else
                     ('AC-Lnn', r'AC-L\d\d', f'no [featured] and status {status}'))
    if not re.fullmatch(pat, dwg):
        bad.append(f'drawing_no "{dwg}" must look like {fmt} ({why})')

    e = {'title': f['title'], 'dwg': dwg, 'period': f['period'], 'status': status, 'desc': f['summary'],
         'tags': [str(t).lower() for t in tags]} | pick(f, {'link': 'link', 'partners_wanted': 'partners'})
    if fe is None:
        bad += [f'[{k}] only works with [featured]' for k in ('specs', 'learnings', 'notes', 'media', 'reference') if k in f]
    else:
        e['num'] = dwg[3:5]
        e |= pick(fe, {'nav': 'short', 'field': 'field', 'drawing': 'img', 'photo': 'photo', 'keep_drawing_colours': 'raw'})
        if 'overview' in fe:
            e['overview'] = paras(fe['overview'])
        if (sp := f.get('specs')) is not None:
            if 'table' not in sp:
                bad.append('[specs] needs a [specs.table]')
            details = sp.get('details', {})
            bad += [f'specs.details "{k}" is already shown from period/status/field, remove it' for k in details if k.upper() in SHOWN]
            e['details'] = [{'k': 'PERIOD', 'v': f['period']}] + [{'k': k, 'v': v} for k, v in details.items()]
            e |= pick(sp, {'technologies': 'tech', 'highlights_label': 'thirdLabel', 'highlights': 'third'})
            if 'table' in sp:
                e['table'] = [[k, v] for k, v in sp['table'].items()]
        if (le := f.get('learnings')) is not None:
            if 'notes' in f:
                bad.append('[learnings] and [notes] cannot be used together')
            e |= pick(le, {'intro': 'learnIntro', 'points': 'learnings', 'outro': 'learnOutro'})
        if (no := f.get('notes')) is not None:
            if 'text' not in no and 'cards' not in no:
                bad.append('[notes] needs text or [[notes.cards]], or the sheet is not shown')
            e |= pick(no, {'title': 'notesTitle'})
            if 'text' in no:
                e['prose'] = paras(no['text'])
            if 'cards' in no:
                e['cards'] = [pick(c, {'name': 'name', 'repo': 'repo', 'workspace': 'ws', 'text': 'body'}) for c in no['cards']]
        if 'media' in f:
            n = {'FIG.': 1, 'DOC.': 0}  # FIG. 1 is the drawing
            e['gallery'] = [media_item(m, base, n, bad) for m in f['media']]
        if (rf := f.get('reference')) is not None:
            if 'link' not in f:
                bad.append('[reference] needs a top-level link')
            if 'button' not in rf:
                bad.append('[reference] needs a button label, or the page shows an empty button')
            e |= pick(rf, {'text': 'linkText', 'button': 'linkLabel'})
        elif 'link' in f:
            bad.append('a featured project with a link needs a [reference] (text, button)')
    if vo is not None:
        if group != 'void':
            bad.append(f'[void] is only for PAUSED and later, not {status}')
        if fe is not None and 'photo' in vo:
            bad.append('void.photo cannot be used with [featured] (both are the page\'s img)')  # ponytail: spec gap, the page has one img key
        e |= pick(vo, {'why': 'why', 'cause': 'cause', 'carried_into': 'carried', 'feeds': 'feeds', 'photo': 'img'})
    top = base.resolve()
    local = dict.fromkeys(images(e) + [g['src'] for g in e.get('gallery', []) if not web(g['src'])])
    bad += [f'file "{p}" is not in the repo' for p in local
            if not ((q := (base / p).resolve()).is_file() and q.is_relative_to(top))]
    return e | {'id': stem, 'group': group}


def load_entries(folder):
    folder = pathlib.Path(folder)
    entries, errors = [], []
    for path in sorted(folder.glob('*.toml')):
        if path.name.startswith('_'):
            continue
        try:
            f = tomllib.loads(path.read_text(encoding='utf-8'))
        except tomllib.TOMLDecodeError as x:
            errors.append(f'{path.name}: {x}')
            continue
        if f.get('draft'):
            continue
        bad = [f'missing "{k}"' for k in REQUIRED if k not in f] + key_errors(f, KEYS)
        if not bad:
            try:
                entries.append(to_entry(f, path.stem, folder.parent, bad))
            except KeyError as x:
                bad.append(f'missing {x} in a [[...]] block')
            except (TypeError, AttributeError) as x:
                bad.append(f'a value has the wrong type ({x})')
        errors += [f'{path.name}: {m}' for m in bad]
    for key, label in (('dwg', 'drawing_no'), ('num', 'column number')):
        seen = {}
        for e in entries:
            if e.get(key):
                if e[key] in seen:
                    errors.append(f'{e["id"]}.toml and {seen[e[key]]}.toml share {label} "{e[key]}"')
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
    # ponytail: every ext-resource-dependency meta is a project image (the portrait is a plain src), so all are regenerated
    metas = ''.join(f'<meta name="ext-resource-dependency" content="{html.escape(p)}">'
                    for p in dict.fromkeys(p for e in entries for p in images(e)))
    META = re.compile(r'(<meta name="ext-resource-dependency" content="[^"]*">)+')
    src = META.sub(lambda m: metas, src, count=1) if META.search(src) else src.replace('</helmet>', metas + '\n</helmet>', 1)
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
