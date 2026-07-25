from html import escape
from html.parser import HTMLParser


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
            if name in allowed_attrs:
                safe_attrs.append(f' {name}="{escape(value or "", quote=True)}"')
        self.parts.append(f'<{tag}{"".join(safe_attrs)}>')

    def handle_endtag(self, tag):
        if tag in SAFE_HTML_TAGS and tag != 'br':
            self.parts.append(f'</{tag}>')

    def handle_startendtag(self, tag, attrs):
        if tag == 'br':
            self.parts.append('<br>')
            return
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        self.parts.append(escape(data).replace('\n', '<br>'))

    def get_html(self):
        return ''.join(self.parts)


def sanitize_html(value):
    text = str(value or '').strip()
    if not text:
        return ''
    if '<' not in text and '>' not in text:
        return escape(text).replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br>')
    parser = SafeHtmlRenderer()
    parser.feed(text)
    parser.close()
    return parser.get_html()
