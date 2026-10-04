"""Send the generated digest through personal NAVER Mail SMTP."""

from __future__ import annotations

import smtplib
import logging
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path


SEOUL = timezone(timedelta(hours=9), name="KST")


def append_status_file(summary: str, file_path: str) -> str:
    """Include the current local report verbatim, with a visible failure notice."""
    if not file_path:
        return summary
    path = Path(file_path)
    try:
        content = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        logging.warning("추가 상태 파일을 읽지 못했습니다 (%s): %s", path, exc)
        content = "[상태 파일을 읽지 못해 내용이 포함되지 않았습니다.]"
    else:
        if not content.strip():
            logging.warning("추가 상태 파일이 비어 있습니다: %s", path)
            content = "[상태 파일이 비어 있습니다.]"
    return summary.rstrip() + "\n\n---\n\n## 로컬 상태 보고서\n\n" + content + "\n"


def build_message(summary: str, sender: str, recipient: str) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = f"[NAVER 메일 요약] {datetime.now(SEOUL):%Y-%m-%d}"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(summary)
    return message


def send_summary(
    summary: str,
    sender: str,
    recipient: str,
    app_password: str,
    host: str = "smtp.naver.com",
    port: int = 587,
) -> None:
    message = build_message(summary, sender, recipient)
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(sender, app_password)
        smtp.send_message(message)
