# Project: LeLe Chinese Quiz Automation System Re-Architecture

## Architecture
The system consists of 4 isolated quiz sub-pipelines (`pinyinquiz`, `vocabCNquiz`, `vocabVNquiz`, `multilevelsquiz`) sharing a unified Google Spreadsheet state database (`1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0`) and Google Drive video storage folder (`1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB`).

The architecture is partitioned into 4 distinct workflow nodes:
1. **[1. Cloud Edge Gateway]**: Ultra-lightweight Cloudflare Workers (<2ms CPU) acting as pure asynchronous routers returning HTTP 202 Accepted immediately and triggering GitHub Actions.
2. **[2. Google Sheets State DB]**: Centralized state management across tabs `pinyin`, `vocabCN`, `vocabVN`, and `multilevels` with 16 standard columns (A:P), enforcing the strict invariant `Batch ID (#) == Physical Row Number`.
3. **[3. Google Colab Manim Engine (GPU T4 Accelerated)]**: 100% cloud-hosted compute on Google Colab GPU/CPU runtimes via google-colab-cli, executing Manim 1080x1920 60fps video rendering (including 30s 1 Nghĩa - 5 Cấp độ HSK format), Edge-TTS audio synthesis, multi-account Gmail rotation, and 0% VPS compute (GitHub Actions retained as standby backup).
4. **[4. Auto-QC & GDrive Storage]**: Automated video quality control (Gatekeeper 2 / OpenCV / FFprobe), direct streamable link generation in Column K (`https://drive.google.com/file/d/{FILE_ID}/view?usp=drivesdk`), and Telegram status alerts.

```
[User / Webhook / Cron]
         │
         ▼
[1. Cloud Edge Gateway] ──(HTTP 202 + repository_dispatch)──┐
         │ (or standalone cron / workflow_dispatch)         │
         ▼                                                  ▼
[2. Google Sheets State DB] ◄─── [3. GitHub Actions Manim Engine]
(pinyin, vocabCN, vocabVN, ml)   (Python ideation, GK1, Manim 60fps)
         ▲                                                  │
         │                                                  ▼
         └──────── (Col K direct URL) ───── [4. Auto-QC & GDrive Storage]
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Ultra-Lightweight Edge Router (<2ms CPU) | Replace monolithic CF workers with lightweight routers in `pinyinquiz`, `vocabCNquiz`, `vocabVNquiz` | M1 | Survey (Explorer 1) |
| 2 | HTTP 202 Async Dispatch | Immediate HTTP 202 Accepted response for `/api/receive-ideas` with `ctx.waitUntil` / async dispatch | M1 | Survey (Explorer 1) |
| 3 | Cloudflare Config Bug Fixes | Fix hardcoded stale domain fallbacks and cross-pipeline webhook URL references | M1 | Survey (Explorer 1) |
| 4 | Standalone Zero-Cloudflare Fallback | GitHub Actions `workflow_dispatch` and scheduled crons to run ideation and rendering without Cloudflare | M1 | Survey (Explorer 1) |
| 5 | Dynamic 6-Key Gemini Rotation | Ephemeral key rotation `(i-1)%len(keys)`, zero-secret logging, cascading models (3.7 ➔ 2.5 ➔ 2.0 ➔ 1.5) | M2 | Survey (Explorer 2) |
| 6 | Circuit Breaker & Multi-Tier Failover | 429 quota exhaustion cooldown recovery loop, OpenAI-compatible fallback, and local vocab banks | M2 | Survey (Explorer 2) |
| 7 | Deterministic Gatekeeper 1 Engine | 5 pure Python instant validation checks: 100% Simplified Chinese, single topic, pure VN, 1:1 syllable/tone, 5-word curve | M2 | Survey (Explorer 2) |
| 8 | VocabVN Pipeline Harmonization | Upgrade `vocabVNquiz/src/llm_client.py` and `scripts/generate_daily_batches.py` to match `vocabCNquiz`/`pinyinquiz` | M2 | Survey (Explorer 2) |
| 9 | In-View Live Terminal Dashboard | Upgrade `quiz/monitor.py` to render real-time 4-node status across `pinyin`, `vocabCN`, and `vocabVN` | M3 | Survey (Explorer 3) |
| 10 | Monitor CLI Flags (`--status`, `--verify-tab`, `--inview`) | Provide CLI inspection commands for Google Sheets state querying and tab health | M3 | Survey (Explorer 3) |
| 11 | Zero-VPS Compute Enforcement | Ensure 100% Manim rendering executes on GitHub Actions cloud runners with zero local host load | M4 | Survey (Explorer 3) |
| 12 | Column K Direct Playable GDrive URLs | Enforce `https://drive.google.com/file/d/{FILE_ID}/view?usp=drivesdk` across all pipelines | M4 | Survey (Explorer 3) |
| 13 | Sheet Row == Batch ID Invariant | Enforce strict physical row number matching Batch ID `#` across all sheet operations | M4 | Survey (Explorer 2, 3) |
| 14 | Multi-Pipeline E2E Lifecycle Verification | Execute and verify online batch progression (`Pending` ➔ `Rendering` ➔ `Video` ➔ `Ready`) for all 3 pipelines | M4 | Survey (Explorer 3) |
| 15 | Adversarial Coverage Hardening (Tier 5) | Comprehensive adversarial test generation and linguistic stress-testing across all validators | M4 | Orchestration Plan |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Ultra-Lightweight Edge Routers & HTTP 202 Async Dispatch | Refactor CF workers across 3 pipelines (<2ms CPU, HTTP 202 async dispatch, standalone triggers, fix config bugs) | none | DONE |
| M2 | Python Backend Harmonization, 6-Key Failover & Gatekeeper 1 | Harmonize `vocabVNquiz`, ensure 6-key Gemini failover, pure Python Gatekeeper 1 validations & negative context | none | DONE |
| M3 | In-View Real-Time Terminal Dashboard (`quiz/monitor.py`) | Upgrade `quiz/monitor.py` to live 4-node dashboard with `--status`, `--verify-tab`, `--inview` flags | M2 | DONE |
| M4 | Multi-Pipeline E2E Cloud Verification & Adversarial Hardening | E2E cloud test run across 3 pipelines, lifecycle verification, 0% VPS compute, GDrive Col K links, Tier 5 hardening | M1, M2, M3 | DONE |
| M5 | 100% Google Colab CLI Migration | Migrate Manim rendering & Auto-QC from GitHub Actions to Google Colab CLI (GPU T4 accelerated, multi-account Gmail rotation, warm session reuse, Zero-VPS compute preserved) | M1, M2, M3, M4 | DONE |

