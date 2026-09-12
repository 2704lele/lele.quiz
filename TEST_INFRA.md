# Test Infrastructure & Methodology: LeLe Chinese Quiz Automation System

## 1. Overview & Quality Engineering Principles

This document defines the End-to-End (E2E) Test Infrastructure and 4-Tier Test Methodology for the **LeLe Chinese Quiz Automation System** across all three sub-pipelines:
1. **`pinyinquiz`** (Hanzi ➔ Pinyin, Google Sheets tab: `pinyin`)
2. **`vocabCNquiz`** (Hanzi ➔ Vietnamese definition, Google Sheets tab: `vocabCN`)
3. **`vocabVNquiz`** (Vietnamese definition ➔ Hanzi, Google Sheets tab: `vocabVN`)

### Core Engineering Invariants
- **Opaque-Box Verification:** Tests assert observable external contracts (HTTP status codes, response payloads, execution latency budgets, schema structures, and deterministic validation return values) rather than private implementation details.
- **Zero VPS Compute:** All video rendering (Manim Community Edition 1080x1920 60fps) and audio synthesis execute 100% on GitHub Actions Cloud Runners (`ubuntu-22.04`). The local VPS process table must remain 0% burdened by rendering jobs.
- **Strict Linguistic Purity:** 100% Simplified Chinese characters (0% Traditional Chinese), 100% pure Vietnamese definitions without forbidden English words or loanword corruptions, and exact 1:1 Pinyin syllable-to-Hanzi correspondence.
- **Row Index Invariant:** Physical Google Sheet row number strictly equals Batch ID integer (`# == Row Number`).
- **Streamable Column K URLs:** Video links in Column K must conform strictly to `https://drive.google.com/file/d/{FILE_ID}/view?usp=drivesdk`.

---

## 2. The 4-Tier Test Methodology

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TIER 4: REAL-WORLD APPLICATION SCENARIOS             │
│   • Daily Production Crons   • Rate Limit Recovery   • Auto-Heal E2E    │
├─────────────────────────────────────────────────────────────────────────┤
│                 TIER 3: CROSS-FEATURE COMBINATION TESTING               │
│   • Pairwise Edge Router + GK1  • 6-Key Failover + Sheets DB Sync       │
├─────────────────────────────────────────────────────────────────────────┤
│                 TIER 2: BOUNDARY & CORNER CASE COVERAGE                 │
│   • Erhua Contractions  • Non-Vietnamese Phonemes  • 429 Quota Storms   │
├─────────────────────────────────────────────────────────────────────────┤
│                     TIER 1: CORE FEATURE COVERAGE                       │
│   • 15 Features × >=5 Assertions = 75+ Comprehensive Feature Tests      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Feature Inventory & Verification Matrix

The test infrastructure covers all 15 features defined in `PROJECT.md § Feature Inventory`:

