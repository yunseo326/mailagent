"""Read recent messages from NAVER WORKS through IMAP over SSL."""

from __future__ import annotations

import imaplib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email import message_from_bytes, policy
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser


_MONTH_ABBR = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


class _TextHTMLParser(HTMLParser):
    _BLOCK_TAGS = {
        "br",
        "p",
        "div",
        "li",
        "tr",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fragments: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in self._BLOCK_TAGS:
            self.fragments.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1
        elif not self._ignored_depth and tag in self._BLOCK_TAGS:
            self.fragments.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.fragments.append(data)


@dataclass(frozen=True)
class ReceivedMail:
    sender: str
    subject: str
    body: str
    received_at: datetime
    source: str = "NAVER WORKS"


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except (LookupError, UnicodeDecodeError):
        return value


def _decode_payload(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        raw = part.get_payload()
        return raw if isinstance(raw, str) else ""

    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _html_to_text(source: str) -> str:
    parser = _TextHTMLParser()
    parser.feed(source)
    text = "".join(parser.fragments)
    lines = (" ".join(line.split()) for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def extract_text(message: Message) -> str:
    """Prefer a text/plain body, falling back to converted HTML."""
    plain_parts: list[str] = []
    html_parts: list[str] = []

    parts = message.walk() if message.is_multipart() else [message]
    for part in parts:
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue
        content_type = part.get_content_type()
        if content_type == "text/plain":
            plain_parts.append(_decode_payload(part))
        elif content_type == "text/html":
            html_parts.append(_html_to_text(_decode_payload(part)))

    body = "\n".join(plain_parts).strip() or "\n".join(html_parts).strip()
    return re.sub(r"\n{3,}", "\n\n", body)


def _message_datetime(message: Message, metadata: bytes) -> datetime | None:
    # IMAP INTERNALDATE is the server-side receipt time and is preferred.
    match = re.search(rb'INTERNALDATE "([^"]+)"', metadata)
    if match:
        try:
            value = match.group(1).decode("ascii")
            return datetime.strptime(value, "%d-%b-%Y %H:%M:%S %z")
        except (UnicodeDecodeError, ValueError):
            pass

    try:
        parsed = parsedate_to_datetime(message.get("Date", ""))
        if parsed is None:
            return None
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except (TypeError, ValueError, OverflowError):
        return None


class ImapMailReader:
    def __init__(
        self,
        host: str,
        port: int,
        email: str,
        app_password: str,
        source: str = "NAVER WORKS",
    ):
        self.host = host
        self.port = port
        self.email = email
        self._app_password = app_password
        self.source = source

    def _connect(self) -> imaplib.IMAP4_SSL:
        client = imaplib.IMAP4_SSL(self.host, self.port)
        try:
            client.login(self.email, self._app_password)
        except Exception:
            try:
                client.logout()
            except Exception:
                pass
            raise
        return client

    def test_login(self) -> None:
        client = self._connect()
        client.logout()

    def fetch_recent(self, hours: int = 24) -> list[ReceivedMail]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        client = self._connect()
        try:
            status, _ = client.select("INBOX", readonly=True)
            if status != "OK":
                raise RuntimeError("NAVER WORKS 받은편지함을 열 수 없습니다.")

            # SINCE works at day precision, so exact 24-hour filtering happens below.
            since = f"{cutoff.day:02d}-{_MONTH_ABBR[cutoff.month - 1]}-{cutoff.year}"
            status, data = client.search(None, "SINCE", since)
            if status != "OK":
                raise RuntimeError("NAVER WORKS 메일 검색에 실패했습니다.")

            messages: list[ReceivedMail] = []
            for message_id in data[0].split():
                status, fetched = client.fetch(message_id, "(INTERNALDATE RFC822)")
                if status != "OK":
                    continue
                item = next((x for x in fetched if isinstance(x, tuple)), None)
                if not item or len(item) < 2:
                    continue
                metadata, raw_message = item[0], item[1]
                message = message_from_bytes(raw_message, policy=policy.default)
                received_at = _message_datetime(message, metadata)
                if received_at is None or received_at.astimezone(timezone.utc) < cutoff:
                    continue
                messages.append(
                    ReceivedMail(
                        sender=_decode_header(message.get("From")) or "발신자 없음",
                        subject=_decode_header(message.get("Subject")) or "제목 없음",
                        body=extract_text(message),
                        received_at=received_at,
                        source=self.source,
                    )
                )
            return sorted(messages, key=lambda item: item.received_at, reverse=True)
        finally:
            try:
                client.logout()
            except Exception:
                pass


# 기존 코드에서 사용하던 이름과의 호환성을 유지합니다.
NaverWorksMailReader = ImapMailReader
