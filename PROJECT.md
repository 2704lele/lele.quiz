# Project: LeLe Chinese Quiz Automation & Pipeline Hardening

## Architecture
The LeLe Chinese Quiz production system automates end-to-end quiz video generation across 4 distinct quiz content domains:
1. `pinyinquiz`: Pinyin phonetic training and tone differentiation.
2. `vocabCNquiz`: Vocabulary recognition (Chinese Hanzi to Vietnamese).
3. `vocabVNquiz`: Reverse vocabulary recognition (Vietnamese to Chinese Hanzi).
4. `multilevelsquiz`: Multi-tier vocabulary and emotional gradation (HSK 1-5).

### Data Flow & Orchestration
```
Google Sheets (Master Database: 1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0)
   ├── Tabs: pinyin, vocabCN, vocabVN, multilevels
   │     │
   │     ▼
   ├── GitHub Actions Workflows (.github/workflows/)
   │     ├── 01_quiz_ideation_and_scripting.yml (00:00 GMT+7 -> cron '0 17 * * *')
   │     ├── 02_quiz_video_rendering_and_qc.yml (Every 4h -> cron '30 18,22,2,6,10,14 * * *')
   │     ├── 03_quiz_morning_audit.yml (05:01 GMT+7 -> cron '1 22 * * *')
   │     └── 04_quiz_social_distribution.yml (07:00 GMT+7 -> cron '0 0 * * *')
   │
   ▼
Rendering Engines (Manim 1080x1920 60fps + Edge-TTS Audio)
   ├── Manim short-form vertical video rendering (1080x1920, 60fps)
   ├── Gatekeeper 2 QC: Video format, duration, audio-video sync, resolution
   └── Upload to Google Drive canonical folders:
         ├── pinyin: 1f2mFUgpz_pYn3y9HqeHyOG9DzPMVH9QY
         ├── vocabCN: 1eI7I4jQqGBjD7MC_NXJ4zwFANxrcZM1E
         ├── vocabVN: 1VPqs9h4LLmmmXWKDGWoAz1fUCylVLK2H
         └── multilevels: 17xOkiW-XOWRDK2CCwNEl_rlf1rGKqKXm
   │
   ▼
State Transition & Invariant Enforcement
   ├── Google Sheets Column D -> "Ready"
   ├── Google Sheets Column K -> Direct streamable link: https://drive.google.com/file/d/{FILE_ID}/view?usp=drivesdk
   ├── Invariant: Enforce strictly 21px row height across all 4 tabs (scripts/enforce_row_height_21px.py)
   └── Audit: Morning Gatekeeper Audit + Telegram Briefing (scripts/run_morning_audit.py)
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Workflow Cron Scheduling | Configure native `schedule` POSIX UTC cron triggers in 01-04 YAML workflows | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Missing Dependency Fix | Add `rich` to `pip install` in `03_quiz_morning_audit.yml` and `04_quiz_social_distribution.yml` | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Workflow 04 Input Fallbacks | Add fallback expressions for null inputs when triggered via schedule/dispatch | M1 | Survey Explorer 1 |
| 4 | VPS Crontab Optimization | Remove deleted legacy scripts `auto_backup.py` and `sync_code_to_gdrive.py`, preserve HanaAssistant jobs | M1 | ORIGINAL_REQUEST §R2 |
| 5 | Dispatcher CLI Harmonization | Harmonize `scripts/run_render_dispatcher.py` to support pipeline-specific arguments across all 4 pipelines | M2 | Survey Explorer 2 |
| 6 | Pinyin Word Parser Fix | Update `pinyinquiz` to parse 3-part words and auto-compute `hidden_pinyin` | M2 | Survey Explorer 2 |
| 7 | GDrive Canonical Mapping & Streamable URL | Enforce canonical folder IDs and streamable URL format in Column K | M2 | Survey Explorer 2 |
| 8 | Batch Rendering 21 Pending Rows | Render 6 pinyin, 5 vocabCN, 5 vocabVN, 5 multilevels videos with Manim 1080x1920 60fps & Edge-TTS | M3 | ORIGINAL_REQUEST §R3 |
| 9 | Gatekeeper 2 QC & Status Promotion | Verify videos, upload to Google Drive, populate Col K, set Col D to `Ready` | M3 | ORIGINAL_REQUEST §R3 |
| 10 | 21px Row Height Invariant | Execute `scripts/enforce_row_height_21px.py` to maintain 100% 21px row height across all 4 tabs | M4 | ORIGINAL_REQUEST §R4 |
| 11 | Morning Audit Script Execution | Run `scripts/run_morning_audit.py` to reconcile sheet states and verify Google Drive purity | M5 | ORIGINAL_REQUEST §R5 |
| 12 | Telegram Briefing & Zero-Leak Vault | Verify Telegram transmission without leaking bot tokens or credentials | M5 | ORIGINAL_REQUEST §R5 |
| 13 | GitHub Actions E2E Verification | Trigger and verify `03_quiz_morning_audit.yml` test run on GitHub Actions | M5 | ORIGINAL_REQUEST §R5 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Workflow Cron Scheduling & VPS Crontab Optimization | Update 01-04 workflow files, add `rich`, optimize host crontab | none | DONE |
| M2 | Pipeline Pre-requisites & Dispatcher Hardening | Fix pinyin 3-part word parser, harmonize render dispatcher CLI flags, align GDrive folder mappings | none | DONE |
| M3 | Batch Rendering & Gatekeeper 2 QC for 21 Pending Rows | Execute Manim 1080x1920 60fps & Edge-TTS render, Gatekeeper 2 QC, update Col K GDrive links and Col D to `Ready` | M2 | DONE |
| M4 | 21px Row Height Invariant Enforcement | Run `scripts/enforce_row_height_21px.py` across all 4 tabs to guarantee 100% 21px invariant | M3 | DONE |
| M5 | E2E Audit, Telegram Briefing & GHA Verification | Verify local audit execution, run `03_quiz_morning_audit.yml` on GHA, verify Telegram brief | M1, M3, M4 | DONE |

## Interface Contracts

### Workflows ↔ GitHub Actions Runner
- `01_quiz_ideation_and_scripting.yml`: cron `'0 17 * * *'` (00:00 GMT+7)
- `02_quiz_video_rendering_and_qc.yml`: cron `'30 18,22,2,6,10,14 * * *'` (01:30, 05:30, 09:30, 13:30, 17:30, 21:30 GMT+7)
- `03_quiz_morning_audit.yml`: cron `'1 22 * * *'` (05:01 GMT+7), `pip install ... rich`
- `04_quiz_social_distribution.yml`: cron `'0 0 * * *'` (07:00 GMT+7), `pip install ... rich`

### Google Sheets ↔ Pipeline State Machine
- Tab names: `pinyin`, `vocabCN`, `vocabVN`, `multilevels`
- Column A (index 0): `ID` (e.g. `#54`, `#40`, `#33`, `#34`)
- Column D (index 3): `Status` -> Values: `Pending` -> `Rendering` -> `Video` -> `Ready` -> `Published`
- Column K (index 10): `Drive Link` -> Format: `https://drive.google.com/file/d/{FILE_ID}/view?usp=drivesdk`
- Column P (index 15): `Notes` -> Gatekeeper 2 QC timestamp & metadata
- Row Height: strictly `21px` across all rows `[0, rowCount)`

