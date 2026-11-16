"""
Lumen – schöne Dokumente erstellen: Markdown → Word (.docx), PDF, EPUB (E-Book), HTML, Markdown, Text.
Word braucht python-docx, PDF braucht reportlab (beides installiert setup-linux.sh). EPUB/HTML gehen immer.
"""
import html
import re
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

FORMATS = ("docx", "pdf", "epub", "html", "md", "txt")


def default_dir():
    for name in ("Dokumente", "Documents"):
        p = Path.home() / name
        if p.is_dir():
            return p / "Lumen"
    return Path.home() / "Lumen-Dokumente"


def safe_name(title):
    n = re.sub(r"[^\w\-äöüÄÖÜß ]+", "", title or "").strip().replace(" ", "_")[:60]
    return n or "Dokument"


# ---------------------------------------------------------------- Markdown → Blöcke
def blocks(md):
    """→ [(typ, inhalt)] mit typ in h1,h2,h3,p,ul,ol,quote,code,hr,pagebreak"""
    out, para, lst, code = [], [], None, None

    def flush():
        nonlocal para, lst
        if para:
            out.append(("p", " ".join(para)))
            para = []
        if lst:
            out.append(lst)
            lst = None

    for line in (md or "").replace("\r", "").split("\n"):
        if code is not None:
            if line.strip().startswith("```"):
                out.append(("code", "\n".join(code)))
                code = None
            else:
                code.append(line)
            continue
        s = line.strip()
        if s.startswith("```"):
            flush()
            code = []
        elif not s:
            flush()
        elif s in ("---", "***", "___"):
            flush()
            out.append(("hr", ""))
        elif s.lower() in ("\\pagebreak", "<!-- pagebreak -->", "[seitenumbruch]"):
            flush()
            out.append(("pagebreak", ""))
        elif m := re.match(r"^(#{1,6})\s+(.*)", s):
            flush()
            out.append(("h" + str(min(3, len(m.group(1)))), m.group(2).strip()))
        elif m := re.match(r"^[-*+]\s+(.*)", s):
            if para:
                out.append(("p", " ".join(para)))
                para = []
            if not lst or lst[0] != "ul":
                if lst:
                    out.append(lst)
                lst = ("ul", [])
            lst[1].append(m.group(1))
        elif m := re.match(r"^\d+[.)]\s+(.*)", s):
            if para:
                out.append(("p", " ".join(para)))
                para = []
            if not lst or lst[0] != "ol":
                if lst:
                    out.append(lst)
                lst = ("ol", [])
            lst[1].append(m.group(1))
        elif s.startswith(">"):
            flush()
            out.append(("quote", s.lstrip("> ").strip()))
        else:
            if lst:
                out.append(lst)
                lst = None
            para.append(s)
    if code is not None:
        out.append(("code", "\n".join(code)))
    flush()
    return out


def inline_html(t):
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<i>\1</i>", t)
    t = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"<i>\1</i>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


def inline_runs(t):
    """→ [(text, bold, italic)] für Word."""
    runs = []
    for part in re.split(r"(\*\*.+?\*\*|\*[^*\s][^*]*?\*|`.+?`)", t):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            runs.append((part[2:-2], True, False))
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            runs.append((part[1:-1], False, True))
        elif part.startswith("`") and part.endswith("`"):
            runs.append((part[1:-1], False, False))
        else:
            runs.append((part, False, False))
    return runs


def plain(t):
    return re.sub(r"\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`", lambda m: next(g for g in m.groups() if g is not None), t)


