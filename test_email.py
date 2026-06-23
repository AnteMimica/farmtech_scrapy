"""
Standalone email test — verifies Gmail SMTP works before touching the scraper.

Run:  python test_email.py

Reads credentials from a .env file in the same folder:
  GMAIL_USER=testotp2802@gmail.com
  GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx
  MAIL_TO=amimic00@fesb.hr
"""
import os
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

load_dotenv()  # pulls .env into environment variables

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
MAIL_TO = os.getenv("MAIL_TO")

# Fail loudly if something's missing, rather than a cryptic SMTP error
missing = [k for k, v in {
    "GMAIL_USER": GMAIL_USER,
    "GMAIL_APP_PASSWORD": GMAIL_APP_PASSWORD,
    "MAIL_TO": MAIL_TO,
}.items() if not v]
if missing:
    raise SystemExit(f"Missing in .env: {', '.join(missing)}")


def send_test_email():
    current_date = datetime.datetime.now().strftime("%d-%m-%Y")

    smtp_server = "smtp.gmail.com"
    smtp_port = 587  # TLS

    subject = f"Vranjky Novi HZZ Oglasi - {current_date}"
    body = (
        "Ovo je testna poruka iz JobWatch skripte.\n\n"
        "Ako vidiš ovaj email, SMTP slanje radi ispravno.\n"
        f"Vrijeme: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}"
    )

    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = ", ".join([MAIL_TO]) if isinstance(MAIL_TO, str) else ", ".join(MAIL_TO)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    print(f"Connecting to {smtp_server}:{smtp_port} ...")
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.set_debuglevel(0)        # set to 1 to see the full SMTP conversation
        server.starttls()               # upgrade to encrypted TLS
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, [MAIL_TO], msg.as_string())
    print(f"✓ Email sent to {MAIL_TO}")


if __name__ == "__main__":
    send_test_email()