| # | Feature Name | Milestone | Scope / Target Modules | Primary Invariant |
|---|--------------|-----------|------------------------|-------------------|
| F1 | Ultra-Lightweight Edge Router (<2ms CPU) | M1 | `*/cloudflare/src/index.js` | CPU execution time < 2ms, zero subrequest bloat |
| F2 | HTTP 202 Async Dispatch Contract | M1 | `*/cloudflare/src/index.js` | Immediate HTTP 202 Accepted on `/api/receive-ideas` |
| F3 | Cloudflare Config Bug Fixes | M1 | `*/cloudflare/wrangler.toml`, `src/config.js` | No cross-pipeline webhook leaks, active domains only |
| F4 | Standalone Zero-Cloudflare Fallback | M1 | `.github/workflows/`, `scripts/` | `workflow_dispatch` manual trigger without CF dependencies |
| F5 | Dynamic 6-Key Gemini Rotation | M2 | `*/src/llm_client.py` | `(i-1)%len(keys)` rotation, zero-secret log masking |
| F6 | Circuit Breaker & Multi-Tier Failover | M2 | `*/src/llm_client.py` | 429 cooldown loop, fallback models, local bank fallback |
| F7 | Deterministic Gatekeeper 1 Engine | M2 | `*/src/pre_render_validator.py` | 5 pure Python rules (<1ms), OpenCC/Traditional/English filter |
| F8 | VocabVN Pipeline Harmonization | M2 | `vocabVNquiz/src/`, `vocabVNquiz/scripts/` | Match `pinyinquiz` & `vocabCNquiz` generator architectures |
| F9 | In-View Live Terminal Dashboard | M3 | `monitor.py` | 4-node schema visualization across all 3 pipelines |
| F10 | Monitor CLI Flags (`--status`, `--verify-tab`, `--inview`) | M3 | `monitor.py` | CLI flags for instant health check & schema verification |
| F11 | Zero-VPS Compute Enforcement | M4 | System / Process Table (`ps aux`) | 0% Manim rendering on local VPS host |
| F12 | Column K Direct Playable GDrive URLs | M4 | `*/src/gdrive_uploader.py`, GSheets | `https://drive.google.com/file/d/{FILE_ID}/view?usp=drivesdk` |
| F13 | Sheet Row == Batch ID Invariant | M4 | `*/src/gsheet_manager.py`, GSheets | Sheet physical row index strictly matches Batch ID `#` |
| F14 | Multi-Pipeline E2E Lifecycle Verification | M4 | Cross-pipeline orchestration | Complete state transition `Pending` ➔ `Rendering` ➔ `Video` ➔ `Ready` |
| F15 | Adversarial Coverage Hardening (Tier 5) | M4 | `tests/` | Multi-character fuzzing, homoglyphs, mojibake, malformed JSON |

---

## 4. Tier 1: Feature Coverage Specifications (>=5 per Feature = 75 Cases)

### Feature 1: Ultra-Lightweight Edge Router (<2ms CPU)
- `T1-F1-01`: Root GET `/` returns HTTP 200 with JSON payload containing project status and active pipeline name.
- `T1-F1-02`: CPU execution budget under normal routing conditions remains strictly under 2.0 milliseconds.
- `T1-F1-03`: Total outgoing subrequests during edge routing equals 1 (`workflow_dispatch` dispatch call).
- `T1-F1-04`: Edge router delegates all cryptographic RSA-SHA256 JWT operations to cloud runners (0 WebCrypto calls in worker).
- `T1-F1-05`: Edge router delegates all LLM prompt parsing and linguistic regex auditing away from worker memory.

### Feature 2: HTTP 202 Async Dispatch Contract
- `T2-F2-01`: POST `/api/receive-ideas` returns HTTP 202 Accepted within <50ms wall-clock response time.
- `T2-F2-02`: Response body contains `{"status": "Accepted", "dispatched": true, "timestamp": "..."}`.
- `T2-F2-03`: Background dispatch utilizes `ctx.waitUntil()` non-blocking promise execution.
- `T2-F2-04`: POST `/api/trigger-ideation` returns HTTP 202 Accepted and triggers `ScriptNewIdeation.yml`.
- `T2-F2-05`: POST `/api/render` returns HTTP 202 Accepted and dispatches `Render.yml` with target `row_id`.

### Feature 3: Cloudflare Config Bug Fixes
- `T1-F3-01`: `pinyinquiz/cloudflare/src/config.js` does not contain stale domain `.aleron-dt.workers.dev`.
- `T1-F3-02`: `vocabVNquiz/cloudflare/src/github_trigger.js` does not leak `pinyinquiz` webhook URL on unset env.
- `T1-F3-03`: `wrangler.toml` across all 3 pipelines defines isolated `SHEET_TAB_NAME` (`pinyin`, `vocabCN`, `vocabVN`).
- `T1-F3-04`: `wrangler.toml` specifies correct GitHub Actions workflow files (`Render.yml`, `vocabcn_render.yml`, `vocabvn_render.yml`).
- `T1-F3-05`: All 3 worker configurations have cron triggers safely disabled in development (`crons = []`).

### Feature 4: Standalone Zero-Cloudflare Fallback
- `T1-F4-01`: `generate_daily_batches.py` runs standalone via CLI flag `--mode batch` without contacting Cloudflare.
- `T1-F4-02`: Direct Google Sheets writing mode (`--direct-write`) writes batches without Cloudflare worker intermediary.
- `T1-F4-03`: GitHub Actions workflows support direct manual execution via `workflow_dispatch` with parameter overrides.
- `T1-F4-04`: Negative context history can be read directly from Google Sheets API via Python `gspread`.
- `T1-F4-05`: Standalone fallback vocabulary banks provide emergency generation if all network APIs are unreachable.