### Google Drive Storage Invariant
- Root Folder: `1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB` ("Quiz")
- Strictly 5 canonical subfolders:
  - `00.codebases` (`1C-n3Un-D6Teu4LapgIWWeVZ6l7toH8lm`)
  - `01.pinyinquiz` (`1f2mFUgpz_pYn3y9HqeHyOG9DzPMVH9QY`)
  - `02.vocabCNquiz` (`1eI7I4jQqGBjD7MC_NXJ4zwFANxrcZM1E`)
  - `03.vocabVNquiz` (`1VPqs9h4LLmmmXWKDGWoAz1fUCylVLK2H`)
  - `04.multilevelsquiz` (`17xOkiW-XOWRDK2CCwNEl_rlf1rGKqKXm`)
- Strictly 0 loose/orphan files in root.

## Code Layout
- `.github/workflows/`:
  - `01_quiz_ideation_and_scripting.yml`
  - `02_quiz_video_rendering_and_qc.yml`
  - `03_quiz_morning_audit.yml`
  - `04_quiz_social_distribution.yml`
- `scripts/`:
  - `run_render_dispatcher.py`: Central render dispatcher
  - `enforce_row_height_21px.py`: Row height invariant enforcer
  - `run_morning_audit.py`: Morning Gatekeeper audit & Telegram briefing
- `pinyinquiz/`:
  - `src/gsheet_manager.py`: Pinyin Google Sheets manager & parser
  - `scripts/run_batch.py`: Pinyin batch renderer
  - `scripts/run_qc.py`: Pinyin auto-QC
- `vocabCNquiz/`, `vocabVNquiz/`, `multilevelsquiz/`:
  - Individual quiz pipelines with `scripts/run_batch.py` and `scripts/run_qc.py`
