import base64
from email.message import EmailMessage

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import MANAGER_EMAIL
from tools.oauth_tools import get_valid_credentials, list_authorized_users


def _gmail_service(email: str):
    creds = get_valid_credentials(email)
    if not creds:
        return None
    return build("gmail", "v1", credentials=creds)


def send_email(from_email: str, to: str, subject: str, body: str) -> str:
    service = _gmail_service(from_email)
    if not service:
        return (
            f"Error: {from_email} not authenticated. "
            f"Please login at /login first."
        )
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to
        encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        body = {"raw": encoded}
        result = service.users().messages().send(userId="me", body=body).execute()
        return f"Email sent to {to} (Gmail API) | ID: {result.get('id')}"
    except HttpError as e:
        return f"Error sending email: {e}"
    except Exception as e:
        return f"Error: {e}"


def send_daily_summary(year: int, month: int, day: int, summary: dict) -> str:
    users = list_authorized_users()
    if not users:
        return (
            "Error: No authenticated Gmail users found. "
            "Go to /login to authorize your Gmail account."
        )
    from_email = users[0]
    if not MANAGER_EMAIL:
        return "Error: MANAGER_EMAIL not set in .env"
    subject = f"Daily Production Summary - {year}-{month:02d}-{day:02d}"
    lines = [
        f"Daily Production Summary",
        f"Date: {year}-{month:02d}-{day:02d}",
        "",
        f"Workers: {summary['workers_count']}",
        f"Entries: {summary['entries_count']}",
        f"Total Pieces: {summary['total_pieces']}",
        f"Gross Amount: Rs {summary['total_gross']:,.2f}",
        f"Tax Deducted: Rs {summary['total_tax']:,.2f}",
        f"Net Amount: Rs {summary['total_net']:,.2f}",
        "",
        "Workers:",
    ]
    for w in summary["workers"]:
        lines.append(f"  - {w}")
    lines.append("")
    lines.append("---")
    lines.append("This is an automated report from Admin Ops AI.")
    return send_email(from_email, MANAGER_EMAIL, subject, "\n".join(lines))
