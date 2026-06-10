import os
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from config import PDF_DIR, EXCEL_SLIPS_DIR
from tools.calc_tools import calc_worker_payslip
from tools.excel_tools import get_worker_entries
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment


def _format_month(month: int) -> str:
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    return months[month - 1]


def generate_pdf_payslip(worker: str, year: int, month: int) -> str:
    data = calc_worker_payslip(worker, year, month)
    if "error" in data:
        return data["error"]

    filename = f"{worker}_{year}_{month:02d}.pdf"
    filepath = PDF_DIR / filename
    doc = SimpleDocTemplate(
        str(filepath), pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], spaceAfter=6*mm)
    normal = styles["Normal"]
    elements = []

    elements.append(Paragraph(f"Pay Slip - {_format_month(month)} {year}", title_style))
    elements.append(Paragraph(f"Worker: {worker}", normal))
    elements.append(Spacer(1, 6*mm))

    prod_data = [[
        Paragraph("<b>Product</b>", normal),
        Paragraph("<b>Description</b>", normal),
        Paragraph("<b>Qty</b>", normal),
        Paragraph("<b>Gross (Rs)</b>", normal),
    ]]
    for pb in data["product_breakdown"]:
        prod_data.append([
            pb["product_code"],
            pb["description"],
            str(pb["quantity"]),
            f'{pb["gross"]:,.2f}',
        ])
    prod_data.append([
        Paragraph("<b>Total</b>", normal), "", str(data["total_pieces"]),
        f'{data["total_gross"]:,.2f}'
    ])
    col_widths = [60*mm, 60*mm, 20*mm, 30*mm]
    t = Table(prod_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.27, 0.45, 0.77)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (2, 0), (3, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.Color(0.9, 0.9, 0.9)),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 6*mm))

    summary_data = [
        ["Description", "Amount (Rs)"],
        ["Gross Total", f'{data["total_gross"]:,.2f}'],
        [f'Tax Deducted ({data["total_entries"] > 0 and 3 or 0}%)', f'({data["total_tax"]:,.2f})'],
        ["Net Payable", f'{data["total_net"]:,.2f}'],
    ]
    st = Table(summary_data, colWidths=[80*mm, 50*mm])
    st.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.27, 0.45, 0.77)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.Color(0.9, 0.9, 0.9)),
    ]))
    elements.append(st)
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(f"Generated on: {date.today().isoformat()}", normal))

    doc.build(elements)
    return str(filepath)


def generate_excel_payslip(worker: str, year: int, month: int) -> str:
    data = calc_worker_payslip(worker, year, month)
    if "error" in data:
        return data["error"]

    filename = f"{worker}_{year}_{month:02d}.xlsx"
    filepath = EXCEL_SLIPS_DIR / filename
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pay Slip"
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=11)

    ws.cell(row=1, column=1, value=f"Pay Slip - {_format_month(month)} {year}").font = Font(bold=True, size=14)
    ws.cell(row=2, column=1, value=f"Worker: {worker}").font = Font(bold=True, size=12)
    ws.merge_cells("A1:D1")
    ws.merge_cells("A2:D2")

    headers = ["Product", "Description", "Quantity", "Gross (Rs)"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    row = 5
    for pb in data["product_breakdown"]:
        ws.cell(row=row, column=1, value=pb["product_code"])
        ws.cell(row=row, column=2, value=pb["description"])
        ws.cell(row=row, column=3, value=pb["quantity"])
        ws.cell(row=row, column=4, value=pb["gross"])
        row += 1

    ws.cell(row=row, column=1, value="Total").font = Font(bold=True)
    ws.cell(row=row, column=3, value=data["total_pieces"]).font = Font(bold=True)
    ws.cell(row=row, column=4, value=data["total_gross"]).font = Font(bold=True)
    row += 2

    ws.cell(row=row, column=1, value="Gross Total").font = Font(bold=True)
    ws.cell(row=row, column=4, value=data["total_gross"]).font = Font(bold=True)
    row += 1
    ws.cell(row=row, column=1, value="Tax Deducted").font = Font(bold=True)
    ws.cell(row=row, column=4, value=data["total_tax"]).font = Font(bold=True)
    row += 1
    ws.cell(row=row, column=1, value="Net Payable").font = Font(bold=True, size=12)
    ws.cell(row=row, column=4, value=data["total_net"]).font = Font(bold=True, size=12, color="006400")

    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 15
    wb.save(filepath)
    return str(filepath)
