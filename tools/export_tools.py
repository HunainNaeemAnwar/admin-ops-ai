from datetime import date
from pathlib import Path
from typing import Optional

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from config import DAILY_LOGS_DIR, FIXED_WORKERS
from tools.database import (
    get_daily_totals,
    get_active_workers,
    get_all_products,
    get_worker_month_production,
)


def generate_excel_report(period: str = "daily", year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> str:
    today = date.today()
    y = year or today.year
    m = month or today.month
    d = day or today.day

    products = get_all_products()
    product_codes = [p["code"] for p in products]

    if period == "daily":
        return _daily_excel_report(y, m, d, product_codes)
    elif period == "weekly":
        return _weekly_excel_report(y, m, d, product_codes)
    elif period == "monthly":
        return _monthly_excel_report(y, m, product_codes)
    return f"Unknown period '{period}'"


def _thin_border():
    s = Side(style="thin")
    return Border(left=s, right=s, top=s, bottom=s)


def _style_header(ws, row: int, cols: int):
    fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    font = Font(color="FFFFFF", bold=True, size=11)
    center = Alignment(horizontal="center", vertical="center")
    for c in range(1, cols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = fill
        cell.font = font
        cell.alignment = center
        cell.border = _thin_border()


def _daily_excel_report(year: int, month: int, day: int, product_codes: list[str]) -> str:
    date_str = f"{year}-{month:02d}-{day:02d}"
    totals = get_daily_totals(date_str)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Daily {day:02d}-{month:02d}"

    ws.cell(row=1, column=1, value=f"Daily Production Report - {date_str}").font = Font(bold=True, size=14)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(product_codes) + 1)

    headers = ["Product"] + product_codes + ["Total"]
    _style_header(ws, 3, len(headers))

    row = 4
    total_row = 0
    for code in product_codes:
        qty = totals.get(code, 0)
        ws.cell(row=row, column=1, value=code).border = _thin_border()
        ws.cell(row=row, column=2, value=qty).border = _thin_border()
        ws.cell(row=row, column=2).alignment = Alignment(horizontal="center")
        total_row += qty
        row += 1

    ws.cell(row=row, column=1, value="Grand Total").font = Font(bold=True)
    ws.cell(row=row, column=1).border = _thin_border()
    ws.cell(row=row, column=2, value=total_row).font = Font(bold=True)
    ws.cell(row=row, column=2).border = _thin_border()
    ws.cell(row=row, column=2).alignment = Alignment(horizontal="center")

    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 14

    filepath = DAILY_LOGS_DIR / f"report_daily_{date_str}.xlsx"
    wb.save(filepath)
    return str(filepath)


def _weekly_excel_report(year: int, month: int, day: int, product_codes: list[str]) -> str:
    from datetime import date as dt_date, timedelta
    dt = dt_date(year, month, day)
    monday = dt - timedelta(days=dt.weekday())
    sunday = monday + timedelta(days=6)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Weekly {monday.isoformat()}"

    ws.cell(row=1, column=1, value=f"Weekly Production Report - {monday.isoformat()} to {sunday.isoformat()}").font = Font(bold=True, size=14)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(product_codes) + 2)

    headers = ["Date", "Day"] + product_codes + ["Total"]
    _style_header(ws, 3, len(headers))

    row = 4
    grand_total = 0
    for i in range(7):
        d = monday + timedelta(days=i)
        ds = d.isoformat()
        totals = get_daily_totals(ds)
        ws.cell(row=row, column=1, value=ds).border = _thin_border()
        ws.cell(row=row, column=2, value=d.strftime("%A")).border = _thin_border()
        day_total = 0
        for j, code in enumerate(product_codes):
            qty = totals.get(code, 0)
            cell = ws.cell(row=row, column=3 + j, value=qty)
            cell.border = _thin_border()
            cell.alignment = Alignment(horizontal="center")
            day_total += qty
        grand_total += day_total
        ws.cell(row=row, column=3 + len(product_codes), value=day_total).border = _thin_border()
        ws.cell(row=row, column=3 + len(product_codes)).alignment = Alignment(horizontal="center")
        row += 1

    ws.cell(row=row, column=1, value="Grand Total").font = Font(bold=True)
    ws.cell(row=row, column=1).border = _thin_border()
    ws.cell(row=row, column=3 + len(product_codes), value=grand_total).font = Font(bold=True)
    ws.cell(row=row, column=3 + len(product_codes)).border = _thin_border()

    for j, code in enumerate(product_codes):
        col_letter = chr(67 + j)
        ws.cell(row=row, column=3 + j).value = f"=SUM({col_letter}4:{col_letter}{row-1})"
        ws.cell(row=row, column=3 + j).font = Font(bold=True)
        ws.cell(row=row, column=3 + j).border = _thin_border()
        ws.cell(row=row, column=3 + j).alignment = Alignment(horizontal="center")

    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 12
    for j in range(len(product_codes)):
        ws.column_dimensions[chr(67 + j)].width = 12

    filepath = DAILY_LOGS_DIR / f"report_weekly_{monday.isoformat()}.xlsx"
    wb.save(filepath)
    return str(filepath)


def _monthly_excel_report(year: int, month: int, product_codes: list[str]) -> str:
    from calendar import monthrange
    days = monthrange(year, month)[1]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Monthly {year}-{month:02d}"

    ws.cell(row=1, column=1, value=f"Monthly Production Report - {year}-{month:02d}").font = Font(bold=True, size=14)
    total_cols = 2 + len(product_codes)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)

    headers = ["Date"] + product_codes + ["Total"]
    _style_header(ws, 3, len(headers))

    row = 4
    grand_totals = {code: 0 for code in product_codes}
    for d in range(1, days + 1):
        date_str = f"{year}-{month:02d}-{d:02d}"
        totals = get_daily_totals(date_str)
        day_total = sum(totals.values())
        if day_total == 0:
            continue
        ws.cell(row=row, column=1, value=date_str).border = _thin_border()
        for j, code in enumerate(product_codes):
            qty = totals.get(code, 0)
            ws.cell(row=row, column=2 + j, value=qty).border = _thin_border()
            ws.cell(row=row, column=2 + j).alignment = Alignment(horizontal="center")
            grand_totals[code] += qty
        ws.cell(row=row, column=total_cols, value=day_total).border = _thin_border()
        ws.cell(row=row, column=total_cols).alignment = Alignment(horizontal="center")
        row += 1

    ws.cell(row=row, column=1, value="Grand Total").font = Font(bold=True)
    ws.cell(row=row, column=1).border = _thin_border()
    for j, code in enumerate(product_codes):
        ws.cell(row=row, column=2 + j, value=grand_totals[code]).font = Font(bold=True)
        ws.cell(row=row, column=2 + j).border = _thin_border()
        ws.cell(row=row, column=2 + j).alignment = Alignment(horizontal="center")

    grand_total = sum(grand_totals.values())
    ws.cell(row=row, column=total_cols, value=grand_total).font = Font(bold=True)
    ws.cell(row=row, column=total_cols).border = _thin_border()

    ws.column_dimensions["A"].width = 14
    for j in range(len(product_codes)):
        ws.column_dimensions[chr(66 + j)].width = 12

    filepath = DAILY_LOGS_DIR / f"report_monthly_{year}-{month:02d}.xlsx"
    wb.save(filepath)
    return str(filepath)
