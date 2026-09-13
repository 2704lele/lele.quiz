# LeLe Chinese Quiz Automation — Claude Code Guide

## Project Overview
Automated end-to-end Chinese quiz video production pipeline (1080x1920 @ 60fps vertical short-form videos):
- **Master Database**: Google Sheets (`1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0`)
- **4 Quiz Domains**:
  1. `pinyinquiz`: Pinyin tone and phonetic recognition (HSK 1-6).
  2. `vocabCNquiz`: Hanzi to Vietnamese meaning.
  3. `vocabVNquiz`: Reverse lookup (Vietnamese meaning to Hanzi).
  4. `multilevelsquiz`: 1 core word across 5 HSK levels (HSK 1-5).
- **Rendering Engine**: Manim CE + Edge-TTS audio generation + Gatekeeper QC.
- **Distribution**: Google Drive canonical storage + Buffer social publishing.

---

## Quick Commands Reference

### Environment Setup
```bash
source env.sh
pip install -r pinyinquiz/requirements.txt rich pytest
```

### Ideation & Content Generation (Gemini AI)
```bash
./quick_idea.sh [tab] [count]
# Example: ./quick_idea.sh pinyin 3
# Direct CLI: python3 scripts/run_ideation_dispatcher.py --tab pinyin --count 1
```

### Rendering & Quality Control
```bash
./quick_render.sh [tab] [row_id] [quality]
# Example (All pending): ./quick_render.sh all
# Example (Specific row): ./quick_render.sh pinyin 54 qh
# Direct CLI: python3 scripts/run_render_dispatcher.py --tab pinyin --row 54 --quality qh
```

### Social Publishing (Buffer API)
```bash
./quick_publish.sh [tab] [row_id] [channels]
# Example: ./quick_publish.sh pinyin 2 buffer1
# Direct CLI: python3 scripts/publish_social_batch.py --tab pinyin --id 2 --channels buffer1
```

### Auditing & Invariant Maintenance
```bash
# Morning gatekeeper audit & reconciliation
python3 scripts/run_morning_audit.py

# Enforce strictly 21px row height across all 4 tabs
python3 scripts/enforce_row_height_21px.py

# Run unit and integration tests
pytest tests/ -v
```

---

## Critical System Invariants & Contracts

1. **Google Sheets State Machine**:
   - **Tab names**: `pinyin`, `vocabCN`, `vocabVN`, `multilevels`
   - **Column A (idx 0)**: `ID` (e.g. `#54`, `#40`, `#33`, `#34`)
   - **Column D (idx 3)**: `Status` (`Pending` -> `Rendering` -> `Video` -> `Ready` -> `Published`)
   - **Column K (idx 10)**: `Drive Link` (Strict format: `https://drive.google.com/file/d/{FILE_ID}/view?usp=drivesdk`)
   - **Column P (idx 15)**: `Notes` (QC metadata, timestamps)
   - **Row Height Invariant**: Strictly `21px` across all rows in all 4 tabs (`scripts/enforce_row_height_21px.py`).

2. **Google Drive Storage Invariant**:
   - **Root Folder**: `Quiz` (`1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB`)
   - **Strictly 5 Canonical Subfolders**:
     - `00.codebases` (`1C-n3Un-D6Teu4LapgIWWeVZ6l7toH8lm`)
     - `01.pinyinquiz` (`1f2mFUgpz_pYn3y9HqeHyOG9DzPMVH9QY`)
     - `02.vocabCNquiz` (`1eI7I4jQqGBjD7MC_NXJ4zwFANxrcZM1E`)
     - `03.vocabVNquiz` (`1VPqs9h4LLmmmXWKDGWoAz1fUCylVLK2H`)
     - `04.multilevelsquiz` (`17xOkiW-XOWRDK2CCwNEl_rlf1rGKqKXm`)
   - Exactly 0 orphan/loose files in root.

3. **Zero-Leak Vault Policy**:
   - Never log API keys, Bearer tokens, Telegram bot tokens, or Google service account credentials.
   - Do not commit `.env`, `configs/*.json`, or `service_account.json`.

---

## Code Architecture & Style Conventions

- **Python Version**: Python 3.10+
- **Bytecode**: Always include `sys.dont_write_bytecode = True` and `os.environ["PYTHONDONTWRITEBYTECODE"] = "1"` at script entrypoints.
- **Root Resolution**: Use `QUIZ_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))` and `sys.path.insert(0, QUIZ_ROOT)`.
- **Typing & Formatting**: Follow PEP 8 with explicit type hints (`str`, `dict`, `Optional`, `List`).
- **Tests**: Write unit & integration tests under `tests/` using `pytest`.
