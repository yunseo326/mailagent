"""NAVER WORKS and NAVER Mail daily digest command-line entry point."""

from __future__ import annotations

import argparse
import imaplib
import logging
import re
import smtplib
import sys
from pathlib import Path

from classifier import ProcessedMail, preprocess_mails
from config import Config, ConfigurationError
from mail_reader import ImapMailReader
from mail_sender import append_status_file, send_summary
from summary_builder import build_summary, default_summary_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="최근 네이버 계열 메일을 분류하고 요약")
    parser.add_argument(
        "--test-login", action="store_true", help="설정된 모든 메일 계정 로그인 테스트"
    )
    parser.add_argument("--output", type=Path, help="요약 Markdown 파일 경로")
    parser.add_argument("--stdout", action="store_true", help="요약 내용을 콘솔에도 출력")
    parser.add_argument(
        "--send", action="store_true", help="생성한 요약을 설정된 Gmail 주소로 전송"
    )
    return parser.parse_args()


def _safe_subject(
    subject: str, limit: int = 100, redact_auth_codes: bool = False
) -> str:
    one_line = " ".join(subject.split())
    if redact_auth_codes:
        one_line = re.sub(
            r"(?<!\d)\[?\d{4,8}\]?(?!\d)", "[인증번호 숨김]", one_line
        )
    return one_line if len(one_line) <= limit else one_line[:limit].rstrip() + "…"


def log_preprocessing_report(processed: list[ProcessedMail]) -> None:
    included = [item for item in processed if not item.excluded]
    excluded = [item for item in processed if item.excluded]
    logging.info(
        "전처리 결과: 총 수집 %d건, 제외 %d건, 포함 %d건",
        len(processed),
        len(excluded),
        len(included),
    )

    tagged_examples = [item for item in included if item.tags][:5]
    if tagged_examples:
        logging.info("적용된 태그 예시:")
        for item in tagged_examples:
            logging.info(
                "  - [%s] %s -> %s",
                item.mail.source,
                _safe_subject(item.mail.subject),
                ", ".join(item.tags),
            )
    else:
        logging.info("적용된 태그 예시: 없음")

    routine_examples = [
        item
        for item in excluded
        if item.exclusion_reason and item.exclusion_reason.startswith("routine_")
    ][:5]
    if routine_examples:
        logging.info("제외된 routine auth/integration notification 예시:")
        for item in routine_examples:
            logging.info(
                "  - [%s] %s -> %s",
                item.mail.source,
                _safe_subject(item.mail.subject, redact_auth_codes=True),
                item.exclusion_reason,
            )
    else:
        logging.info("제외된 routine auth/integration notification 예시: 없음")


def run() -> int:
    args = parse_args()
    try:
        config = Config.from_env()
        readers = [
            ImapMailReader(
                config.imap_host,
                config.imap_port,
                config.naver_works_email,
                config.naver_works_app_password,
                "NAVER WORKS",
            )
        ]
        if config.naver_mail_email and config.naver_mail_app_password:
            readers.append(
                ImapMailReader(
                    config.naver_mail_imap_host,
                    config.naver_mail_imap_port,
                    config.naver_mail_email,
                    config.naver_mail_app_password,
                    "네이버 메일",
                )
            )

        if args.test_login:
            for reader in readers:
                logging.info("%s 로그인을 테스트합니다.", reader.source)
                reader.test_login()
                logging.info("%s 로그인에 성공했습니다.", reader.source)
            return 0

        mails = []
        for reader in readers:
            logging.info("%s의 최근 24시간 메일을 조회합니다.", reader.source)
            mails.extend(reader.fetch_recent(hours=24))
        mails.sort(key=lambda mail: mail.received_at, reverse=True)
        processed = preprocess_mails(mails)
        log_preprocessing_report(processed)

        summary = build_summary(processed)
        summary = append_status_file(summary, config.summary_status_file)
        output_path = args.output or default_summary_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(summary, encoding="utf-8")
        logging.info("일일 요약을 %s 파일에 저장했습니다.", output_path.resolve())
        if args.send:
            if not config.naver_mail_email or not config.naver_mail_app_password:
                raise ConfigurationError(
                    "요약 발송에는 NAVER_MAIL_EMAIL과 "
                    "NAVER_MAIL_APP_PASSWORD가 필요합니다."
                )
            if not config.summary_recipient:
                raise ConfigurationError("SUMMARY_RECIPIENT를 설정하세요.")
            send_summary(
                summary,
                config.naver_mail_email,
                config.summary_recipient,
                config.naver_mail_app_password,
                config.naver_mail_smtp_host,
                config.naver_mail_smtp_port,
            )
            logging.info("Gmail 수신 주소로 요약 메일을 전송했습니다.")
        if args.stdout:
            print(summary)
        return 0
    except ConfigurationError as exc:
        logging.error("설정 오류: %s", exc)
    except imaplib.IMAP4.error:
        logging.error(
            "메일 계정 로그인 또는 IMAP 처리에 실패했습니다. "
            "직전 로그에 표시된 계정의 주소, IMAP 설정, 앱 비밀번호를 확인하세요."
        )
    except smtplib.SMTPAuthenticationError:
        logging.error(
            "네이버 SMTP 인증에 실패했습니다. 개인 네이버 메일 주소와 "
            "애플리케이션 비밀번호를 확인하세요."
        )
    except smtplib.SMTPException as exc:
        logging.error("요약 메일 전송 중 SMTP 오류가 발생했습니다: %s", exc)
    except OSError as exc:
        logging.error("메일 서버 통신 중 오류가 발생했습니다: %s", exc)
    except Exception as exc:
        logging.exception("예상하지 못한 오류가 발생했습니다: %s", exc)
    return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
    )
    sys.exit(run())
