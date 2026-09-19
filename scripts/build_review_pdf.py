"""Build a clearly labelled review PDF from a manuscript and its BibTeX records.

Supports the Markdown subset used by the current working papers. This is an
editorial artifact, not a publisher template or a claim of submission readiness.
"""
import argparse
from datetime import date
import hashlib
import html
import importlib.metadata
import json
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from pypdf import PdfReader


def normalize(s):
    return s.translate(str.maketrans({'\u2013': '-', '\u2014': ' - ', '\u2011': '-',
                                     '\u2212': '-', '\u2192': ' -> ', '\u2019': "'"}))


def inline(s):
    s = html.escape(normalize(s))
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<link href="\2" color="#164b70">\1</link>', s)
    s = re.sub(r'`([^`]+)`', r'<font name="Courier" size="8.2">\1</font>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<i>\1</i>', s)
    return s


def bib_records(text):
    """Read brace-delimited fields used in these local bibliography files."""
    records = []
    for block in re.split(r'(?m)^@', text)[1:]:
        header = re.match(r'\w+\{([^,]+),', block)
        assert header, block[:80]
        fields = {}
        for match in re.finditer(r'(?m)^\s*(\w+)\s*=\s*\{', block):
            start, depth, end = match.end(), 1, match.end()
            while depth:
                assert end < len(block)
                depth += (block[end] == '{') - (block[end] == '}')
                end += 1
            fields[match.group(1)] = block[start:end-1].replace('{', '').replace('}', '')
        assert 'title' in fields and 'url' in fields
        records.append((header.group(1), fields))
    return records


