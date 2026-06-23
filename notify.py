"""
Notifications: Gmail email + Twilio SMS.

Both channels fire on new jobs. Any channel whose .env vars are missing is
silently skipped, so you can run email-only, SMS-only, or both.

.env keys:
  Email:  GMAIL_USER, GMAIL_APP_PASSWORD, MAIL_TO
  SMS:    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM, TWILIO_TO
"""
import os
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

load_dotenv()

# --- Email config ---
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
MAIL_TO = os.getenv("MAIL_TO")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# --- SMS config ---
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")
TWILIO_TO = os.getenv("TWILIO_TO")


def _format_email_body(jobs):
    lines = []
    for j in jobs:
        lines.append(
            f"\u2022 {j.title}\n"
            f"  Mjesto: {j.location}\n"
            f"  Poslodavac: {j.employer}\n"
            f"  Rok/datum: {j.deadline}\n"
            f"  {j.url}"
        )
    return (
        f"Prona\u0111eno {len(jobs)} novi oglas(a) koji sadr\u017ee 'pripravnik':\n\n"
        + "\n\n".join(lines)
    )


def _send_email(jobs):
    if not all([GMAIL_USER, GMAIL_APP_PASSWORD, MAIL_TO]):
        return "email: skipped (missing .env vars)"
    current_date = datetime.datetime.now().strftime("%d-%m-%Y")
    subject = f"Mara Novi HZZ/Ljekarne SDZ Oglasi Pripravnik - {current_date}"
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = MAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(_format_email_body(jobs), "plain", "utf-8"))
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, [MAIL_TO], msg.as_string())
        return f"email: sent to {MAIL_TO}"
    except Exception as e:
        return f"email: error {e}"


def _format_sms_body(jobs):
    # SMS is short; keep it tight. One line per job, title + location.
    parts = [f"{len(jobs)} novi pripravnik oglas(a):"]
    for j in jobs[:5]:  # cap so we don't blow past a couple SMS segments
        loc = f" ({j.location})" if j.location else ""
        parts.append(f"- {j.title}{loc}")
    if len(jobs) > 5:
        parts.append(f"...i jo\u0161 {len(jobs) - 5}. Vidi email za detalje.")
    return "\n".join(parts)


def _send_sms(jobs):
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, TWILIO_TO]):
        return "sms: skipped (missing .env vars)"
    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        msg = client.messages.create(
            body=_format_sms_body(jobs),
            from_=TWILIO_FROM,
            to=TWILIO_TO,
        )
        return f"sms: queued {msg.sid} ({msg.status})"
    except Exception as e:
        return f"sms: error {e}"


def notify(jobs):
    """Fire all configured channels for a batch of new jobs."""
    if not jobs:
        return ["nothing to send"]
    return [_send_email(jobs), _send_sms(jobs)]
