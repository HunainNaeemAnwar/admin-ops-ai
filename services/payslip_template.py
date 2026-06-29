from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from config import PDF_DIR, TAX_PERCENTAGE

# Register fonts
pdfmetrics.registerFont(TTFont("NotoNastaliqUrdu", "/usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Regular.ttf"))
pdfmetrics.registerFont(TTFont("NotoNastaliqUrdu-Bold", "/usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Bold.ttf"))

# --- PROFESSIONAL COLOR PALETTE ---
NAVY = colors.Color(0.12, 0.22, 0.42)
STEEL_BLUE = colors.Color(0.27, 0.45, 0.77)
LIGHT_GREY = colors.Color(0.95, 0.95, 0.95)
WHITE = colors.white
BLACK = colors.black
SOFT_GREEN = colors.Color(0.85, 0.93, 0.85)
DARK_GREEN = colors.Color(0.15, 0.45, 0.15)
DARK_RED = colors.Color(0.75, 0.15, 0.15)

FONT_NAME = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_BOLD_ITALIC = "Helvetica-BoldOblique"
URDU_FONT = "NotoNastaliqUrdu"
URDU_FONT_BOLD = "NotoNastaliqUrdu-Bold"

CELL_PADDING = 6
SECTION_GAP = 2 * mm
TABLE_GAP = 8 * mm


def _format_month(month: int) -> str:
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    return months[month - 1]


def _has_urdu(text: str) -> bool:
    for ch in text:
        if '\u0600' <= ch <= '\u06FF' or '\u0750' <= ch <= '\u077F' or '\uFB50' <= ch <= '\uFDFF' or '\uFE70' <= ch <= '\uFEFF':
            return True
    return False


def _p(text: str, size: int = 10, align: int = 0, bold: bool = False, color=BLACK) -> Paragraph:
    font = URDU_FONT if _has_urdu(text) else FONT_NAME
    if bold and not _has_urdu(text):
        font = FONT_BOLD
    elif bold:
        font = URDU_FONT_BOLD
    style = ParagraphStyle(
        "Cell", alignment=align, fontSize=size, leading=size + 4,
        textColor=color, spaceAfter=0, spaceBefore=0, fontName=font,
    )
    return Paragraph(f"<b>{text}</b>" if bold else text, style)


def _section_heading(text: str) -> Paragraph:
    style = ParagraphStyle(
        "Section", alignment=0, fontSize=11, leading=14,
        textColor=NAVY, spaceAfter=0, spaceBefore=0, fontName=FONT_BOLD_ITALIC,
    )
    return Paragraph(text, style)


def _make_table_style(num_rows: int, col_align: list | None = None) -> TableStyle:
    style_cmds = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.Color(0.75, 0.75, 0.75)),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), CELL_PADDING),
        ("BOTTOMPADDING", (0, 0), (-1, -1), CELL_PADDING),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    if num_rows > 0:
        style_cmds.extend([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ])
        for i in range(2, num_rows):
            if i % 2 == 0:
                style_cmds.append(("BACKGROUND", (0, i), (-1, i), LIGHT_GREY))
    if col_align:
        for col_idx, align in col_align:
            style_cmds.append(("ALIGN", (col_idx, 0), (col_idx, -1), align))
    return TableStyle(style_cmds)