### Feature 5: Dynamic 6-Key Gemini Rotation
- `T1-F5-01`: `parse_gemini_keys` parses comma, semicolon, newline delimited key strings and list inputs.
- `T1-F5-02`: Key selection indexing follows ephemeral rotation `key_index = (batch_id - 1) % len(keys)`.
- `T1-F5-03`: `mask_key()` masks keys to `AIzaSy...****` and never prints plaintext keys to stdout/stderr.
- `T1-F5-04`: Key rotation progresses sequentially across the 6-key pool without starvation.
- `T1-F5-05`: Missing API key configuration gracefully falls back to OpenAI-compatible endpoint or local bank.

### Feature 6: Circuit Breaker & Multi-Tier Failover
- `T1-F6-01`: HTTP 429 response triggers immediate failover to the next available API key in the pool.
- `T1-F6-02`: Exhaustion of all 6 keys triggers the 60s Quota Recovery Cooldown Loop before retry.
- `T1-F6-03`: Model hierarchy cascades from `gemini-3.7-flash` ➔ `gemini-2.5-flash` ➔ `gemini-2.0-flash` ➔ `gemini-1.5-flash`.
- `T1-F6-04`: Total API outage cascades gracefully to secondary OpenAI-compatible endpoint (`LLM_BASE_URL`).
- `T1-F6-05`: Tier 3 fallback activates embedded deterministic vocabulary bank when all LLM services fail.

### Feature 7: Deterministic Gatekeeper 1 Engine
- `T1-F7-01`: Rule 1 validates 100% Simplified Chinese characters (passes valid Simplified words like `妈妈`, `苹果`, `学校`).
- `T1-F7-02`: Rule 2 validates single focused topics (passes `Đồ Dùng Nhà Bếp`, `HSK 1 • Đồ Ăn`, `Thời tiết bốn mùa`).
- `T1-F7-03`: Rule 3 validates pure Vietnamese meanings (passes `Cái bàn học`, `Quả táo đỏ`, `Đi học buổi sáng`).
- `T1-F7-04`: Rule 4 validates 1:1 Pinyin syllable count and tone marks (passes `bà ba`, `mā ma`, `píng guǒ`).
- `T1-F7-05`: Rule 5 validates exact 5-word batch size, intra-batch uniqueness, and emotional retention curve.

### Feature 8: VocabVN Pipeline Harmonization
- `T1-F8-01`: `vocabVNquiz/src/pre_render_validator.py` matches rule implementations of `vocabCNquiz` and `pinyinquiz`.
- `T1-F8-02`: `vocabVNquiz/src/llm_client.py` supports 6-key rotation and multi-tier failover identically to `pinyinquiz`.
- `T1-F8-03`: `vocabVNquiz/scripts/generate_daily_batches.py` supports `--mode batch` and `--mode single_row`.
- `T1-F8-04`: VocabVN batch format correctly handles Vietnamese prompt ➔ Hanzi quiz structure.
- `T1-F8-05`: VocabVN negative context history query targets worksheet tab `vocabVN`.

### Feature 9: In-View Live Terminal Dashboard
- `T1-F9-01`: `python quiz/monitor.py` executes without uncaught exceptions and renders Rich terminal UI.
- `T1-F9-02`: Dashboard displays 4 workflow nodes: `[1. CF Worker]` ➔ `[2. Google Sheets]` ➔ `[3. GH Actions]` ➔ `[4. Auto-QC & GDrive]`.
- `T1-F9-03`: Dashboard renders active status table for all 3 sub-pipelines (`pinyinquiz`, `vocabCNquiz`, `vocabVNquiz`).
- `T1-F9-04`: Dashboard displays architecture directives (Zero-VPS ban, Spreadsheet ID, Row invariant).
- `T1-F9-05`: Output cleanly adapts to standard 80-column and wide terminal viewports.

