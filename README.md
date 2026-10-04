# NAVER / NAVER WORKS 메일 전처리 시스템

최근 24시간 동안 NAVER WORKS와 개인 네이버 메일 받은편지함에 도착한 메일을 읽고, 가벼운 설명 태그를 붙여 하나의 Markdown digest를 생성하는 Windows용 Python 프로젝트입니다. 개인 네이버 메일 연결은 선택 사항입니다.

Python은 개인화된 중요도를 결정하지 않습니다. 애매한 메일은 digest에 남겨두며, 최종 우선순위는 Gmail과 이 digest를 함께 보는 ChatGPT가 판단합니다.

Gmail은 ChatGPT의 기존 Gmail 연결이 직접 읽습니다. 이 프로그램은 Gmail 서버에 로그인하거나 Gmail을 읽지 않습니다. 생성한 요약은 개인 네이버 메일 SMTP를 통해 지정한 Gmail 주소로 보낼 수 있으므로 Google 계정 비밀번호나 앱 비밀번호가 필요하지 않습니다. OpenAI API도 사용하지 않습니다.

## 준비 사항

- Windows 10/11
- Python 3.11 이상
- IMAP 사용이 허용된 NAVER WORKS 계정
- NAVER WORKS 외부 앱 비밀번호
- 개인 네이버 메일 계정 및 애플리케이션 비밀번호(선택 사항)

외부 Python 패키지 없이 표준 라이브러리만 사용합니다. 실제 비밀번호는 코드가 아닌 `.env`에서만 읽으며 `.env`는 Git에서 제외됩니다.

## 설치

PowerShell에서 프로젝트 폴더로 이동해 실행합니다.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

이미 `.env`가 있다면 복사 명령은 실행하지 마세요.

## 환경 설정

`.env`에 NAVER WORKS 정보만 입력합니다.

```dotenv
NAVER_WORKS_EMAIL=your-account@example.com
NAVER_WORKS_APP_PASSWORD=your-naver-works-app-password
NAVER_WORKS_IMAP_HOST=imap.worksmobile.com
NAVER_WORKS_IMAP_PORT=993

# 개인 네이버 메일을 함께 처리할 때만 입력
NAVER_MAIL_EMAIL=your-id@naver.com
NAVER_MAIL_APP_PASSWORD=your-naver-mail-app-password
NAVER_MAIL_IMAP_HOST=imap.naver.com
NAVER_MAIL_IMAP_PORT=993
NAVER_MAIL_SMTP_HOST=smtp.naver.com
NAVER_MAIL_SMTP_PORT=587

# Gmail 수신에는 비밀번호가 필요하지 않음
SUMMARY_RECIPIENT=your-address@gmail.com
```

일반 로그인 비밀번호가 아니라 각 서비스에서 발급한 외부 앱/애플리케이션 비밀번호를 사용하세요. NAVER WORKS에서 IMAP 또는 외부 앱 접근이 차단돼 있다면 조직 관리자의 허용이 필요할 수 있습니다.

개인 네이버 메일은 네이버 메일의 `환경설정 > POP3/IMAP 설정 > IMAP/SMTP 설정`에서 IMAP 사용을 먼저 켜야 합니다. 개인 네이버 메일을 사용하지 않으려면 `NAVER_MAIL_...` 항목을 비워두면 됩니다.

## 실행

로그인만 확인합니다.

```powershell
python main.py --test-login
```

연결된 계정들의 최근 24시간 메일을 합쳐 처리하고 `summaries/naver-mail-digest-YYYY-MM-DD.md`를 생성합니다. 각 메일에는 출처 계정과 적용된 태그가 표시됩니다.

```powershell
python main.py
```

요약을 콘솔에서도 함께 확인하려면 다음과 같이 실행합니다.

```powershell
python main.py --stdout
```

저장 위치를 직접 지정할 수도 있습니다.

```powershell
python main.py --output my-summary.md
```

요약 파일을 만든 뒤 개인 네이버 메일 SMTP로 Gmail 수신 주소에 전송합니다.

```powershell
python main.py --send
```

위 명령으로 Gmail에서 요약을 수신하면 ChatGPT의 Gmail 연결로 확인할 수 있습니다. 이 옵션도 로컬 Markdown 파일을 함께 저장합니다.

실행할 때마다 `C:\Users\SAMSUNG\2trading\logs\daily_update\latest_status.md`를 UTF-8로 읽어 **로컬 상태 보고서** 구역에 전체 내용을 포함합니다. 저장되는 요약 파일과 메일 본문 모두에 포함되며, 예약 실행에도 적용됩니다. 파일이 없거나 읽을 수 없거나 비어 있으면 본문에 안내를 넣고 로그에 경고를 남긴 뒤 메일 요약 처리를 계속합니다.

경로를 바꾸려면 `.env`에 `SUMMARY_STATUS_FILE=C:\다른폴더\상태.md`를 설정하세요. `SUMMARY_STATUS_FILE=`로 비워두면 상태 보고서를 포함하지 않습니다.

## 태그 및 제외 기준

- `school`, `scholarship`, `opportunity`, `career`, `ai`, `semiconductor`, `data`, `robotics`, `education`, `deadline`, `result`, `newsletter`, `promotion` 등의 설명 태그를 붙입니다.
- 태그는 최종 중요도 판정이 아닙니다. 예를 들어 뉴스레터에 `AI`가 한 번 등장하면 `newsletter`, `ai` 태그가 붙을 수 있지만 중요 메일로 승격되지는 않습니다.
- 애매하거나 태그가 없는 메일도 digest에 포함합니다.
- 명백한 광고, 동일 메일 중복, 온보딩, 인증번호, 앱 연동 승인, 2단계 인증 설정, 앱 비밀번호 생성 같은 routine 알림만 제외합니다.
- 의심스러운 로그인, 알 수 없는 기기, 예상하지 못한 비밀번호·보안 설정 변경 등은 `security` 태그를 붙이고 제외하지 않습니다.

제외된 메일은 digest 본문에 넣지 않고 개수만 표시합니다. 규칙과 태그는 `classifier.py`에서 조정할 수 있습니다.

## 파일 구성

- `main.py`: 실행 흐름, 요약 저장, 오류 처리
- `config.py`: `.env` 설정 로드 및 검증
- `mail_reader.py`: IMAP 로그인, 최근 메일 조회, 본문 추출
- `classifier.py`: lightweight 태깅 및 보수적인 noise 제외
- `summary_builder.py`: Markdown 일일 요약 생성
- `mail_sender.py`: 개인 네이버 SMTP를 통한 Gmail 수신 주소 발송

## 보안

- `.env`를 Git에 커밋하거나 공유하지 마세요.
- 외부 앱 비밀번호를 코드, 로그, 화면 캡처에 넣지 마세요.
- 비밀번호가 노출되면 즉시 폐기하고 새로 발급하세요.

## Windows 예약 실행

`run_daily.ps1`은 프로젝트 가상환경으로 `main.py --send`를 실행하고 결과를 `logs/daily-run.log`에 기록합니다. Windows 작업 스케줄러의 `NAVER Mail Daily Digest` 작업이 매일 오전 7시 30분에 이 스크립트를 실행합니다.

Gmail로 보내지 않고 예약 실행 경로만 점검하려면 다음 명령을 사용할 수 있습니다.

```powershell
.\run_daily.ps1 -NoSend
```
