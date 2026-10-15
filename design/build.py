"""Rebuild ../index.html from portfolio.dc.html (the editable design source).

The bundle in index.html holds a compiled copy of the dc page as a JSON string.
Only the part after </helmet> is replaced; the bundle's own head (inlined fonts,
runtime) is kept. Run: python3 design/build.py
"""
import json, re, pathlib

here = pathlib.Path(__file__).parent
src = (here / 'portfolio.dc.html').read_text()
idx = here.parent / 'index.html'
bundle = idx.read_text()

TPL = re.compile(r'(<script type="__bundler/template"[^>]*>)(.*?)(</script>)', re.S)
tpl = json.loads(TPL.search(bundle).group(2))

body = src.split('</helmet>', 1)[1]
markup, script = body.split('<script type="text/x-dc"', 1)
# the bundler's compile step: camelCase attrs -> sc-camel-kebab, no </img>
markup = re.sub(r' ([a-z]+[A-Z][A-Za-z]*)=',
                lambda m: ' sc-camel-' + re.sub(r'[A-Z]', lambda x: '-' + x.group().lower(), m.group(1)) + '=',
                markup).replace('</img>', '')
tpl = tpl.split('</helmet>', 1)[0] + '</helmet>' + markup + '<script type="text/x-dc"' + script.replace(' data-dc-script data-props', ' data-dc-script="" data-props', 1)

bundle = TPL.sub(lambda m: m.group(1) + json.dumps(tpl).replace('</', '<\\/') + m.group(3), bundle)
idx.write_text(bundle)
print('index.html rebuilt,', len(bundle), 'bytes')