### Feature 10: Monitor CLI Flags (`--status`, `--verify-tab`, `--inview`)
- `T1-F10-01`: `python quiz/monitor.py --status` prints summary table with counts for Pending, Rendering, Video, Ready.
- `T1-F10-02`: `python quiz/monitor.py --verify-tab pinyin` audits schema and integrity of tab `pinyin`.
- `T1-F10-03`: `python quiz/monitor.py --verify-tab vocabCN` audits schema and integrity of tab `vocabCN`.
- `T1-F10-04`: `python quiz/monitor.py --verify-tab vocabVN` audits schema and integrity of tab `vocabVN`.
- `T1-F10-05`: `python quiz/monitor.py --inview` initiates live refresh mode without crashing.

### Feature 11: Zero-VPS Compute Enforcement
- `T1-F11-01`: Local host process table contains 0 active `manim` rendering processes during test runs.
- `T1-F11-02`: Local host process table contains 0 long-running video encoding `ffmpeg` processes.
- `T1-F11-03`: 100% of Manim rendering commands are constrained to GitHub Actions runner environments.
- `T1-F11-04`: Local scripts restrict execution to orchestration, testing, and status query actions.
- `T1-F11-05`: CPU load on VPS host remains unaffected during cloud batch execution.

### Feature 12: Column K Direct Playable GDrive URLs
- `T1-F12-01`: GDrive URLs match regex `^https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)/view\?usp=drivesdk$`.
- `T1-F12-02`: Extracted GDrive File ID contains at least 25 characters.
- `T1-F12-03`: `GDriveUploader.upload_file` automatically sets `anyone:reader` public view permissions.
- `T1-F12-04`: Column K links are directly streamable in browsers and video players without redirect loops.
- `T1-F12-05`: Invalid or empty GDrive URLs trigger Gatekeeper 2 / Auto-QC rejection.

### Feature 13: Sheet Row == Batch ID Invariant
- `T1-F13-01`: Physical row index $N$ contains Batch ID `#N` in Column A for all data rows ($N \ge 2$).
- `T1-F13-02`: Header row occupies physical row 1 with exactly 16 standard column names (A..P).
- `T1-F13-03`: `GSheetManager.get_row_by_id(N)` returns physical row index $N$.
- `T1-F13-04`: Batch insertion logic calculates target row via `row_number = batch_id`.
- `T1-F13-05`: Row re-generation (`--mode single_row --row-id N`) strictly updates row $N$ without shifting other rows.

### Feature 14: Multi-Pipeline E2E Lifecycle Verification
- `T1-F14-01`: Batch lifecycle transitions correctly: `Pending` ➔ `Rendering` / `In Progress` ➔ `Video` ➔ `Ready`.
- `T1-F14-02`: Auto-QC inspection verifies 1080x1920 resolution, 60fps framerate, and valid audio streams.
- `T1-F14-03`: Column J contains valid 3-channel social metadata (YouTube Shorts, TikTok, Facebook Reels).
- `T1-F14-04`: Column P (Notes) records Auto-QC pass timestamp upon promotion to `Ready`.
- `T1-F14-05`: State machine prevents promotion to `Ready` if video file is missing or corrupted.

### Feature 15: Adversarial Coverage Hardening (Tier 5)
- `T1-F15-01`: Validator rejects Traditional Chinese characters embedded inside long Simplified Chinese sentences.
- `T1-F15-02`: Validator rejects sneaky English words inside compound Vietnamese strings (e.g. `Ăn apple`, `Đi taxi`).
- `T1-F15-03`: Validator rejects tone mismatches and invalid neutral tone syllables in multi-syllable words.
- `T1-F15-04`: Validator rejects malformed JSON responses with unescaped control characters from LLM.
- `T1-F15-05`: Validator rejects topic strings containing disguised delimiters (e.g. `Đồ ăn; thức uống`, `Chào hỏi, v.v.`).

---

## 5. Tier 2: Boundary & Corner Cases (>=5 per Feature = 75 Cases)

