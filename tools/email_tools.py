import base64
from datetime import date, timedelta
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from io import BytesIO

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import MANAGER_EMAIL
from tools.oauth_tools import get_valid_credentials, list_authorized_users
from tools.database import get_daily_totals, get_all_products
from tools.export_tools import generate_excel_report, generate_monthly_excel_stream


def _gmail_service(email: str):
    creds = get_valid_credentials(email)
    if not creds:
        return None
    return build("gmail", "v1", credentials=creds)


def send_email(from_email: str, to: str, subject: str, body: str,
               attachment_path: str = "",
               attachment_bytes: BytesIO | None = None,
               attachment_filename: str = "",
               is_html: bool = False) -> str:
    service = _gmail_service(from_email)
    if not service:
        return (
            f"Error: {from_email} not authenticated. "
            f"Please login at /login first."
        )
    try:
        subtype = "html" if is_html else "plain"

        if attachment_path or attachment_bytes:
            msg = MIMEMultipart()
            msg.attach(MIMEText(body, subtype))
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = to

            part = MIMEBase("application", "octet-stream")
            if attachment_bytes:
                part.set_payload(attachment_bytes.getvalue())
                filename = attachment_filename or "attachment.xlsx"
            else:
                with open(attachment_path, "rb") as f:
                    part.set_payload(f.read())
                filename = attachment_path.split("/")[-1]
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={filename}")
            msg.attach(part)
        else:
            msg = EmailMessage()
            msg.set_content(body, subtype=subtype)
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = to

        encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        body_raw = {"raw":encoded}
        result = service.users().messages().send(userId="me", body=body_raw).execute()
        return f"Email sent to {to} (Gmail API) | ID: {result.get('id')}"
    except HttpError as e:
        return f"Error sending email: {e}"
    except Exception as e:
        return f"Error: {e}"


def _format_period(period: str, year: int, month: int, day: int) -> str:
    if period == "daily":
        return f"{year}-{month:02d}-{day:02d}"
    elif period == "weekly":
        dt = date(year, month, day)
        monday = dt - timedelta(days=dt.weekday())
        sunday = monday + timedelta(days=6)
        return f"{monday.isoformat()} to {sunday.isoformat()}"
    elif period == "monthly":
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return f"{months[month-1]} {year}"
    return ""


def _build_quantities_report(period: str, year: int, month: int, day: int) -> str:
    products = get_all_products()
    product_codes = [p["code"] for p in products]

    lines = []

    if period == "weekly":
        dt = date(year, month, day)
        monday = dt - timedelta(days=dt.weekday())
        for i in range(7):
            d = monday + timedelta(days=i)
            ds = d.isoformat()
            totals = get_daily_totals(ds)
            has_data = any(totals.values())
            if has_data:
                lines.append(f"{d.strftime('%A')} ({ds}):")
                for code in product_codes:
                    qty = totals.get(code, 0)
                    if qty > 0:
                        lines.append(f"  {code}: {qty} pcs")
                lines.append("")
        if not any(get_daily_totals((monday + timedelta(days=i)).isoformat()) for i in range(7)):
            lines.append("  No production recorded for this week.")
    else:
        if period == "daily":
            date_str = f"{year}-{month:02d}-{day:02d}"
            totals = get_daily_totals(date_str)
            period_label = date_str
        else:
            totals = {}
            from tools.database import get_worker_month_production, get_active_workers
            for w in get_active_workers():
                entries = get_worker_month_production(w["id"], year, month)
                for e in entries:
                    code = e["product_code"]
                    totals[code] = totals.get(code, 0) + e["quantity"]
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            period_label = f"{months[month-1]} {year}"

        has_data = any(v > 0 for v in totals.values())
        if has_data:
            for code in product_codes:
                qty = totals.get(code, 0)
                if qty > 0:
                    lines.append(f"  {code}: {qty} pcs")
        else:
            lines.append("  No production recorded.")

    return "\n".join(lines)


def _build_html_report(period: str, year: int, month: int, day: int) -> str:
    """Build an HTML table of production quantities for the given period."""
    products = get_all_products()
    product_codes = [p["code"] for p in products]

    totals: dict[str, int] = {}
    has_data = False

    if period == "monthly":
        from tools.database import get_worker_month_production, get_active_workers
        for w in get_active_workers():
            entries = get_worker_month_production(w["id"], year, month)
            for e in entries:
                code = e["product_code"]
                totals[code] = totals.get(code, 0) + e["quantity"]
        has_data = any(v > 0 for v in totals.values())
    elif period == "daily":
        date_str = f"{year}-{month:02d}-{day:02d}"
        totals = get_daily_totals(date_str)
        has_data = any(v > 0 for v in totals.values())
    else:  # weekly
        dt = date(year, month, day)
        monday = dt - timedelta(days=dt.weekday())
        for i in range(7):
            d = (monday + timedelta(days=i)).isoformat()
            for code, qty in get_daily_totals(d).items():
                totals[code] = totals.get(code, 0) + qty
        has_data = any(v > 0 for v in totals.values())

    if not has_data:
        return "<p><em>No production recorded for this period.</em></p>"

    rows_html = ""
    for c in product_codes:
        qty = totals.get(c, 0)
        if qty > 0:
            rows_html += f"<tr><td style='padding:6px 10px;border:1px solid #ddd;'>{c}</td><td style='padding:6px 10px;border:1px solid #ddd;text-align:right;'>{qty:,}</td></tr>\n"

    return f"""<table style="border-collapse:collapse;width:100%;max-width:500px;font-family:Arial,sans-serif;font-size:13px;">
<thead><tr style="background:#f5f5f5;">
  <th style="padding:8px 10px;border:1px solid #ddd;text-align:left;">Product</th>
  <th style="padding:8px 10px;border:1px solid #ddd;text-align:right;">Qty (pcs)</th>
</tr></thead>
<tbody>
{rows_html}</tbody></table>"""


def send_report(period: str, year: int, month: int, day: int) -> str:
    users = list_authorized_users()
    if not users:
        return (
            "Error: No authenticated Gmail users found. "
            "Go to /login to authorize your Gmail account."
        )
    from_email = users[0]
    if not MANAGER_EMAIL:
        return "Error: MANAGER_EMAIL not set in .env"

    period_label = period.capitalize()
    period_str = _format_period(period, year, month, day)

    html_table = _build_html_report(period, year, month, day)

    html_body = f"""<html><body style="font-family:Arial,sans-serif;color:#333;line-height:1.6;max-width:600px;">
<p>Dear Manager,</p>
<p>Following is the production report for <strong>{period_str}</strong>.</p>
<h3 style="color:#555;font-size:14px;margin:16px 0 8px;">Production Summary</h3>
{html_table}
<br>
<p>Regards,<br>
<strong>Admin Ops AI</strong><br>
<em style="color:#888;font-size:12px;">An Autonomous Factory Agent</em></p>
</body></html>"""

    subject = f"Production Report – {period_label} {period_str}"

    if period == "monthly":
        buf, filename = generate_monthly_excel_stream(year, month)
        return send_email(from_email, MANAGER_EMAIL, subject, html_body,
                          attachment_bytes=buf, attachment_filename=filename, is_html=True)
    elif period == "weekly":
        attachment_path = generate_excel_report(period, year, month, day)
        return send_email(from_email, MANAGER_EMAIL, subject, html_body,
                          attachment_path=attachment_path, is_html=True)

    return send_email(from_email, MANAGER_EMAIL, subject, html_body, is_html=True)


def send_summary(period: str, year: int, month: int, day: int) -> str:
    return send_report(period, year, month, day)
