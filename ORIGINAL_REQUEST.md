# Original User Request

## 2026-09-12T22:58:43Z

Automate and harden the LeLe Chinese Quiz production pipeline by configuring GitHub Actions cron schedules, resolving workflow dependency issues, cleaning up VPS cronjobs, batch rendering 21 pending quiz videos with Gatekeeper 2 QC, and verifying end-to-end reporting.

Working directory: `/media/vpsg16gb/Media/lelehoctiengtrung/quiz`
Integrity mode: development

## Requirements

### R1. GitHub Actions Automated Scheduling & Dependency Fixes
Configure native `schedule` (POSIX cron UTC) triggers for all 4 GitHub Actions workflows in `.github/workflows/`:
- `01_quiz_ideation_and_scripting.yml`: Daily ideation batch trigger at 00:00 GMT+7 (`cron: '0 17 * * *'`).
- `02_quiz_video_rendering_and_qc.yml`: Periodic pending render & Gatekeeper 2 QC trigger (01:30, 05:30, 09:30, 13:30, 17:30, 21:30 GMT+7 -> `cron: '30 18,22,2,6,10,14 * * *'`).
- `03_quiz_morning_audit.yml`: Daily morning audit trigger at 05:01 AM GMT+7 (`cron: '1 22 * * *'`). Include `rich` in `pip install` to eliminate `ModuleNotFoundError: No module named 'rich'`.
- `04_quiz_social_distribution.yml`: Automated publishing trigger or manual dispatch alignment.

### R2. VPS Crontab Optimization
Audit `crontab -l` on the host, remove invalid entries referencing deleted legacy scripts (`scripts/auto_backup.py`, `scripts/sync_code_to_gdrive.py`), and ensure all cron tasks align cleanly with zero-VPS compute / GitHub Actions cloud orchestration.

### R3. Batch Rendering & Gatekeeper 2 QC for Pending Rows
Process all 21 pending rows across the 4 quiz tabs (`pinyin`, `vocabCN`, `vocabVN`, `multilevels`):
- Execute Manim 1080x1920 60fps rendering and Edge-TTS synthesis in cloud runners / dispatcher.
- Run Gatekeeper 2 QC to verify video validity and populate Column K with direct Google Drive streamable URLs (`https://drive.google.com/file/d/{FILE_ID}/view?usp=drivesdk`).
- Update Column D status to `Ready`.

### R4. Enforce 21px Row Height Invariant
Execute `scripts/enforce_row_height_21px.py` across all 4 tabs to maintain 100% adherence to the 21px row height standard.

### R5. E2E Audit & Telegram Briefing
Trigger and verify `scripts/run_morning_audit.py` (and test run `03_quiz_morning_audit.yml`), ensuring Telegram notifications are sent successfully without secret exposure (Zero-Leak Vault).

## Acceptance Criteria

### Workflow & Cron Verification
- [ ] All 4 workflow YAML files in `.github/workflows/` contain valid `schedule` cron blocks and pass YAML syntax checks.
- [ ] `03_quiz_morning_audit.yml` contains `rich` in its pip install step and executes without module import errors.

### VPS Environment
- [ ] `crontab -l` contains no broken paths or non-existent script references.

### Pipeline Execution & Data Integrity
- [ ] All 21 pending rows in Google Sheets (`1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0`) are rendered, QC-checked, and transitioned to `Ready` status with valid Column K GDrive links.
- [ ] 100% of rows across all 4 tabs satisfy the 21px row height invariant.
- [ ] Morning audit script outputs `PASSED` and transmits the status brief to Telegram.

## 2026-09-14T00:29:35Z

# Comprehensive Pipeline Audit & Ideation Batch Generation

Working directory: `/media/vpsg16gb/Media/lelehoctiengtrung/quiz`
Integrity mode: development

## Objectives
Perform an end-to-end audit and execution across the LeLe Chinese Quiz automation system:
1. Audit and reconcile Google Sheets row indices vs Column A (`#<RowNumber>`) across all 4 worksheets (`pinyin`, `vocabCN`, `vocabVN`, `multilevels`). If any row index and Column A are mismatched or missing, fix them immediately.
2. Audit all 4 GitHub Actions workflows (`.github/workflows/`) for complete Python dependencies.
3. Audit Google Colab notebook (`scripts/render_quiz_colab.ipynb`) and CLI runners to ensure 100% parity with GitHub Actions.
4. Generate 5 verified ideas for each of the 4 tabs (20 new quiz batches total) under Gatekeeper 1 linguistic QC and enforce the 21px row height invariant.

## Requirements

### R1. Google Sheets Row Number & Column A Strict Alignment
- Inspect all rows across all 4 worksheets in Spreadsheet `1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0`.
- Enforce the invariant: Row $N$ in the sheet MUST have Column A strictly equal to `f"#{N}"`.
- Automatically fix any misalignments, duplicates, or missing numbers.
- Maintain the 21px row height invariant across 100% of rows in all 4 tabs.

### R2. GitHub Actions Workflow Dependencies Verification
- Audit `.github/workflows/`:
  - `01_quiz_ideation_and_scripting.yml`
  - `02_quiz_video_rendering_and_qc.yml`
  - `03_quiz_morning_audit.yml`
  - `04_quiz_social_distribution.yml`
- Verify that every workflow installs all necessary dependencies without missing packages (`manim`, `edge-tts`, `opencv-python-headless`, `opencc-python-reimplemented`, `gspread`, `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `pypinyin`, `requests`, `rich`, `scipy`, `numpy`, `Pillow`, `pydub`, `pyyaml`).

### R3. Google Colab vs GitHub Actions Parity Verification
- Inspect `scripts/render_quiz_colab.ipynb` and `scripts/colab_render_cli.py`.
- Ensure Colab installs the exact same dependency set and follows the exact same render, audio generation, and Google Drive upload logic (OAuth 2.0 direct file links in Column K) as GitHub Actions.

### R4. Batch Ideation Generation (5 Ideas per Tab)
- Execute `scripts/run_ideation_dispatcher.py` to generate 5 new ideas for each of the 4 tabs (`pinyin`, `vocabCN`, `vocabVN`, `multilevels`).
- Ensure all 20 batches pass Gatekeeper 1 linguistic QC with spaced pinyin (`mǐ fàn`).
- Verify all 20 rows are appended in `Pending` status with strict Column A sequential IDs.
- Execute `scripts/enforce_row_height_21px.py` to guarantee 100% 21px row height compliance.

## Acceptance Criteria

### Data & Schema Integrity
- [ ] 100% of rows across `pinyin`, `vocabCN`, `vocabVN`, and `multilevels` have Column A strictly equal to `#{RowIndex}`.
- [ ] 100% of rows satisfy the 21px row height invariant.

### Environment & Workflow Parity
- [ ] All 4 GitHub Actions workflows pass dependency audits without missing packages.
- [ ] Google Colab notebook (`render_quiz_colab.ipynb`) has 100% parity with GitHub Actions dependencies and direct file link uploads.

### Ideation Execution
- [ ] 5 valid batches added to `pinyin` (status `Pending`).
- [ ] 5 valid batches added to `vocabCN` (status `Pending`).
- [ ] 5 valid batches added to `vocabVN` (status `Pending`).
- [ ] 5 valid batches added to `multilevels` (status `Pending`).
- [ ] Morning audit passes with status `PASSED` across all 4 worksheets.