def body_html(md):
    out = []
    for typ, c in blocks(md):
        if typ in ("h1", "h2", "h3"):
            out.append(f"<{typ}>{inline_html(c)}</{typ}>")
        elif typ == "p":
            out.append(f"<p>{inline_html(c)}</p>")
        elif typ in ("ul", "ol"):
            out.append(f"<{typ}>" + "".join(f"<li>{inline_html(x)}</li>" for x in c) + f"</{typ}>")
        elif typ == "quote":
            out.append(f"<blockquote>{inline_html(c)}</blockquote>")
        elif typ == "code":
            out.append(f"<pre><code>{html.escape(c)}</code></pre>")
        elif typ == "hr":
            out.append("<hr/>")
        elif typ == "pagebreak":
            out.append('<div style="page-break-after:always"></div>')
    return "\n".join(out)


CSS = ("body{font-family:Georgia,'Times New Roman',serif;line-height:1.6;max-width:42em;margin:2em auto;padding:0 1em;color:#222}"
       "h1,h2,h3{font-family:'Helvetica Neue',Arial,sans-serif;line-height:1.25}h1{font-size:2em;margin-top:1.5em}"
       "blockquote{border-left:3px solid #ccc;margin:1em 0;padding-left:1em;color:#555}pre{background:#f4f4f4;padding:.8em;"
       "overflow:auto}p{text-align:justify;hyphens:auto}")


# ---------------------------------------------------------------- Formate
def to_html(title, md, author=""):
    return (f'<!doctype html><html lang="de"><head><meta charset="utf-8"><title>{html.escape(title)}</title>'
            f"<style>{CSS}</style></head><body>"
            + (f'<h1 style="text-align:center;margin-top:3em">{html.escape(title)}</h1>' if title and not md.lstrip().startswith("# ") else "")
            + (f'<p style="text-align:center"><i>{html.escape(author)}</i></p>' if author else "")
            + body_html(md) + "</body></html>")


def to_docx(path, title, md, author=""):
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
        from docx.shared import Pt
    except ImportError:
        raise RuntimeError("Für Word-Dateien fehlt python-docx (setup-linux.sh erneut ausführen oder: .venv/bin/pip install python-docx).")
    d = Document()
    d.core_properties.title = title
    if author:
        d.core_properties.author = author
    st = d.styles["Normal"]
    st.font.name, st.font.size = "Georgia", Pt(11.5)
    if title and not md.lstrip().startswith("# "):
        h = d.add_heading(title, 0)
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if author:
            p = d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(author).italic = True
    for typ, c in blocks(md):
        if typ in ("h1", "h2", "h3"):
            d.add_heading(plain(c), int(typ[1]))
        elif typ in ("p", "quote"):
            p = d.add_paragraph(style="Quote" if typ == "quote" and "Quote" in [s.name for s in d.styles] else None)
            for text, b, i in inline_runs(c):
                r = p.add_run(text)
                r.bold, r.italic = b or None, i or None
        elif typ in ("ul", "ol"):
            for x in c:
                p = d.add_paragraph(style="List Bullet" if typ == "ul" else "List Number")
                for text, b, i in inline_runs(x):
                    r = p.add_run(text)
                    r.bold, r.italic = b or None, i or None
        elif typ == "code":
            p = d.add_paragraph()
            r = p.add_run(c)
            r.font.name = "Courier New"
            r.font.size = Pt(9.5)
        elif typ in ("hr", "pagebreak"):
            if typ == "pagebreak":
                d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
            else:
                d.add_paragraph("* * *").alignment = WD_ALIGN_PARAGRAPH.CENTER
    d.save(str(path))


