# E2E Test Infra: LeLe Chinese Quiz Automation

## Test Philosophy
- Opaque-box, requirement-driven. Derived from ORIGINAL_REQUEST.md and production invariants.
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise + Workload Testing.

## Feature Inventory & Test Mapping
| # | Feature | Source (Requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|----------------------|:------:|:------:|:------:|
| 1 | Workflow Cron Schedules | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 2 | Python Missing Dependencies (`rich`) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 3 | Workflow 04 Input Fallbacks | Survey Explorer 1 | 5 | 5 | ✓ |
| 4 | VPS Crontab Cleanliness | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 5 | Dispatcher CLI Compatibility | Survey Explorer 2 | 5 | 5 | ✓ |
| 6 | Pinyin 3-Part Parsing & Auto-Pinyin | Survey Explorer 2 | 5 | 5 | ✓ |
| 7 | Google Drive Canonical Purity | Survey Explorer 3 | 5 | 5 | ✓ |
| 8 | Batch Video Rendering (21 rows) | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 9 | Gatekeeper 2 QC & Status Promotion | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 10 | 21px Row Height Invariant | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 11 | Morning Audit Reconciliation | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ |
| 12 | Telegram Briefing & Zero-Leak Vault | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ |
| 13 | GitHub Actions Run Verification | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ |

## Test Architecture
- Test Runner: Python test suite `scripts/run_e2e_verification.py` + `scripts/run_morning_audit.py`
- Invariant Validators:
  - YAML syntax & schedule trigger validator (PyYAML)
  - Crontab audit validator (`crontab -l`)
  - Google Sheets status & URL validator (`gspread`)
  - 21px row height validator (`scripts/enforce_row_height_21px.py`)
  - Google Drive storage purity validator (Google Drive API v3)
  - GitHub Actions run validator (`gh run view`)

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Cloud Scheduled Cycle (Morning Audit -> Ideation -> Render -> QC -> Social) | F1, F2, F3, F8, F9, F10, F11, F12, F13 | High |
| 2 | Invariant Recovery & Storage Purity Assurance | F4, F7, F10, F11 | Medium |
| 3 | Batch Ingestion & Gatekeeper Promotion of New Content | F5, F6, F8, F9, F10 | High |
| 4 | Zero-Leak Vault Security & Telegram Alerting | F2, F11, F12 | Medium |
| 5 | Dual-Platform Execution Consistency (VPS local CLI vs GitHub Actions runner) | F1, F2, F4, F10, F11, F13 | High |

## Coverage Thresholds
- Tier 1: ≥5 test cases per feature (happy-path isolation)
- Tier 2: ≥5 test cases per feature (boundary and error-handling conditions)
- Tier 3: pairwise coverage of major feature interactions
- Tier 4: ≥5 realistic application scenarios
