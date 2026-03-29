#!/usr/bin/env python3
"""Send emails via SMTP (Gmail App Password)."""

import sys
import io
import json
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Load .env if SMTP vars not already in environment
SKILL_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SKILL_DIR.parent.parent

_ENV_CANDIDATES = [
    PROJECT_ROOT / ".env",                          # OpenClaw workspace root
    Path("D:/Myapps/buddy agent/.env"),             # Dev repo
    Path.home() / ".openclaw" / "workspace" / ".env",
]

if not os.environ.get("SMTP_USER"):
    for _env_path in _ENV_CANDIDATES:
        if _env_path.exists():
            with open(_env_path, encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line and not _line.startswith("#") and "=" in _line:
                        _key, _, _val = _line.partition("=")
                        _key = _key.strip()
                        _val = _val.strip().strip('"').strip("'")
                        if _key and _val:
                            os.environ.setdefault(_key, _val)
            break


def send_via_smtp(to: str, subject: str, body: str,
                  from_name: str = "Buddy Agent",
                  cc: str = "", bcc: str = "",
                  attachment: str = "") -> dict:
    """Send email via Gmail SMTP."""
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_APP_PASSWORD", "")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    if not smtp_user or not smtp_pass:
        return {"status": "error", "message": "SMTP credentials not configured. Set SMTP_USER and SMTP_APP_PASSWORD."}

    msg = MIMEMultipart()
    msg["From"] = f"{from_name} <{smtp_user}>"
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Attachment
    if attachment and Path(attachment).exists():
        filepath = Path(attachment)
        part = MIMEBase("application", "octet-stream")
        with open(filepath, "rb") as f:
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={filepath.name}")
        msg.attach(part)

    # Build recipient list
    recipients = [to]
    if cc:
        recipients.extend([addr.strip() for addr in cc.split(",")])
    if bcc:
        recipients.extend([addr.strip() for addr in bcc.split(",")])

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipients, msg.as_string())
        return {"status": "success", "to": to, "subject": subject}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def main():
    if len(sys.argv) < 4:
        print(json.dumps({"error": "Usage: send_email.py <to> <subject> <body> [from_name] [cc] [bcc] [attachment]"}))
        sys.exit(1)

    to = sys.argv[1]
    subject = sys.argv[2]
    body = sys.argv[3]
    from_name = sys.argv[4] if len(sys.argv) > 4 else "Buddy Agent"
    cc = sys.argv[5] if len(sys.argv) > 5 else ""
    bcc = sys.argv[6] if len(sys.argv) > 6 else ""
    attachment = sys.argv[7] if len(sys.argv) > 7 else ""

    result = send_via_smtp(to, subject, body, from_name, cc, bcc, attachment)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