## Interface Contracts

### Edge Router ↔ GitHub Actions
- **Webhook Endpoint**: `POST /api/receive-ideas` or `POST /`
- **Response**: HTTP 202 Accepted immediately (`{"status": "accepted", "batch_id": "#...", "dispatched": true}`)
- **Dispatch Payload**:
  ```json
  {
    "event_type": "new_ideation_batch",
    "client_payload": {
      "pipeline": "pinyin" | "vocabCN" | "vocabVN",
      "batch_id": 25,
      "topic": "...",
      "timestamp": "..."
    }
  }
  ```

### Python Generator / Validator ↔ Google Sheets State DB
- **Spreadsheet ID**: `1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0`
- **Tabs**: `pinyin`, `vocabCN`, `vocabVN`
- **Columns (16)**:
  - `A`: `#` (Batch ID integer, matching physical row index)
  - `B`: `Topic` (2..50 chars, no delimiters)
  - `C`: `Level` (HSK 1..6)
  - `D`: `Status` (`Pending` ➔ `Rendering` / `In Progress` ➔ `Video` ➔ `Ready` / `Failed`)
  - `E..I`: `Word 1` .. `Word 5` (Formatted JSON/Dict per pipeline spec)
  - `J`: `metadata` (JSON payload with audio/quiz configuration)
  - `K`: `Video` (Direct playable Google Drive URL: `https://drive.google.com/file/d/{FILE_ID}/view?usp=drivesdk`)
  - `L..N`: `Youtube`, `Tiktok`, `Facebook`
  - `O`: `Created At` (ISO timestamp)
  - `P`: `Notes` (Gatekeeper 1/2 QC audit remarks)

### Monitor Dashboard CLI Contract
- `python quiz/monitor.py`: Renders live In-View 4-node terminal dashboard.
- `python quiz/monitor.py --status`: Prints instant status summary table with row counts per status (`Pending`, `Rendering`, `Video`, `Ready`) across all 3 tabs.
- `python quiz/monitor.py --verify-tab <pinyin|vocabCN|vocabVN>`: Performs deep schema and integrity audit for the specified tab.
- `python quiz/monitor.py --inview`: Continuous live refresh dashboard mode.

## Code Layout
- `pinyinquiz/`:
  - `cloudflare/`: Cloudflare worker edge router (`src/index.js`, `wrangler.toml`)
  - `src/`: Core Python modules (`pre_render_validator.py`, `llm_client.py`, `gsheet_manager.py`, `gdrive_uploader.py`, `render_engine.py`)
  - `scripts/`: Batch generation and execution scripts (`generate_daily_batches.py`, `run_batch.py`)
  - `tests/`: Unit and gatekeeper tests (`test_pinyin_gatekeeper.py`, etc.)
- `vocabCNquiz/`:
  - `cloudflare/`: Cloudflare worker edge router (`src/index.js`, `wrangler.toml`)
  - `src/`: Core Python modules (`pre_render_validator.py`, `llm_client.py`, `gsheet_manager.py`, `gdrive_uploader.py`, `render_engine.py`)
  - `scripts/`: Batch generation and execution scripts (`generate_daily_batches.py`, `run_batch.py`)
  - `tests/`: Unit and gatekeeper tests (`test_gatekeeper.py`, etc.)
- `vocabVNquiz/`:
  - `cloudflare/`: Cloudflare worker edge router (`src/index.js`, `wrangler.toml`)
  - `src/`: Core Python modules (`pre_render_validator.py`, `llm_client.py`, `gsheet_manager.py`, `gdrive_uploader.py`, `render_engine.py`)
  - `scripts/`: Batch generation and execution scripts (`generate_daily_batches.py`, `run_batch.py`)
  - `tests/`: Unit and gatekeeper tests (`test_vocabvn_gatekeeper.py`, etc.)
- `quiz/`:
  - `monitor.py`: Real-time In-View Terminal Dashboard across all 3 pipelines
- `.github/workflows/`:
  - Cloud ideation, rendering, and QC workflows for `pinyin`, `vocabCN`, `vocabVN`.
- `tests/`:
  - E2E and cross-pipeline verification suites (`test_gatekeeper1_adversarial_stress.py`, `test_live_sheets_empirical_audit.py`, `test_empirical_challenger_m3.py`).
