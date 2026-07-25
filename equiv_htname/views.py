from decimal import Decimal, InvalidOperation
from html import escape
from html.parser import HTMLParser

from django.core.paginator import Paginator
from django.db.models import IntegerField, Sum, Value
from django.db.models.functions import Cast, Coalesce, Replace
from django.http import JsonResponse
from django.shortcuts import render

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


def _annotate_ypri24(qs):
    """ypri24(CharField) → ypri24_num(IntegerField) 어노테이션 추가."""
    return qs.annotate(
        ypri24_num=Cast(Replace('ypri24', Value(','), Value('')), IntegerField())
    )


def _ypri24_total(qs):
    agg = qs.aggregate(
        total=Coalesce(Sum('ypri24_num'), Value(0), output_field=IntegerField())
    )
    return _format_amount(str(agg['total'])) if agg['total'] else ''


def _ypri24_display(value):
    """ypri24 표시용: 빈 값이나 0이면 '-' 반환."""
    formatted = _format_amount(value)
    if not formatted or formatted == '0':
        return '-'
    return formatted


def _set_ypri24_display(page):
    for row in page.object_list:
        row.ypri24_display = _ypri24_display(row.ypri24)


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


# 검색 타입 정의: (필드 조회식, 표시명)
# ATC만 startswith, 나머지는 icontains
SEARCH_TYPES = {
    'htname':  ('htname__icontains',   '약품명'),
    'ee':      ('ee__icontains',       '효능'),
    'ingr_t':  ('ingr_t__icontains',   '성분명'),
    'company': ('company__icontains',  '회사'),
    'wfco':    ('wfco__icontains',     '활성성분코드'),
    'cfno':    ('cfno__icontains',     '효능분류'),
    'atc':     ('atc__istartswith',    'ATC분류'),
}


def search_view(request):
    """
    medicines_medicine 에서 의약정보 검색.
    - Table 1: stype/sval 로 medicines_medicine 검색 (7가지 검색 종류)
    - Table 2: Table 1 행 선택 → wfco 앞 6자리로 med_interaction_mfname 검색
    - Table 3: Table 2 행 선택 → wfco 전체(10자리)로 medicines_medicine 검색
               각 행에 [DI] 버튼 → 의약정보 팝업
    """
    stype = request.GET.get('stype', 'htname').strip()
    if stype not in SEARCH_TYPES:
        stype = 'htname'
    sval = request.GET.get('sval', '').strip()

    # 하위호환: 기존 htname 파라미터 지원
    if not sval:
        legacy = request.GET.get('htname', '').strip()
        if legacy:
            sval = legacy
            stype = 'htname'

    wfco6 = request.GET.get('wfco6', '').strip()
    wfco_t1 = request.GET.get('wfco_t1', '').strip()
    wfco_full = request.GET.get('wfco', '').strip()
    sort1_raw = request.GET.get('sort1', '')
    sort1 = sort1_raw if sort1_raw in ('htname', 'company', 'ypri24') else 'ypri24'
    sort3_raw = request.GET.get('sort3', '')
    sort3 = sort3_raw if sort3_raw in ('htname', 'company', 'ypri24') else 'ypri24'

    # ── Table 1: 검색 ────────────────────────────────────────────────────────
    table1_page = None
    table1_ypri24_total = ''
    if sval:
        field_lookup, _ = SEARCH_TYPES[stype]
        _sort1_map = {
            'htname': ('htname', 'id'),
            'company': ('company', 'id'),
            'ypri24': ('-ypri24_num', 'id'),
        }
        t1_order = _sort1_map[sort1]
        qs1 = _annotate_ypri24(
            MedicinesMedicine.objects.filter(**{field_lookup: sval})
        ).order_by(*t1_order)
        table1_ypri24_total = _ypri24_total(qs1)
        p1 = Paginator(qs1, PAGE_SIZE)
        table1_page = p1.get_page(request.GET.get('page1', 1))
        _set_ypri24_display(table1_page)

    # ── Table 2: wfco 앞 6자리 비교 ────────────────────────────────────────
    table2_page = None
    table2_ypri24_total = ''
    if wfco6:
        qs2 = _annotate_ypri24(
            MedInteractionMfname.objects.filter(wfco__startswith=wfco6)
        ).order_by('-ypri24_num', 'id')
        table2_ypri24_total = _ypri24_total(qs2)
        p2 = Paginator(qs2, PAGE_SIZE)
        table2_page = p2.get_page(request.GET.get('page2', 1))
        _set_ypri24_display(table2_page)

    # ── Table 3: wfco 전체(10자리) 비교 ─────────────────────────────────────
    table3_page = None
    table3_ypri24_total = ''
    if wfco_full:
        _sort3_map = {
            'htname': ('htname', 'id'),
            'company': ('company', 'id'),
            'ypri24': ('-ypri24_num', 'id'),
        }
        t3_order = _sort3_map[sort3]
        qs3 = _annotate_ypri24(
            MedicinesMedicine.objects.filter(wfco=wfco_full)
        ).order_by(*t3_order)
        table3_ypri24_total = _ypri24_total(qs3)
        p3 = Paginator(qs3, PAGE_SIZE)
        table3_page = p3.get_page(request.GET.get('page3', 1))
        _set_ypri24_display(table3_page)

    # ── Table 3: ee/ingr_t 공통값 (header 표시용) ───────────────────────────
    table3_ee = ''
    table3_ingr_t = ''
    if wfco_full:
        first_row = qs3.first()
        if first_row:
            table3_ee = first_row.ee
            table3_ingr_t = first_row.ingr_t

    return render(request, 'equiv_htname/search.html', {
        'stype': stype,
        'sval': sval,
        'search_types': SEARCH_TYPES,
        'wfco6': wfco6,
        'wfco_t1': wfco_t1,
        'wfco_full': wfco_full,
        'sort1': sort1,
        'sort3': sort3,
        'table1_page': table1_page,
        'table1_ypri24_total': table1_ypri24_total,
        'table2_page': table2_page,
        'table2_ypri24_total': table2_ypri24_total,
        'table3_page': table3_page,
        'table3_ypri24_total': table3_ypri24_total,
        'table3_ee': table3_ee,
        'table3_ingr_t': table3_ingr_t,
    })


def druginfo_detail(request):
    """
    DI 버튼 클릭 시 medicines_druginfo 테이블에서 의약정보를 조회하여 JSON 반환.
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