| Feature | Test Case ID | Boundary / Corner Case Condition | Expected Behavior |
|---|---|---|---|
| F1 | `T2-F1-01` | Edge router receives empty POST payload `{}` | Returns HTTP 400 Bad Request or graceful default without crash |
| F1 | `T2-F1-02` | Edge router receives 100 concurrent webhook requests | Handles burst within <2ms CPU per event via async `waitUntil` |
| F1 | `T2-F1-03` | Edge router receives unknown route `/api/unknown` | Returns HTTP 404 Not Found cleanly |
| F1 | `T2-F1-04` | GitHub Actions API returns HTTP 500 downstream | Worker logs error in background without blocking 202 client response |
| F1 | `T2-F1-05` | Large request headers (>8KB) sent to edge router | Handled within Cloudflare header limits without worker crash |
| F2 | `T2-F2-01` | POST `/api/receive-ideas` with invalid JSON string | Returns HTTP 400 with descriptive error JSON |
| F2 | `T2-F2-02` | Ingestion payload with non-integer `batch_id` | Sanitized to integer or string representation cleanly |
| F2 | `T2-F2-03` | Ingestion payload with missing `pipeline` field | Defaults to worker's configured `SHEET_TAB_NAME` |
| F2 | `T2-F2-04` | Rapid sequential POSTs for identical batch ID | Queued asynchronously without race condition |
| F2 | `T2-F2-05` | POST `/api/receive-ideas` with `auto_render=false` | Dispatches ideation without chaining render workflow |
| F3 | `T2-F3-01` | `CF_WEBHOOK_URL` environment variable is undefined | Falls back to pipeline-specific worker URL, never cross-pipeline |
| F3 | `T2-F3-02` | `GITHUB_TOKEN` secret is empty or whitespace | Warns in configuration validation without crashing process |
| F3 | `T2-F3-03` | `wrangler.toml` contains special characters in tab name | Tab name sanitized to standard alphanumeric string |
| F3 | `T2-F3-04` | Multiple AI gateway bindings defined in wrangler | Resolves active gateway name for current environment |
| F3 | `T2-F3-05` | Node.js compatibility flags missing in wrangler | Worker builds cleanly under Cloudflare standard runtime |
| F4 | `T2-F4-01` | Standalone script invoked with `--count 0` | Exits cleanly with 0 batches generated |
| F4 | `T2-F4-02` | Standalone script invoked with `--delay 0` | Executes immediately without artificial sleep |
| F4 | `T2-F4-03` | Standalone script invoked with invalid `--level HSK9` | Rejects invalid HSK level and suggests 1..6 |
| F4 | `T2-F4-04` | Google Sheets API returns 429 during standalone write | Retries with exponential backoff up to 4 attempts |
| F4 | `T2-F4-05` | Standalone script runs with completely empty Sheet | Initializes 16 standard column headers automatically |
| F5 | `T2-F5-01` | `GEMINI_API_KEYS` contains duplicate keys | Deduplicates keys during parsing, preserving unique pool |
| F5 | `T2-F5-02` | `GEMINI_API_KEYS` contains trailing commas & newlines | Trims whitespace and extracts only valid key tokens |
| F5 | `T2-F5-03` | Single key provided (`len(keys) == 1`) | Rotates safely with `(i-1)%1 == 0` without index error |
| F5 | `T2-F5-04` | Extremely short API key (`len(key) <= 8`) | `mask_key` safely masks to `****` without slice index error |
| F5 | `T2-F5-05` | Key rotation with `batch_id = 0` or negative int | Normalizes index safely to valid positive range |
| F6 | `T2-F6-01` | All 6 Gemini keys return HTTP 429 on all models | Enters 60s Quota Recovery loop and sends Telegram alert |
| F6 | `T2-F6-02` | Google AI Studio returns HTTP 503 Service Unavailable | Retries with secondary candidate models in hierarchy |
| F6 | `T2-F6-03` | LLM returns HTTP 200 with non-JSON text | `parse_json_from_llm` extracts JSON code blocks or arrays |
| F6 | `T2-F6-04` | LLM returns JSON with trailing commas `[...,]` | Regex cleaner strips trailing commas and parses successfully |
| F6 | `T2-F6-05` | OpenAI fallback returns 401 Unauthorized | Skips OpenAI tier and activates emergency local vocab bank |
| F7 | `T2-F7-01` | Universal heritage character (e.g. `生`, `床`, `衣服`) | Accurately recognized as valid Simplified Chinese |
| F7 | `T2-F7-02` | Contracted Erhua Pinyin (e.g. `哪儿` ➔ `nǎr`, `玩儿` ➔ `wánr`) | Validated as legitimate 1-syllable contraction |
| F7 | `T2-F7-03` | Multi-syllable word with neutral tone (e.g. `妈妈` ➔ `mā ma`) | Validated against `VALID_NEUTRAL_SYLLABLES` |
| F7 | `T2-F7-04` | Allowed loanword in Vietnamese (e.g. `cà phê`, `xe buýt`, `tivi`) | Whitelisted and accepted without forbidden English false positive |
| F7 | `T2-F7-05` | Topic with Vietnamese connector (`Thời tiết & Khí hậu`) | Accepted as valid single topic (connector `&`, `và`, `-` allowed) |
| F8 | `T2-F8-01` | VocabVN receives batch with 4 or 6 words | Rejects with explicit error: must contain exactly 5 words |
| F8 | `T2-F8-02` | VocabVN batch contains duplicate Vietnamese definitions | Rejects with intra-batch duplicate meaning error |
| F8 | `T2-F8-03` | VocabVN batch contains duplicate Hanzi characters | Rejects with intra-batch duplicate Hanzi error |
| F8 | `T2-F8-04` | VocabVN candidate topic overlaps with past sheet topic | Rejects candidate under negative context deduplication |
| F8 | `T2-F8-05` | VocabVN candidate shares $\ge 2$ words with past batch | Rejects candidate under pair repetition rule |
| F9 | `T2-F9-01` | Dashboard executed in narrow terminal (<60 cols) | Wraps tables gracefully without crashing |
| F9 | `T2-F9-02` | Dashboard executed with non-UTF8 environment | Enforces UTF-8 encoding for Chinese/Vietnamese glyphs |
| F9 | `T2-F9-03` | Node status is in `BUSY` or `ERROR` state | Renders correct colored status badge (`[bold blue]` / `[bold red]`) |
| F9 | `T2-F9-04` | Dashboard executed in CI/CD non-interactive mode | Prints single snapshot without blocking terminal |
| F9 | `T2-F9-05` | Dashboard executed when network is offline | Renders cached/static architecture view without uncaught error |
| F10 | `T2-F10-01` | `--verify-tab` called with invalid tab `unknown_tab` | Prints error message listing valid tabs (`pinyin`, `vocabCN`, `vocabVN`) |
| F10 | `T2-F10-02` | `--status` called when Google Sheets has 0 rows | Reports 0 counts across statuses without division-by-zero |
| F10 | `T2-F10-03` | `--status` called with unauthenticated credentials | Prints graceful auth error and instructions |
| F10 | `T2-F10-04` | Multiple flags passed simultaneously (`--status --verify-tab pinyin`) | Executes both actions sequentially |
| F10 | `T2-F10-05` | `--verify-tab` encounters missing columns in sheet | Pinpoints exact missing column indices in output report |
| F11 | `T2-F11-01` | Local developer accidentally executes `manim` locally | Test runner flags violation and verifies CI/CD enforces cloud execution |
| F11 | `T2-F11-02` | GitHub Actions runner runs out of disk space during render | Workflows configure caching and workspace cleanup steps |
| F11 | `T2-F11-03` | Video render exceeds runner time limit (>15 mins) | GitHub Actions workflow sets step timeout to 15 minutes |
| F11 | `T2-F11-04` | Background subprocesses left orphaned on runner | GitHub runner ephemeral container terminates all child PIDs |
| F11 | `T2-F11-05` | Process inspection test runs on different OS architectures | Uses portable `psutil` or standard `ps` parsing |
| F12 | `T2-F12-01` | Uploaded video filename contains spaces and unicode | GDrive uploader sanitizes and uploads successfully |
| F12 | `T2-F12-02` | GDrive user OAuth refresh token expires | Automatically refreshes access token via OAuth2 token endpoint |
| F12 | `T2-F12-03` | GDrive user quota full | Cascades to Service Account credentials automatically |
| F12 | `T2-F12-04` | Permission setting fails due to corporate domain policy | Logs warning and falls back to standard folder view link |
| F12 | `T2-F12-05` | Column K URL contains extra query params or trailing slash | Regex normalizer extracts clean standard view link |
| F13 | `T2-F13-01` | Sheet has blank rows between data rows | Auto-healing / validator detects gap and flags invariant error |
| F13 | `T2-F13-02` | Column A contains string `#25` vs integer `25` | Normalizer parses both formats and verifies equality to row index |
| F13 | `T2-F13-03` | Sheet row insertion at boundary $N=500$ | Google Sheets manager expands sheet grid automatically |
| F13 | `T2-F13-04` | Batch ID out-of-order in Sheet | Auditor highlights mismatched row indices with warning |
| F13 | `T2-F13-05` | Sheet update with partial 10-column array | Padds to 16 columns to prevent shifting downstream columns |
| F14 | `T2-F14-01` | Batch generation produces 5 words with low contrast | Gatekeeper 2 video QC luminance audit catches blowout |
| F14 | `T2-F14-02` | Edge-TTS audio file is 0 bytes due to network drop | Pre-render validator detects missing audio and re-synthesizes |
| F14 | `T2-F14-03` | Video duration is under 15s or over 120s | Auto-QC flags duration non-compliance and blocks `Ready` |
| F14 | `T2-F14-04` | Video FPS is below 23.0 fps | Auto-QC flags framerate non-compliance |
| F14 | `T2-F14-05` | Video cover frame has black screen at 00:00 | Auto-QC cover stability audit catches black frame |
| F15 | `T2-F15-01` | Hanzi input containing zero-width spaces or BOM | Sanitizer removes invisible characters before validation |
| F15 | `T2-F15-02` | Vietnamese meaning with mojibake characters `\ufffd` | Validator rejects invalid character encoding |
| F15 | `T2-F15-03` | Topic with length 51 characters (1 char over limit) | Validator rejects with max length error |
| F15 | `T2-F15-04` | Pinyin with missing tone mark on multi-syllable word | Validator flags un-toned syllable not in neutral list |
| F15 | `T2-F15-05` | Vietnamese meaning identical to Hanzi prompt | Validator rejects definition identical to prompt |

