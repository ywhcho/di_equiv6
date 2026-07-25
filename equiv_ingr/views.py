from urllib.parse import urlencode
from html import escape
from html.parser import HTMLParser

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from decimal import Decimal, InvalidOperation
from django.db.models import IntegerField, Sum, Value
from django.db.models.functions import Cast, Coalesce, Replace

from .models import MedInteractionMfname, MedicinesDruginfo, MedicinesMedicine

PAGE_SIZE = 10

_SAFE_HTML_TAGS = {
    'a', 'b', 'br', 'div', 'em', 'i', 'li', 'ol', 'p', 'span',
    'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'th', 'thead',
    'tr', 'u', 'ul',
}
_SAFE_HTML_ATTRS = {
    'a': {'href', 'target', 'rel'},
    'td': {'colspan', 'rowspan'},
    'th': {'colspan', 'rowspan'},
}


class _SafeHtmlRenderer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag not in _SAFE_HTML_TAGS:
            return
        safe_attrs = []
        allowed_attrs = _SAFE_HTML_ATTRS.get(tag, set())
        for name, value in attrs:
            if name in allowed_attrs:
                safe_attrs.append(f' {name}="{escape(value or "", quote=True)}"')
        self.parts.append(f'<{tag}{"".join(safe_attrs)}>')

    def handle_endtag(self, tag):
        if tag in _SAFE_HTML_TAGS and tag != 'br':
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


def _format_amount(value):
    text = str(value or '').strip()
    if not text:
        return ''
    normalized = text.replace(',', '')
    try:
        return f"{int(Decimal(normalized)):,}"
    except (InvalidOperation, ValueError):
        return text


def _ypri24_display(value):
    formatted = _format_amount(value)
    if not formatted or formatted == '0':
        return '-'
    return formatted


def _druginfo_ypri24_display(ypri24, canc_date):
    base_display = _ypri24_display(ypri24)
    canc_date_text = str(canc_date or '').strip()
    if canc_date_text:
        return f'{base_display}(-사용종료일: {canc_date_text})'
    return f'{base_display}(-)'


def _sanitize_html(value):
    text = str(value or '').strip()
    if not text:
        return ''
    if '<' not in text and '>' not in text:
        return escape(text).replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br>')
    parser = _SafeHtmlRenderer()
    parser.feed(text)
    parser.close()
    return parser.get_html()


def _get_table1_queryset(query_type, query_val):
    filter_map = {
        'ingr_t': 'ingr_t__icontains',
        'kingr_t': 'kingr_t__icontains',
        'cfno': 'cfno__icontains',
        'wfco': 'wfco__icontains',
        'ATC': 'ATC__istartswith',
    }
    lookup = filter_map.get(query_type)
    if not lookup:
        return MedInteractionMfname.objects.none()

    return MedInteractionMfname.objects.filter(**{lookup: query_val}).order_by('wfco', 'id')


def _get_table2_base_queryset(wfco_full):
    return MedicinesMedicine.objects.filter(wfco=wfco_full).annotate(
        ypri24_num=Cast(Replace('ypri24', Value(','), Value('')), IntegerField())
    )


def _get_table2_queryset(wfco_full, sort2):
    sort_map = {
        'htname': ('htname', 'id'),
        'company': ('company', 'id'),
        'ypri24': ('-ypri24_num', 'id'),
    }
    order_by = sort_map.get(sort2, sort_map['ypri24'])
    return _get_table2_base_queryset(wfco_full).order_by(*order_by)


def _get_table2_sort_links(query_type, query_val, wfco_full, page1):
    base_params = {
        'type': query_type,
        'val': query_val,
        'wfco': wfco_full,
        'page1': page1,
        'page2': 1,
    }
    return {
        key: '?' + urlencode({**base_params, 'sort2': key})
        for key in ('htname', 'company', 'ypri24')
    }


def search_view(request):
    query_type = request.GET.get('type', 'ingr_t')
    query_val = request.GET.get('val', '').strip()
    wfco_full = request.GET.get('wfco', '').strip()
    sort2 = request.GET.get('sort2', 'ypri24').strip()

    table1_page = None
    if query_val:
        qs1 = _get_table1_queryset(query_type, query_val)
        p1 = Paginator(qs1, PAGE_SIZE)
        table1_page = p1.get_page(request.GET.get('page1', 1))

    table2_page = None
    table2_ypri24_total = None
    table2_ingr_t = ''
    if wfco_full:
        qs2 = _get_table2_queryset(wfco_full, sort2)
        agg = qs2.aggregate(total=Coalesce(Sum('ypri24_num'), Value(0), output_field=IntegerField()))
        table2_ypri24_total = _format_amount(str(agg['total'])) if agg['total'] else ''
        first_row = qs2.first()
        if first_row:
            table2_ingr_t = first_row.ingr_t
        p2 = Paginator(qs2, PAGE_SIZE)
        table2_page = p2.get_page(request.GET.get('page2', 1))
        for row in table2_page.object_list:
            row.ypri24_display = _ypri24_display(row.ypri24)

    auto_focus = ''
    if wfco_full:
        auto_focus = 'table2-section'

    return render(request, 'equiv_ingr/search.html', {
        'query_type': query_type,
        'query_val': query_val,
        'table1_page': table1_page,
        'table2_page': table2_page,
        'table2_ypri24_total': table2_ypri24_total,
        'table2_ingr_t': table2_ingr_t,
        'table2_sort_links': _get_table2_sort_links(query_type, query_val, wfco_full, request.GET.get('page1', 1)),
        'wfco_full': wfco_full,
        'sort2': sort2,
        'auto_focus': auto_focus,
    })


def druginfo_detail(request):
    """
    di 버튼 클릭 시 medicines_druginfo 테이블에서 의약정보를 조회하여 JSON 반환.
    ?htname=... 파라미터로 검색
    """
    htname = request.GET.get('htname', '').strip()
    if not htname:
        return JsonResponse({'results': []})

    rows = MedicinesDruginfo.objects.filter(htname=htname)
    results = []
    for row in rows:
        results.append({
            'htname': row.htname,
            'ingr_t': row.ingr_t,
            'sthunite_t': row.sthunite_t,
            'ypri24': _druginfo_ypri24_display(row.ypri24, row.canc_date),
            'company': row.company,
            'kfregcd': row.kfregcd,
            'ee': row.ee,
            'ud_html': _sanitize_html(row.ud),
            'nb_html': _sanitize_html(row.nb),
        })
    return JsonResponse({'results': results})