def to_pdf(path, title, md, author=""):
    try:
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (ListFlowable, ListItem, PageBreak, Paragraph, Preformatted, SimpleDocTemplate,
                                        Spacer)
    except ImportError:
        raise RuntimeError("Für PDF fehlt reportlab (setup-linux.sh erneut ausführen oder: .venv/bin/pip install reportlab).")
    font, bold, italic = _pdf_fonts()
    ss = getSampleStyleSheet()
    body = ParagraphStyle("b", parent=ss["BodyText"], fontName=font, fontSize=11, leading=15.5, alignment=TA_JUSTIFY, spaceAfter=6)
    hs = {f"h{i}": ParagraphStyle(f"h{i}", parent=ss[f"Heading{i}"], fontName=bold) for i in (1, 2, 3)}
    quote = ParagraphStyle("q", parent=body, leftIndent=18, textColor="#555555", fontName=italic)
    tstyle = ParagraphStyle("t", parent=ss["Title"], fontName=bold, fontSize=26, leading=32, alignment=TA_CENTER)

    def pml(t):  # Markdown-inline → reportlab-Markup
        t = html.escape(t, quote=False)
        t = re.sub(r"\*\*(.+?)\*\*", rf'<font name="{bold}">\1</font>', t)
        t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", rf'<font name="{italic}">\1</font>', t)
        return re.sub(r"`(.+?)`", r'<font name="Courier">\1</font>', t)

    story = []
    if title and not md.lstrip().startswith("# "):
        story += [Spacer(1, 6 * cm), Paragraph(pml(title), tstyle)]
        if author:
            story.append(Paragraph(pml(author), ParagraphStyle("a", parent=body, alignment=TA_CENTER, fontName=italic)))
        story.append(PageBreak())
    first_h1 = True
    for typ, c in blocks(md):
        if typ == "h1":
            if not first_h1:
                story.append(PageBreak())
            first_h1 = False
            story.append(Paragraph(pml(c), hs["h1"]))
        elif typ in ("h2", "h3"):
            story.append(Paragraph(pml(c), hs[typ]))
        elif typ == "p":
            story.append(Paragraph(pml(c), body))
        elif typ == "quote":
            story.append(Paragraph(pml(c), quote))
        elif typ in ("ul", "ol"):
            story.append(ListFlowable([ListItem(Paragraph(pml(x), body)) for x in c],
                                      bulletType="bullet" if typ == "ul" else "1", bulletFontName=font))
        elif typ == "code":
            story.append(Preformatted(c, ParagraphStyle("c", fontName="Courier", fontSize=8.5, leading=11)))
        elif typ == "hr":
            story.append(Paragraph("* * *", ParagraphStyle("hr", parent=body, alignment=TA_CENTER)))
        elif typ == "pagebreak":
            story.append(PageBreak())

    def foot(canvas, doc):
        canvas.saveState()
        canvas.setFont(font, 9)
        canvas.drawCentredString(A4[0] / 2, 1.2 * cm, str(doc.page))
        canvas.restoreState()

    SimpleDocTemplate(str(path), pagesize=A4, title=title, author=author or "", leftMargin=2.3 * cm, rightMargin=2.3 * cm,
                      topMargin=2.2 * cm, bottomMargin=2.2 * cm).build(story, onLaterPages=foot, onFirstPage=foot)


def _pdf_fonts():
    """TrueType-Schrift mit Umlauten/Sonderzeichen, falls vorhanden (DejaVu), sonst Helvetica."""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        if "LumenSerif" in pdfmetrics.getRegisteredFontNames():
            return "LumenSerif", "LumenSerif-B", "LumenSerif-I"
        for base in ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "/usr/share/fonts/TTF"):
            r, b, i = (Path(base) / f for f in ("DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf", "DejaVuSerif-Italic.ttf"))
            if r.exists() and b.exists() and i.exists():
                pdfmetrics.registerFont(TTFont("LumenSerif", str(r)))
                pdfmetrics.registerFont(TTFont("LumenSerif-B", str(b)))
                pdfmetrics.registerFont(TTFont("LumenSerif-I", str(i)))
                return "LumenSerif", "LumenSerif-B", "LumenSerif-I"
    except Exception:
        pass
    return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"