---

## 6. Tier 3: Cross-Feature Combinations (Pairwise Coverage)

Pairwise interaction testing validates that sub-components interact seamlessly across subsystem boundaries:

| Interaction Pair | Interacting Features | Verification Focus | Expected Invariant |
|---|---|---|---|
| **P1** | F1 (Edge Router) + F2 (HTTP 202) + F4 (GH Actions) | Ingestion webhook receives batch and dispatches cloud render asynchronously | Edge returns 202 in <50ms; GH runner starts `Render.yml` |
| **P2** | F5 (6-Key Gemini) + F6 (Circuit Breaker) + F7 (Gatekeeper 1) | Key rotation under 429 rate limit while validating 5-word candidate | Cooldown/failover executes; Gatekeeper 1 audits final batch |
| **P3** | F7 (Gatekeeper 1) + F13 (Row Invariant) + F14 (Lifecycle) | Validated batch persisted to Google Sheet at exact physical row index | Row number == Batch ID; status initialized to `Pending` |
| **P4** | F4 (Cloud Render) + F11 (Zero VPS) + F12 (GDrive URL) | Cloud runner executes Manim 60fps render and uploads to Google Drive | 0% VPS CPU load; Column K populated with direct view link |
| **P5** | F9 (Monitor UI) + F10 (CLI Flags) + F13 (Sheet State) | Monitor CLI `--status` and `--verify-tab` querying live state DB | Accurate row counts per tab; schema validation report |
| **P6** | F8 (VocabVN) + F7 (Gatekeeper 1) + F5 (Gemini Rotation) | VocabVN batch generation using rotated keys and harmonized validator | 100% Simplified Chinese & pure Vietnamese meanings |
| **P7** | F14 (Auto-QC) + F12 (GDrive URL) + F13 (Notes QC) | Auto-QC inspecting rendered video from Drive and promoting to `Ready` | Status promoted to `Ready`; Notes updated with QC timestamp |

