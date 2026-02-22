# app/mailer/smtp_client.py
from __future__ import annotations

import os
import smtplib
import mimetypes
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Optional


def send_email_smtp(
    cfg: Dict[str, Any],
    *,
    to_emails: List[str],
    subject: str,
    body: str,
    attachments: Optional[List[str]] = None,  
) -> None:
    smtp_cfg = cfg["smtp"]

    user_env = smtp_cfg.get("username_env", "GMAIL_USER")
    pass_env = smtp_cfg.get("password_env", "GMAIL_APP_PASSWORD")

    user = os.environ.get(user_env, "").strip()
    pwd = os.environ.get(pass_env, "").strip()
    if not user or not pwd:
        raise RuntimeError(f"Missing env vars: {user_env} / {pass_env}")

    host = smtp_cfg.get("host", "smtp.gmail.com")
    port = int(smtp_cfg.get("port", 587))
    use_starttls = bool(smtp_cfg.get("use_starttls", True))

    sender_name = str(smtp_cfg.get("sender_name", "TempleManager")).strip()
    from_addr = f"{sender_name} <{user}>"

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    msg.set_content(body)

    # ✅ 附件
    for file_path in (attachments or []):
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"Attachment not found: {p}")

        data = p.read_bytes()

        # CSV 常見 mime：text/csv
        ctype, encoding = mimetypes.guess_type(str(p))
        if not ctype:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)

        msg.add_attachment(
            data,
            maintype=maintype,
            subtype=subtype,
            filename=p.name,
        )

    if use_starttls:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user, pwd)
            server.send_message(msg)
    else:
        with smtplib.SMTP_SSL(host, port, timeout=30) as server:
            server.login(user, pwd)
            server.send_message(msg)