def to_epub(path, title, md, author=""):
    """EPUB 3 ohne Zusatz-Bibliothek – jedes # Kapitel wird eine eigene Seite."""
    chapters, cur = [], None
    for line in (md or "").split("\n"):
        if re.match(r"^#\s+", line):
            cur = [re.sub(r"^#\s+", "", line).strip(), []]
            chapters.append(cur)
        else:
            if cur is None:
                cur = [title or "Start", []]
                chapters.append(cur)
            cur[1].append(line)
    chapters = [c for c in chapters if c[0].strip() or "".join(c[1]).strip()] or [[title, [md]]]
    uid = f"urn:uuid:{uuid.uuid4()}"
    x = lambda t: html.escape(t or "", quote=True)  # noqa: E731

    def page(t, inner):
        return ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml" '
                f'xmlns:epub="http://www.idpf.org/2007/ops" lang="de" xml:lang="de"><head><meta charset="utf-8"/><title>{x(t)}</title>'
                f'<link rel="stylesheet" href="style.css"/></head><body>{inner}</body></html>')

    def xhtml(s):  # HTML → XHTML-tauglich
        return s.replace("<hr/>", "<hr />").replace("<br>", "<br />")

    with zipfile.ZipFile(path, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                   '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
                   compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/style.css", CSS + "h1{text-align:center;margin:2em 0 1em}.title{text-align:center;margin-top:30%}",
                   compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/title.xhtml", page(title, f'<div class="title"><h1>{x(title)}</h1>' + (f"<p><i>{x(author)}</i></p>" if author else "") + "</div>"),
                   compress_type=zipfile.ZIP_DEFLATED)
        items, spine, nav = [], [], []
        for i, (t, lines) in enumerate(chapters, 1):
            fn = f"kap{i:03d}.xhtml"
            z.writestr("OEBPS/" + fn, page(t, f"<h1>{inline_html(t)}</h1>" + xhtml(body_html("\n".join(lines)))), compress_type=zipfile.ZIP_DEFLATED)
            items.append(f'<item id="k{i}" href="{fn}" media-type="application/xhtml+xml"/>')
            spine.append(f'<itemref idref="k{i}"/>')
            nav.append(f'<li><a href="{fn}">{x(plain(t))}</a></li>')
        z.writestr("OEBPS/nav.xhtml", page("Inhalt", f'<nav epub:type="toc" id="toc"><h1>Inhalt</h1><ol>{"".join(nav)}</ol></nav>'),
                   compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid" xml:lang="de">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="uid">{uid}</dc:identifier><dc:title>{x(title)}</dc:title>
<dc:language>de</dc:language><dc:creator>{x(author or "Lumen")}</dc:creator>
<meta property="dcterms:modified">{datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}</meta></metadata>
<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="css" href="style.css" media-type="text/css"/><item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>
{"".join(items)}</manifest><spine><itemref idref="title"/><itemref idref="nav"/>{"".join(spine)}</spine></package>''',
                   compress_type=zipfile.ZIP_DEFLATED)


def make(path, title, md, fmt=None, author=""):
    """Erstellt ein Dokument. fmt aus FORMATS oder aus der Dateiendung."""
    path = Path(path)
    fmt = (fmt or path.suffix.lstrip(".") or "docx").lower().replace("word", "docx").replace("ebook", "epub").replace("markdown", "md")
    if fmt not in FORMATS:
        raise RuntimeError(f"Unbekanntes Format {fmt}. Möglich: {', '.join(FORMATS)}")
    if path.suffix.lower() != "." + fmt:
        path = path.with_suffix(path.suffix + "." + fmt if path.suffix and len(path.suffix) > 5 else "." + fmt)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "docx":
        to_docx(path, title, md, author)
    elif fmt == "pdf":
        to_pdf(path, title, md, author)
    elif fmt == "epub":
        to_epub(path, title, md, author)
    elif fmt == "html":
        path.write_text(to_html(title, md, author), "utf-8")
    elif fmt == "md":
        path.write_text((f"# {title}\n\n" if title and not md.lstrip().startswith("# ") else "") + md, "utf-8")
    else:
        path.write_text("\n".join(plain(c) if isinstance(c, str) else "\n".join("• " + plain(i) for i in c)
                                  for _, c in blocks(md)), "utf-8")
    return path