---

## 7. Tier 4: Real-World Application Scenarios (>=5 Scenarios)

### Scenario 1: Scheduled Daily 5-Batch Batch Production Run
- **Flow:** Cron triggers `generate_daily_batches.py --mode batch --count 5 --delay 10`.
- **Validation:** 5 sequential batches generated for alternating HSK levels, rotating through Gemini keys 1..5. All 5 batches pass Gatekeeper 1 rules and are inserted into rows $N..N+4$ with `# == Row Index`. Zero VPS rendering compute.

### Scenario 2: Single-Row Re-generation on Gatekeeper 1 Rejection
- **Flow:** Row $N$ contains invalid Traditional Chinese or forbidden English word. Orchestrator triggers `--mode single_row --row-id N --rejected-topic "..." --error-reasons "..."`.
- **Validation:** LLM receives explicit negative feedback, generates a clean replacement batch, passes Gatekeeper 1, and overwrites row $N$ in-place without altering neighboring rows.

### Scenario 3: Complete API Rate Limit Storm & Automatic Failover
- **Flow:** External traffic causes Google AI Studio to return HTTP 429 on all primary Gemini keys.
- **Validation:** System logs 429 warnings with masked keys, enters 60s Quota Recovery Loop, sends Telegram alert, fails over to candidate models/OpenAI endpoint, and completes batch generation without crashing.

