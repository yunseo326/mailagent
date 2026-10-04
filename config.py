"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_STATUS_FILE = r"C:\Users\SAMSUNG\2trading\logs\daily_update\latest_status.md"


class ConfigurationError(ValueError):
    """Raised when a required environment variable is missing or invalid."""


def _load_env_file(path: Path = Path(".env")) -> None:
    """Load a small, predictable subset of dotenv syntax without dependencies."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if value[:1] == value[-1:] and value.startswith(("'", '"')):
            value = value[1:-1]
        if name:
            os.environ.setdefault(name, value)


@dataclass(frozen=True)
class Config:
    naver_works_email: str
    naver_works_app_password: str
    naver_mail_email: str | None = None
    naver_mail_app_password: str | None = None
    imap_host: str = "imap.worksmobile.com"
    imap_port: int = 993
    naver_mail_imap_host: str = "imap.naver.com"
    naver_mail_imap_port: int = 993
    naver_mail_smtp_host: str = "smtp.naver.com"
    naver_mail_smtp_port: int = 587
    summary_recipient: str | None = None
    summary_status_file: str = DEFAULT_STATUS_FILE

    @classmethod
    def from_env(cls) -> "Config":
        _load_env_file()

        values = {
            "NAVER_WORKS_EMAIL": os.getenv("NAVER_WORKS_EMAIL", "").strip(),
            "NAVER_WORKS_APP_PASSWORD": os.getenv(
                "NAVER_WORKS_APP_PASSWORD", ""
            ).strip(),
            "NAVER_MAIL_EMAIL": os.getenv("NAVER_MAIL_EMAIL", "").strip(),
            "NAVER_MAIL_APP_PASSWORD": os.getenv(
                "NAVER_MAIL_APP_PASSWORD", ""
            ).strip(),
            "SUMMARY_RECIPIENT": os.getenv("SUMMARY_RECIPIENT", "").strip(),
        }
        required_names = ["NAVER_WORKS_EMAIL", "NAVER_WORKS_APP_PASSWORD"]
        missing = [name for name in required_names if not values[name]]
        if missing:
            raise ConfigurationError(
                ".env에 다음 필수 항목을 설정하세요: " + ", ".join(missing)
            )

        naver_mail_values = (
            values["NAVER_MAIL_EMAIL"],
            values["NAVER_MAIL_APP_PASSWORD"],
        )
        if any(naver_mail_values) and not all(naver_mail_values):
            raise ConfigurationError(
                "개인 네이버 메일을 사용하려면 NAVER_MAIL_EMAIL과 "
                "NAVER_MAIL_APP_PASSWORD를 모두 설정하세요."
            )

        try:
            imap_port = int(os.getenv("NAVER_WORKS_IMAP_PORT", "993"))
            naver_mail_imap_port = int(os.getenv("NAVER_MAIL_IMAP_PORT", "993"))
            naver_mail_smtp_port = int(os.getenv("NAVER_MAIL_SMTP_PORT", "587"))
        except ValueError as exc:
            raise ConfigurationError("포트 번호는 정수여야 합니다.") from exc

        return cls(
            naver_works_email=values["NAVER_WORKS_EMAIL"],
            naver_works_app_password=values["NAVER_WORKS_APP_PASSWORD"],
            naver_mail_email=values["NAVER_MAIL_EMAIL"] or None,
            naver_mail_app_password=values["NAVER_MAIL_APP_PASSWORD"] or None,
            imap_host=os.getenv("NAVER_WORKS_IMAP_HOST", "imap.worksmobile.com"),
            imap_port=imap_port,
            naver_mail_imap_host=os.getenv(
                "NAVER_MAIL_IMAP_HOST", "imap.naver.com"
            ),
            naver_mail_imap_port=naver_mail_imap_port,
            naver_mail_smtp_host=os.getenv(
                "NAVER_MAIL_SMTP_HOST", "smtp.naver.com"
            ),
            naver_mail_smtp_port=naver_mail_smtp_port,
            summary_recipient=values["SUMMARY_RECIPIENT"] or None,
            summary_status_file=os.getenv(
                "SUMMARY_STATUS_FILE", DEFAULT_STATUS_FILE
            ).strip(),
        )
