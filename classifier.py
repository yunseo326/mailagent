"""Lightweight tagging and conservative noise filtering.

This module deliberately does not decide whether a message is important.  It
adds descriptive tags and removes only clear routine/promotional noise.  Final
personal prioritization belongs to ChatGPT.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from email.utils import parseaddr

from mail_reader import ReceivedMail


TAG_RULES: dict[str, tuple[str, ...]] = {
    "school": ("학교 공지", "공지사항", "학사", "수강", "대학", "교내"),
    "scholarship": ("장학금", "장학생"),
    "opportunity": ("대회", "공모전", "대외활동", "모집", "선발"),
    "career": ("인턴", "인턴십", "취업", "채용"),
    "semiconductor": ("반도체",),
    "data": ("데이터분석", "데이터 분석", "data analysis"),
    "robotics": ("로봇", "robotics"),
    "education": ("교육", "강의", "세미나", "워크숍", "webinar"),
    "deadline": ("마감", "제출", "deadline", "due date"),
    "result": ("합격", "선발 결과", "결과 발표"),
    "newsletter": ("뉴스레터", "newsletter", "weekly digest", "daily briefing"),
    "promotion": ("광고", "프로모션", "할인", "특가", "쿠폰", "세일"),
    "onboarding": ("온보딩", "welcome to", "시작하기", "가입을 환영"),
    "auth": ("인증번호", "인증 코드", "verification code", "otp", "일회용 비밀번호"),
    "integration": ("앱 연동", "외부 앱", "connected app", "접근 권한 승인"),
}

SECURITY_RISK_PATTERNS = (
    r"의심스러운\s*(?:로그인|활동|접속)",
    r"비정상(?:적인)?\s*(?:로그인|활동|접속)",
    r"알\s*수\s*없는\s*(?:로그인|기기|접속)",
    r"새로운\s*기기(?:에서)?\s*(?:로그인|접속)",
    r"해외\s*(?:로그인|접속)",
    r"로그인\s*시도(?:가)?\s*차단",
    r"계정\s*(?:탈취|도용)",
    r"비밀번호(?:가)?\s*(?:변경|재설정)(?:되었|됐)",
    r"2단계\s*인증.*(?:해제|변경)",
    r"보안\s*설정.*(?:변경|해제)",
    r"복구\s*(?:이메일|전화번호).*변경",
    r"suspicious\s+(?:sign[ -]?in|login|activity)",
    r"unrecognized\s+(?:sign[ -]?in|login|device)",
    r"unauthorized\s+(?:access|login|change)",
    r"password\s+(?:was\s+)?(?:changed|reset)",
    r"two-factor authentication\s+(?:disabled|changed)",
    r"account\s+(?:takeover|compromised)",
)

ROUTINE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "routine_auth_code",
        ("인증번호", "인증 코드", "verification code", "otp", "일회용 비밀번호"),
    ),
    (
        "routine_integration",
        (
            "앱 연동 승인",
            "외부 앱 승인",
            "연동이 승인",
            "connected app authorized",
            "접근 권한이 승인",
        ),
    ),
    (
        "routine_2fa",
        (
            "2단계 인증 설정",
            "2단계 인증이 설정",
            "2단계 인증 활성화",
            "two-factor authentication enabled",
            "2fa enabled",
        ),
    ),
    (
        "routine_app_password",
        (
            "앱 비밀번호 생성",
            "앱 비밀번호가 생성",
            "애플리케이션 비밀번호 생성",
            "애플리케이션 비밀번호가 생성",
            "app password created",
            "app password generated",
        ),
    ),
    (
        "routine_onboarding",
        ("온보딩", "가입을 환영", "welcome to", "계정 설정을 시작"),
    ),
)

PROMOTION_MARKERS = ("[광고]", "(광고)", "advertisement")
PROMOTION_SIGNALS = (
    "광고",
    "할인",
    "특가",
    "쿠폰",
    "프로모션",
    "세일",
    "무료 체험",
    "지금 구매",
    "수신거부",
    "unsubscribe",
)


@dataclass(frozen=True)
class ProcessedMail:
    mail: ReceivedMail
    tags: tuple[str, ...]
    excluded: bool = False
    exclusion_reason: str | None = None


def _normalized_text(mail: ReceivedMail) -> str:
    return f"{mail.subject}\n{mail.body}".casefold()


def _has_security_risk(text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in SECURITY_RISK_PATTERNS)


def _tags_for(text: str) -> tuple[str, ...]:
    tags = [
        tag
        for tag, keywords in TAG_RULES.items()
        if any(keyword.casefold() in text for keyword in keywords)
    ]
    if re.search(r"(?<![a-z])ai(?![a-z])", text, re.IGNORECASE):
        tags.append("ai")
    if _has_security_risk(text):
        tags.append("security")
    return tuple(dict.fromkeys(tags))


def tag_mail(mail: ReceivedMail) -> ProcessedMail:
    text = _normalized_text(mail)
    subject = mail.subject.casefold().strip()
    tags = _tags_for(text)

    # A credible security warning is always retained for ChatGPT to evaluate.
    if "security" in tags:
        return ProcessedMail(mail=mail, tags=tags)

    for reason, phrases in ROUTINE_RULES:
        if any(phrase.casefold() in subject for phrase in phrases):
            return ProcessedMail(mail=mail, tags=tags, excluded=True, exclusion_reason=reason)

    promotion_signal_count = sum(
        signal.casefold() in text for signal in PROMOTION_SIGNALS
    )
    if any(marker.casefold() in subject for marker in PROMOTION_MARKERS) or promotion_signal_count >= 2:
        return ProcessedMail(
            mail=mail,
            tags=tags,
            excluded=True,
            exclusion_reason="obvious_promotion",
        )

    # Ambiguous mail remains in the digest, even when it has no tags.
    return ProcessedMail(mail=mail, tags=tags)


def _duplicate_key(mail: ReceivedMail) -> str:
    sender_address = parseaddr(mail.sender)[1].casefold().strip()
    subject = " ".join(mail.subject.casefold().split())
    body = " ".join(mail.body.casefold().split())
    payload = "\0".join((sender_address, subject, body))
    return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()


def preprocess_mails(mails: list[ReceivedMail]) -> list[ProcessedMail]:
    processed: list[ProcessedMail] = []
    seen: set[str] = set()
    for mail in mails:
        item = tag_mail(mail)
        duplicate_key = _duplicate_key(mail)
        if duplicate_key in seen:
            duplicate_tags = tuple(dict.fromkeys((*item.tags, "duplicate")))
            item = replace(
                item,
                tags=duplicate_tags,
                excluded=True,
                exclusion_reason="duplicate",
            )
        else:
            seen.add(duplicate_key)
        processed.append(item)
    return processed