### Scenario 4: End-to-End Ingestion ➔ Cloud Render ➔ Auto-QC ➔ Ready Promotion
- **Flow:** Ingest webhook POST to `/api/receive-ideas` with valid 5-word batch.
- **Validation:** Router returns HTTP 202 Accepted immediately. GitHub Actions triggers `Render.yml` on cloud runner. Video rendered at 1080x1920 60fps. Uploaded to GDrive folder `1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB`. Column K populated with direct playable link. Auto-QC validates video streams and promotes status to `Ready`.

### Scenario 5: Multi-Tab Live Monitor Audit & Health Verification
- **Flow:** Operator executes `python quiz/monitor.py --status` and `python quiz/monitor.py --verify-tab all`.
- **Validation:** Real-time summary table displayed for `pinyin`, `vocabCN`, and `vocabVN` tabs. Schema audit verifies 16 standard columns and Batch ID invariant across all tabs.

---

## 8. Test Execution Commands & Environment Matrix

### Runner Commands

```bash
# 1. Run all unit, contract, and opaque-box E2E test suites
pytest tests/ -v

# 2. Run Gatekeeper 1 deterministic linguistic validation suite
pytest tests/test_gatekeeper1_engine.py -v

# 3. Run Cloudflare Edge Router contract test suite
pytest tests/test_cloudflare_edge_router.py -v

# 4. Run Google Sheets schema and invariant test suite
pytest tests/test_gsheet_schema_and_invariants.py -v

# 5. Run Gemini rotation and failover test suite
pytest tests/test_gemini_rotation_and_failover.py -v

# 6. Run Zero VPS compute invariant test suite
pytest tests/test_zero_vps_compute.py -v

# 7. Run Monitor CLI flags and dashboard test suite
pytest tests/test_monitor_cli.py -v

# 8. Run Full Opaque-Box E2E Lifecycle Simulation
pytest tests/test_e2e_opaque_box.py -v
```

---

## 9. Requirements Traceability Matrix

| Requirement | Description | Test Module | Test Cases |
|---|---|---|---|
| **R1** | Cloudflare Decoupled Lightweight Gateway (<2ms, HTTP 202) | `tests/test_cloudflare_edge_router.py` | `test_edge_router_*`, `test_http_202_*` |
| **R2** | Zero-Secret 6-Key Rotation & Gatekeeper 1 Deterministic Engine | `tests/test_gatekeeper1_engine.py`, `tests/test_gemini_rotation_and_failover.py` | `test_rule_1_*` .. `test_rule_5_*`, `test_key_rotation_*` |
| **R3** | In-View Real-Time Terminal Dashboard & CLI Flags | `tests/test_monitor_cli.py` | `test_monitor_*`, `test_cli_flags_*` |
| **R4** | End-to-End Multi-Pipeline Verification & Cloud Invariants | `tests/test_gsheet_schema_and_invariants.py`, `tests/test_zero_vps_compute.py`, `tests/test_e2e_opaque_box.py` | `test_schema_*`, `test_zero_vps_*`, `test_e2e_lifecycle_*` |
