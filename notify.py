"""
Notifications: Gmail email + Twilio SMS.

Supports multiple recipients via comma-separated .env values:
  MAIL_TO=a@x.com,b@y.com
  TWILIO_TO=+385111111111,+385222222222

Both channels fire on new jobs. Any channel whose .env vars are missing is
silently skipped. Email and SMS are independent — one failing never blocks
the other.
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
MAIL_TO = os.getenv("MAIL_TO", "")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# --- SMS config ---
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")
TWILIO_TO = os.getenv("TWILIO_TO", "")


def _split(value):
    """Turn a comma-separated env string into a clean list."""
    return [v.strip() for v in value.split(",") if v.strip()]


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
    recipients = _split(MAIL_TO)
    if not all([GMAIL_USER, GMAIL_APP_PASSWORD]) or not recipients:
        return "email: skipped (missing .env vars)"
    current_date = datetime.datetime.now().strftime("%d-%m-%Y")
    subject = f"Mara Novi HZZ/Ljekarne SDZ Pripravnik - {current_date}"
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = ", ".join(recipients)        # all recipients in one email
    msg["Subject"] = subject
    msg.attach(MIMEText(_format_email_body(jobs), "plain", "utf-8"))
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, recipients, msg.as_string())
        return f"email: sent to {len(recipients)} recipient(s)"
    except Exception as e:
        return f"email: error {e}"


def _ascii(s):
    """Strip Croatian diacritics to plain ASCII for SMS (keeps it GSM-7, shorter)."""
    table = str.maketrans({
        "\u010d": "c", "\u0107": "c", "\u017e": "z", "\u0161": "s", "\u0111": "dj",
        "\u010c": "C", "\u0106": "C", "\u017d": "Z", "\u0160": "S", "\u0110": "Dj",
    })
    return s.translate(table)


def _abbrev_title(title, chars=3):
    """First `chars` letters of each word: 'Farmaceutski tehnicar' -> 'Far teh'."""
    words = _ascii(title).split()
    return " ".join(w[:chars] for w in words if w)


def _site_tag(site):
    """Short source label for the SMS."""
    return {"hzz": "HZZ", "ljekarnesdz": "LJK"}.get(site, site.upper()[:3])


def _format_sms_body(jobs):
    # Always-present prefix
    parts = ["mara novi pripravnik:"]
    for j in jobs:
        tag = _site_tag(getattr(j, "site", ""))
        short = _abbrev_title(j.title)
        city = _ascii(j.location).strip()
        entry = f"{tag} {short}" + (f" {city}" if city else "")
        parts.append(entry)
    # Join compactly; lists all ads (may span multiple SMS segments)
    return " | ".join(parts)


def _send_sms(jobs):
    recipients = _split(TWILIO_TO)
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM]) or not recipients:
        return "sms: skipped (missing .env vars)"
    try:
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        body = _format_sms_body(jobs)
        results = []
        for to in recipients:
            try:
                msg = client.messages.create(body=body, from_=TWILIO_FROM, to=to)
                results.append(f"{to}:{msg.status}")
            except Exception as e:
                results.append(f"{to}:error {e}")
        return "sms: " + ", ".join(results)
    except Exception as e:
        return f"sms: error {e}"


def notify(jobs):
    """Fire all configured channels for a batch of new jobs."""
    if not jobs:
        return ["nothing to send"]
    return [_send_email(jobs), _send_sms(jobs)]
