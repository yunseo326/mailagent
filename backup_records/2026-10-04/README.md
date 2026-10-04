# Backup and recovery record — 2026-10-04

Repository: yunseo326/mailagent

Branch: `backup/2026-10-04`

Selected source files: 12

## Restore

Python 3.11+ standard-library NAVER/NAVER WORKS mail preprocessor. Copy .env.example to a new .env and configure fresh NAVER_WORKS_APP_PASSWORD and optional NAVER_MAIL_APP_PASSWORD. Re-enter account/recipient addresses. Old credentials, 22 mail summaries, runtime logs, and virtual environment are intentionally absent. Recreate any scheduler manually after reviewing run_daily.ps1. No mail was fetched or sent during backup.

## Verification and limits

Files were read without executing project code. Selected text and extracted Office/PDF text were checked using Gitleaks v8.30.1, known credential-value matching, and suspicious-code patterns. Findings in experiment comparison/input hashes were reviewed as non-credentials. Binary files listed in summary.json were not covered by text secret scanning. No whole-computer malware clearance or full-history audit is claimed.

`manifest.json` records exact source and uploaded SHA-256 plus Git blob IDs. `exclusions.csv` records excluded paths/reasons; directory entries represent excluded subtrees and are not file counts. Existing remote files outside selected scope may be inherited, but no local unpushed history is added. No raw secrets are recorded here.

This record describes a selected GitHub archive, not a USB or retained local backup. Original source folders are unchanged.