# ── PDF ──
def render_pdf_payslip(data: dict, worker: str, year: int, month: int) -> str:
    filename = f"{worker}_{year}_{month:02d}.pdf"
    filepath = PDF_DIR / filename

    doc = SimpleDocTemplate(
        str(filepath), pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )
    elements = []

    product_totals = data.get("product_totals", {})
    product_rates = data.get("product_rates", {})
    rejection_share = data.get("worker_rejection_share", {})
    all_codes = sorted(set(list(product_totals.keys()) + list(rejection_share.keys())))

    # ── HEADER BAR (Worker Name) ──
    header_font = URDU_FONT_BOLD if _has_urdu(worker) else FONT_BOLD_ITALIC
    header_style = ParagraphStyle("Header", alignment=1, fontSize=20, leading=24, textColor=WHITE, fontName=header_font)
    header_table = Table(
        [[Paragraph(f"<b>{worker}</b>", header_style)]], colWidths=[180 * mm],
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 6 * mm))

    # ── SUBTITLE ──
    sub_style = ParagraphStyle("Sub", alignment=1, fontSize=11, leading=14, textColor=colors.Color(0.4, 0.4, 0.4), fontName=FONT_NAME)
    elements.append(Paragraph(f"{_format_month(month)} {year}", sub_style))
    elements.append(Spacer(1, 10 * mm))

    # ── PRODUCTION SUMMARY ──
    elements.append(_section_heading("PRODUCTION SUMMARY"))
    elements.append(Spacer(1, SECTION_GAP))
    prod_data = [
        [_p("Product", size=10, bold=True, color=WHITE),
         _p("Total Qty", size=10, bold=True, color=WHITE),
         _p("Rejected", size=10, bold=True, color=WHITE),
         _p("Final Qty", size=10, bold=True, color=WHITE)],
    ]
    for code in all_codes:
        total_qty = product_totals.get(code, 0)
        rej_qty = rejection_share.get(code, 0)
        final_qty = total_qty - rej_qty
        prod_data.append([
            _p(code, size=10),
            _p(str(total_qty), size=10),
            _p(str(rej_qty), size=10, color=DARK_RED if rej_qty > 0 else BLACK),
            _p(str(final_qty), size=10),
        ])
    prod_table = Table(prod_data, colWidths=[45 * mm, 45 * mm, 45 * mm, 45 * mm])
    prod_table.setStyle(_make_table_style(len(prod_data)))
    elements.append(prod_table)
    elements.append(Spacer(1, TABLE_GAP))

    # ── EARNINGS ──
    elements.append(_section_heading("EARNINGS"))
    elements.append(Spacer(1, SECTION_GAP))
    earn_data = [
        [_p("Product", size=10, bold=True, color=WHITE),
         _p("Final Qty", size=10, bold=True, color=WHITE),
         _p("Rate (Rs)", size=10, bold=True, color=WHITE),
         _p("Amount (Rs)", size=10, bold=True, color=WHITE)],
    ]
    for code in all_codes:
        total_qty = product_totals.get(code, 0)
        rej_qty = rejection_share.get(code, 0)
        final_qty = total_qty - rej_qty
        rate = product_rates.get(code, 0)
        amount = final_qty * rate
        earn_data.append([
            _p(code, size=10),
            _p(str(final_qty), size=10),
            _p(f"{rate:,.2f}", size=10),
            _p(f"{amount:,.2f}", size=10),
        ])
    earn_table = Table(earn_data, colWidths=[45 * mm, 45 * mm, 45 * mm, 45 * mm])
    earn_table.setStyle(_make_table_style(len(earn_data)))
    elements.append(earn_table)
    elements.append(Spacer(1, 10 * mm))

    # ── SUMMARY BOXES ──
    box_style = ParagraphStyle("Box", alignment=1, fontSize=11, leading=15, spaceAfter=1, fontName=FONT_NAME)

    def _make_box(lines, border_color, bg_color=None, width=80 * mm):
        box_data = []
        for label, value in lines:
            box_data.append([
                Paragraph(f"<b>{label}</b>", box_style),
                Paragraph(f"<b>{value}</b>", box_style),
            ])
        style_cmds = [
            ("BOX", (0, 0), (-1, -1), 1.5, border_color),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
        if bg_color:
            style_cmds.append(("BACKGROUND", (0, 0), (-1, -1), bg_color))
        box = Table(box_data, colWidths=[width, width])
        box.setStyle(TableStyle(style_cmds))
        return box

    gross_box = _make_box([("Gross Salary", f"Rs. {data['gross_total']:,.2f}")], NAVY, LIGHT_GREY)
    elements.append(gross_box)
    elements.append(Spacer(1, 3 * mm))

    arr_style = ParagraphStyle("Arrow", alignment=1, fontSize=12, leading=14, textColor=NAVY, fontName=FONT_NAME)
    elements.append(Paragraph("<b>▼</b>", arr_style))
    elements.append(Spacer(1, 3 * mm))

    ded_lines = []
    if data["rejection_deduction"] > 0:
        ded_lines.append(("Rejection Deduction", f"- Rs. {data['rejection_deduction']:,.2f}"))
    if data["advance_deduction"] > 0:
        ded_lines.append(("Advance Deduction", f"- Rs. {data['advance_deduction']:,.2f}"))
    ded_lines.append((f"Tax Deduction ({TAX_PERCENTAGE}%)", f"- Rs. {data['tax_total']:,.2f}"))
    ded_box = _make_box(ded_lines, DARK_RED)
    elements.append(ded_box)
    elements.append(Spacer(1, 3 * mm))

    elements.append(Paragraph("<b>▼</b>", arr_style))
    elements.append(Spacer(1, 3 * mm))

    net_box = _make_box([("NET PAYABLE SALARY", f"Rs. {data['net_payable']:,.2f}")], DARK_GREEN, SOFT_GREEN)
    elements.append(net_box)
    elements.append(Spacer(1, 15 * mm))

    elements.append(Paragraph(
        f"Generated on: {date.today().isoformat()}",
        ParagraphStyle("Footer", alignment=1, fontSize=8, textColor=colors.grey, fontName=FONT_NAME),
    ))

    doc.build(elements)
    return str(filepath)



