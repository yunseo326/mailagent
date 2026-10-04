# AGENTS.md

## Project Goal

Build a local Python mail preprocessing agent for NAVER and NAVER WORKS.

The Python agent should:
- fetch recent mail
- extract readable text
- apply lightweight tags
- remove only clearly useless system/promotional noise
- generate a compact digest

The Python agent must NOT make the final personalized importance decision.

Final prioritization is performed by ChatGPT together with the directly connected Gmail account.

---

## System Architecture

```text
Gmail
  └─ Read directly by ChatGPT Gmail integration

NAVER / NAVER WORKS
  └─ Local Python mail-agent
       ├─ fetch recent mail
       ├─ extract body text
       ├─ lightweight tagging
       ├─ remove obvious noise
       └─ generate daily digest
              ↓
            Gmail
              ↓
          ChatGPT
              ↓
      final daily briefing