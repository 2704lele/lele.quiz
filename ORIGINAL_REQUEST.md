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
