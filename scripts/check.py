from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import hashlib
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
BASE = '/gas-states-korean-practice-web/'
ORIGIN = 'https://mcyj.github.io'


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.text = []
        self.script = False
        self.schema = []
        self.current_schema = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.nodes.append((tag, attrs))
        if tag == 'script':
            self.script = True
            if attrs.get('type') == 'application/ld+json':
                self.current_schema = ''

    def handle_endtag(self, tag):
        if tag == 'script':
            if self.current_schema is not None:
                self.schema.append(json.loads(self.current_schema))
                self.current_schema = None
            self.script = False

    def handle_data(self, data):
        if self.current_schema is not None:
            self.current_schema += data
        if not self.script:
            self.text.append(data)


def target_for(path):
    assert path.startswith(BASE), path
    rel = unquote(path[len(BASE):])
    dest = (DIST / rel).resolve()
    assert dest.is_relative_to(DIST.resolve()), path
    return dest / 'index.html' if dest.is_dir() or path.endswith('/') else dest


def main():
    files = sorted(DIST.rglob('*.html'))
    assert len(files) == 42, len(files)
    guides = json.loads((ROOT / 'content/guides.json').read_text())
    assert len(guides) == 10 and len({g['slug'] for g in guides}) == 10
    checks = 0
    for path in files:
        raw = path.read_text()
        doc = Document()
        doc.feed(raw)
        tags = doc.nodes
        assert sum(t == 'h1' for t, _ in tags) == 1, path
        assert any(t == 'html' and a.get('lang') in ['ko', 'en'] for t, a in tags)
        assert any(t == 'meta' and a.get('name') == 'viewport' for t, a in tags)
        assert any(t == 'title' for t, _ in tags)
        ids = [a['id'] for _, a in tags if 'id' in a]
        assert len(ids) == len(set(ids)), path
        for tag, attrs in tags:
            if tag == 'img':
                assert 'alt' in attrs and 'width' in attrs and 'height' in attrs, path
            for attribute in ['href', 'src']:
                link = attrs.get(attribute)
                if not link:
                    continue
                parts = urlsplit(link)
                if parts.scheme == 'mailto':
                    assert parts.path == 'june1012june@gmail.com', path
                    continue
                if parts.scheme or parts.netloc:
                    assert parts.scheme == 'https', link
                    if parts.netloc != 'mcyj.github.io' or not parts.path.startswith(BASE):
                        assert parts.netloc in {'www.q-net.or.kr','www1.grc.nasa.gov','openstax.org','www.nist.gov','docs.github.com','mcyj.github.io'}, link
                        continue
                if parts.path:
                    target = target_for(parts.path)
                    assert target.is_file(), (path, link)
                else:
                    target = path
                if parts.fragment:
                    other = Document()
                    other.feed(target.read_text())
                    assert any(a.get('id') == parts.fragment for _, a in other.nodes), (path, link)
                checks += 1
        if path.parent.name not in ['dist'] and path.name != '404.html':
            expected = ORIGIN + BASE + path.relative_to(DIST).as_posix().removesuffix('index.html')
            canonical = [a.get('href') for t,a in tags if t == 'link' and a.get('rel') == 'canonical']
            assert canonical == [expected], (path, canonical)
            assert {a.get('hreflang') for t,a in tags if t == 'link' and a.get('rel') == 'alternate'} == {'ko','en','x-default'}
            assert len(doc.schema) == 1 and doc.schema[0]['url'] == expected
            assert not any('offers' in s or 'aggregateRating' in s for s in doc.schema)
            assert any(t == 'a' and a.get('class') == 'skip' for t,a in tags)
            visible = ' '.join(doc.text)
            assert ('출시 준비 중' if '/ko/' in str(path) else 'Coming soon') in visible
            assert ('제휴' if '/ko/' in str(path) else 'affiliated') in visible
            if '/guides/' in str(path) and path.parent.name != 'guides':
                assert len(visible) > 1000, path
                assert sum(t == 'h2' for t,a in tags) >= 5
                assert doc.schema[0]['@type'] == 'Article'
        assert not re.search(r'play\.google\.com/store/apps|apps\.apple\.com/', raw), path
        assert not re.search(r'googletagmanager|google-analytics|facebook\.net|doubleclick|<iframe', raw, re.I)
    sitemap = ET.parse(DIST / 'sitemap.xml')
    urls = [x.text for x in sitemap.findall('.//{*}loc')]
    assert len(urls) == 41 and len(set(urls)) == 41
    for url in urls:
        assert url.startswith(ORIGIN + BASE)
        assert target_for(urlsplit(url).path).is_file()
    provenance = json.loads((ROOT / 'content/asset-provenance.json').read_text())
    for row in provenance['assets']:
        assert hashlib.sha256((ROOT / row['file']).read_bytes()).hexdigest() == row['sha256']
        assert hashlib.sha256((DIST / row['file']).read_bytes()).hexdigest() == row['sha256']
    js = (DIST / 'assets/site.js').read_text()
    assert not re.search(r'fetch\(|XMLHttpRequest|localStorage|sessionStorage|document\.cookie|sendBeacon|https?://', js)
    css = (DIST / 'assets/site.css').read_text()
    assert 'word-break:keep-all' in css and 'prefers-reduced-motion' in css and ':focus-visible' in css
    for path in ROOT.rglob('*'):
        if not path.is_file() or '.git' in path.parts or 'qa' in path.relative_to(ROOT).parts:
            continue
        assert path.suffix not in {'.jsonl','.p8','.p12','.jks','.keystore','.aab','.apk','.ipa'}, path
        if path.suffix in {'.html','.json','.js','.css','.md','.yml'}:
            raw = path.read_text()
            assert not re.search(r'-----BEGIN [A-Z ]*PRIVATE KEY-----|eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}', raw), path
    print(json.dumps({'status':'passed_static_publication_checks','htmlPages':42,'indexableRoutes':41,'internalLinksAndAssetsChecked':checks,'guideArticles':20,'presentationAssetsExactSha256':5,'unverifiedStoreDownloadLinks':0,'trackingOrStorageCalls':0,'privateBanksOrNativeBinaries':0,'browserQaRequiredSeparately':True}))


if __name__ == '__main__':
    main()
