"""Build a compact digest for ChatGPT's final prioritization."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from classifier import ProcessedMail


SEOUL = timezone(timedelta(hours=9), name="KST")


def _preview(body: str, limit: int = 500) -> str:
    compact = " ".join(body.split())
    return compact if len(compact) <= limit else compact[:limit].rstrip() + "…"


def default_summary_path(now: datetime | None = None) -> Path:
    current = now or datetime.now(SEOUL)
    return Path("summaries") / f"naver-mail-digest-{current:%Y-%m-%d}.md"


def build_summary(processed: list[ProcessedMail]) -> str:
    included = [item for item in processed if not item.excluded]
    excluded_count = len(processed) - len(included)
    now = datetime.now(SEOUL)

    lines = [
        f"# NAVER / NAVER WORKS 메일 digest — {now:%Y-%m-%d}",
        "",
        f"생성 시각: {now:%Y-%m-%d %H:%M} KST",
        "",
        f"- 총 수집: {len(processed)}건",
        f"- 포함: {len(included)}건",
        f"- 명백한 noise 제외: {excluded_count}건",
        "",
        "> 아래 태그는 가벼운 주제 표식이며 중요도 판정이 아닙니다. 최종 판단은 ChatGPT가 수행합니다.",
        "",
    ]
    if not included:
        lines.append("ChatGPT가 검토할 메일이 없습니다.")
        return "\n".join(lines) + "\n"

    for index, item in enumerate(included, 1):
        tags = ", ".join(item.tags) or "untagged"
        lines.extend(
            [
                f"## {index}. {item.mail.subject}",
                "",
                f"- 발신자: {item.mail.sender}",
                f"- 계정: {item.mail.source}",
                f"- 수신: {item.mail.received_at.astimezone(SEOUL):%Y-%m-%d %H:%M} KST",
                f"- 태그: {tags}",
                "",
                _preview(item.mail.body) or "(본문 없음)",
                "",
            ]
        )
    return "\n".join(lines) + "\n"