def build(paper, output, review_date):
    source, bibliography = paper/'manuscript.md', paper/'references.bib'
    text = source.read_text(encoding='utf-8')
    assert 'incomplete' in text[:800].lower() or 'not submission-ready' in text[:800].lower()
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=51, leftMargin=51,
        topMargin=49, bottomMargin=49, title=text.splitlines()[0].removeprefix('# '),
        author='', subject='Incomplete research manuscript for review')
    body = ParagraphStyle('Body', fontName='Times-Roman', fontSize=10.5, leading=13.5,
                          spaceAfter=6, alignment=TA_JUSTIFY)
    literal_body = ParagraphStyle('LiteralBody', parent=body, alignment=0)
    h1 = ParagraphStyle('Title', parent=body, fontName='Times-Bold', fontSize=19,
                        leading=23, spaceAfter=14, alignment=0, keepWithNext=True)
    h2 = ParagraphStyle('Section', parent=body, fontName='Times-Bold', fontSize=13,
                        leading=16, spaceBefore=12, spaceAfter=7, alignment=0, keepWithNext=True)
    h3 = ParagraphStyle('Subsection', parent=h2, fontSize=11.5, leading=14, spaceBefore=9)
    cell = ParagraphStyle('Cell', parent=body, fontName='Helvetica', fontSize=8,
                          leading=10, spaceAfter=0, alignment=0)
    refs = ParagraphStyle('Reference', parent=body, fontSize=9, leading=12, alignment=0)
    caption = ParagraphStyle('Caption', parent=body, fontSize=9, leading=12,
                             alignment=0, keepWithNext=True, spaceBefore=5)
    story = []
    lines = text.splitlines()
    i, tables, paragraphs = 0, 0, []
    figures, in_references = {}, False
    explicit_references = '## References' in lines
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith('#'):
            level = len(line)-len(line.lstrip('#'))
            assert level in (1, 2, 3)
            story.append(Paragraph(inline(line[level:].strip()), {1:h1, 2:h2, 3:h3}[level]))
            in_references = line == '## References'
            i += 1
            continue
        if line.startswith('!['):
            match = re.fullmatch(r'!\[([^\]]+)\]\(([^)]+)\)', line)
            assert match, 'Expected a standalone local figure'
            figure_path = (paper / match.group(2)).resolve()
            assert figure_path.is_relative_to(paper.resolve()) and figure_path.is_file()
            figure = Image(str(figure_path))
            scale = min(doc.width / figure.imageWidth, doc.height * .42 / figure.imageHeight)
            figure.drawWidth, figure.drawHeight = figure.imageWidth * scale, figure.imageHeight * scale
            figures[match.group(2)] = hashlib.sha256(figure_path.read_bytes()).hexdigest()
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            caption_lines = []
            while i < len(lines) and lines[i].strip():
                caption_lines.append(lines[i].strip())
                i += 1
            figure_caption = ' '.join(caption_lines)
            assert re.match(r'\*Figure \d+\.', figure_caption), 'Figure needs its own caption'
            figure_style = ParagraphStyle('FigureCaption', parent=caption, keepWithNext=False)
            story.extend([KeepTogether([figure, Spacer(1, 4),
                          Paragraph(inline(figure_caption), figure_style)]), Spacer(1, 8)])
            continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                values = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', c) for c in values):
                    rows.append(values)
                i += 1
            n = len(rows[0])
            assert all(len(row) == n for row in rows)
            widths = [doc.width*0.30]+[doc.width*0.70/(n-1)]*(n-1)
            cells = [[Paragraph(('<b>'+inline(v)+'</b>') if j == 0 else inline(v), cell)
                      for v in row] for j, row in enumerate(rows)]
            table = Table(cells, colWidths=widths, repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#eaf0f4')),
                ('LINEABOVE', (0,0), (-1,0), .7, colors.HexColor('#455969')),
                ('LINEBELOW', (0,0), (-1,0), .45, colors.HexColor('#81919d')),
                ('LINEBELOW', (0,-1), (-1,-1), .7, colors.HexColor('#455969')),
                ('LEFTPADDING', (0,0), (-1,-1), 5), ('RIGHTPADDING', (0,0), (-1,-1), 5),
                ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6)]))
            story.extend([table, Spacer(1,10)])
            tables += 1
            continue
        chunks = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#', '|')):
            assert not lines[i].startswith('```'), 'Code fences need an explicit layout'
            chunks.append(lines[i].strip())
            i += 1
        paragraph = ' '.join(chunks)
        paragraphs.append(paragraph)
        style = (refs if in_references else caption if re.match(r'\*\*Table \d+\.', paragraph) else
                 literal_body if re.search(r'\b[0-9a-f]{40,64}\b', paragraph) else body)
        story.append(Paragraph(inline(paragraph), style))
    records = bib_records(bibliography.read_text(encoding='utf-8'))
    if explicit_references:
        assert text.split('## References\n')[1].count('[Source](') == len(records)
    else:
        story.extend([Spacer(1, 12), Paragraph('References', h2)])
    for number, (key, fields) in enumerate([] if explicit_references else records, 1):
        author = fields.get('author', '').replace(' and ', '; ')
        lead = f'[{number}] '+'. '.join(v for v in [author, fields.get('year'), fields['title']] if v)+'.'
        venue = fields.get('journal', '')
        if fields.get('volume'):
            venue += ' '+fields['volume']
        if fields.get('number'):
            venue += ('('+fields['number']+')' if fields.get('journal')
                      else ' '+fields['number'])
        tail = ' '.join(v for v in [venue] + [fields.get(k, '') for k in
                       ('booktitle', 'institution', 'howpublished', 'publisher', 'note')] if v)
        if fields.get('pages'):
            tail += ' pp. '+fields['pages'].replace('--', '-')+'.'
        if fields.get('doi'):
            tail += ' DOI: '+fields['doi']+'.'
        if fields.get('eprint'):
            tail += ' arXiv:'+fields['eprint']+' (preprint).'
        story.append(Paragraph(inline(lead+' '+tail)+
            f' <link href="{html.escape(fields["url"])}" color="#164b70">Source</link>.', refs))
    def page(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#bdc7ce'))
        canvas.line(51, 37, A4[0]-51, 37)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#52616c'))
        canvas.drawString(51, 25, 'INCOMPLETE REVIEW DRAFT | '+review_date.strftime('%d %B %Y'))
        canvas.drawRightString(A4[0]-51, 25, str(document.page))
        canvas.restoreState()
    doc.build(story, onFirstPage=page, onLaterPages=page)
    pdf = PdfReader(output)
    extracted = '\n'.join(p.extract_text() or '' for p in pdf.pages)
    for token in ('2,000', '10,000', 'References', '5.7') if paper.name == 'paper3' else ('References',):
        assert token in extracted, token
    assert '\u25a0' not in extracted
    manifest = {'source': source.as_posix(), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'bibliography_sha256': hashlib.sha256(bibliography.read_bytes()).hexdigest(),
        'builder_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'output': output.as_posix(), 'pdf_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'pages': len(pdf.pages), 'tables': tables, 'reference_records': len(records), 'review_date': review_date.isoformat(),
        'figure_sha256': figures, 'explicit_references': explicit_references,
        'packages': {n: importlib.metadata.version(n) for n in ('reportlab', 'pypdf')},
        'publication_ready': False, 'visual_review': 'pending'}
    output.with_suffix('.build.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(manifest))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--paper', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--date', type=date.fromisoformat, required=True)
    args = parser.parse_args()
    build(args.paper, args.output, args.date)
