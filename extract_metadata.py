import csv, os, re, xml.etree.ElementTree as ET

NS = 'http://www.tei-c.org/ns/1.0'
T = lambda tag: f'{{{NS}}}{tag}'

GENRE_RE = re.compile(
    r'\b(comedy|tragedy|farce|tragicomedy|tragi-comedy|opera|drama|musical|'
    r'burletta|melodrama|interlude|masque|afterpiece|prelude|pastoral)\b',
    re.IGNORECASE)

def get_text(el, path):
    found = el.find(path)
    return (found.text or '').strip() if found is not None else ''

def extract(path):
    slug = os.path.basename(path)[:-4]
    tree = ET.parse(path)
    root = tree.getroot()

    title_stmt = root.find(f'.//{T("titleStmt")}')
    title = ''
    subtitle = ''
    if title_stmt is not None:
        for t in title_stmt.findall(T('title')):
            if t.get('type') == 'main':
                title = (t.text or '').strip()
            elif t.get('type') == 'sub':
                subtitle = (t.text or '').strip()

    # authors (may be multiple)
    authors = []
    if title_stmt is not None:
        for author in title_stmt.findall(T('author')):
            pn = author.find(f'.//{T("persName")}')
            if pn is not None:
                fore = get_text(pn, T('forename'))
                sur  = get_text(pn, T('surname'))
                name = ', '.join(filter(None, [sur, fore]))
            else:
                name = (author.text or '').strip()
            if name:
                authors.append(name)
    author_str = ' / '.join(authors)

    # genre from subtitle
    m = GENRE_RE.search(subtitle)
    genre = m.group(1).lower() if m else 'nan'

    # year from standOff event
    year = 'nan'
    for event in root.findall(f'.//{T("event")}'):
        if event.get('type') == 'print' and event.get('when'):
            year = event.get('when')
            break

    return [slug, title or 'nan', author_str or 'nan', genre, year]

rows = []
tei_dir = os.path.join(os.path.dirname(__file__), 'tei')
for fname in sorted(os.listdir(tei_dir)):
    if fname.endswith('.xml'):
        rows.append(extract(os.path.join(tei_dir, fname)))

out = os.path.join(os.path.dirname(__file__), 'corpus_metadata.csv')
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f, delimiter='|')
    w.writerow(['slug', 'title', 'author', 'genre', 'year'])
    w.writerows(rows)

print(f'Written {len(rows)} rows to {out}')
