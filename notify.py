"""
Email notifier — Gmail SMTP, same setup that passed test_email.py.

Reads from .env:
  GMAIL_USER
  GMAIL_APP_PASSWORD
  MAIL_TO
"""
import os
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
MAIL_TO = os.getenv("MAIL_TO")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def notify(jobs):
    """Send one email summarising all new jobs. No-op if jobs is empty."""
    if not jobs:
        return "email: nothing to send"

    if not all([GMAIL_USER, GMAIL_APP_PASSWORD, MAIL_TO]):
        return "email: skipped (missing .env vars)"

    current_date = datetime.datetime.now().strftime("%d-%m-%Y")
    subject = f"Mara Novi oglasi pripravnik Split - {current_date}"

    lines = []
    for j in jobs:
        lines.append(
            f"\u2022 {j.title}\n"
            f"  Mjesto: {j.location}\n"
            f"  Poslodavac: {j.employer}\n"
            f"  Rok prijave: {j.deadline}\n"
            f"  {j.url}"
        )
    body = (
        f"Prona\u0111eno {len(jobs)} novi oglas(a) koji sadr\u017ee 'pripravnik':\n\n"
        + "\n\n".join(lines)
    )

    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = MAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, [MAIL_TO], msg.as_string())
        return f"email: sent to {MAIL_TO}"
    except Exception as e:
        return f"email: error {e}"
