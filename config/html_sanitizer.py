from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse


SAFE_HTML_TAGS = {
    'a', 'b', 'br', 'div', 'em', 'i', 'li', 'ol', 'p', 'span',
    'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'th', 'thead',
    'tr', 'u', 'ul',
}
SAFE_HTML_ATTRS = {
    'a': {'href', 'target', 'rel'},
    'td': {'colspan', 'rowspan'},
    'th': {'colspan', 'rowspan'},
}


def _normalize_newlines(value):
    return value.replace('\r\n', '\n').replace('\r', '\n')


def _is_safe_href(value):
    text = str(value or '').strip()
    if not text:
        return False
    if text.startswith(('/', '#')):
        return True
    scheme = urlparse(text).scheme.lower()
    return scheme in {'http', 'https', 'mailto'}


def _is_safe_rel(value):
    tokens = [token for token in str(value or '').split() if token]
    return bool(tokens) and all(token in {'noopener', 'noreferrer'} for token in tokens)


class SafeHtmlRenderer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag not in SAFE_HTML_TAGS:
            return
        safe_attrs = []
        allowed_attrs = SAFE_HTML_ATTRS.get(tag, set())
        for name, value in attrs:
            if name not in allowed_attrs:
                continue
            if tag == 'a' and name == 'href' and not _is_safe_href(value):
                continue
            if tag == 'a' and name == 'target' and value not in {'_blank', '_self'}:
                continue
            if tag == 'a' and name == 'rel' and not _is_safe_rel(value):
                continue
            safe_attrs.append(f' {name}="{escape(value or "", quote=True)}"')
        self.parts.append(f'<{tag}{"".join(safe_attrs)}>')

    def handle_endtag(self, tag):
        if tag in SAFE_HTML_TAGS and tag != 'br':
            self.parts.append(f'</{tag}>')

    def handle_startendtag(self, tag, attrs):
        if tag == 'br':
            self.parts.append('<br>')
            return
        if tag not in SAFE_HTML_TAGS:
            return
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        normalized = _normalize_newlines(data)
        self.parts.append(escape(normalized).replace('\n', '<br>'))

    def get_html(self):
        return ''.join(self.parts)


def sanitize_html(value):
    text = str(value or '').strip()
    if not text:
        return ''
    if '<' not in text and '>' not in text:
        return escape(_normalize_newlines(text)).replace('\n', '<br>')
    parser = SafeHtmlRenderer()
    parser.feed(text)
    parser.close()
    return parser.get_html()
