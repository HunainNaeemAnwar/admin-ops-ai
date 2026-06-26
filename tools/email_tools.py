import base64
from datetime import date, timedelta
from email.message import EmailMessage
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
               attachment_filename: str = "") -> str:
    service = _gmail_service(from_email)
    if not service:
        return (
            f"Error: {from_email} not authenticated. "
            f"Please login at /login first."
        )
    try:
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders

        if attachment_path or attachment_bytes:
            msg = MIMEMultipart()
            msg.attach(MIMEText(body, "plain"))
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
            msg.set_content(body)
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

    body_lines = [
        "Dear Manager,",
        "",
        f"Following is the production report for {period_str}.",
        "",
        "Department Totals (quantities only):",
        "",
    ]
    body_lines.append(_build_quantities_report(period, year, month, day))
    body_lines.extend(["", "Regards,", "Admin Ops AI"])

    subject = f"Production Report – {period_label} {period_str}"

    if period == "monthly":
        buf, filename = generate_monthly_excel_stream(year, month)
        return send_email(from_email, MANAGER_EMAIL, subject, "\n".join(body_lines),
                          attachment_bytes=buf, attachment_filename=filename)
    elif period == "weekly":
        attachment_path = generate_excel_report(period, year, month, day)
        return send_email(from_email, MANAGER_EMAIL, subject, "\n".join(body_lines), attachment_path)

    return send_email(from_email, MANAGER_EMAIL, subject, "\n".join(body_lines))


def send_summary(period: str, year: int, month: int, day: int) -> str:
    return send_report(period, year, month, day)
