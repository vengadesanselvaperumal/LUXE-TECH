# LUXE.TECH real-data verification

Audit performed: 2026-10-11, with live API and browser checks at approximately 19:21 UTC.

## Results

| Feature | Provider | Data freshness | Record count | Live-fetch status | Frontend display status | Root cause | Fix |
|---|---|---|---|---|---|---|---|
| Trend | No connected runway, social, search, or other trend-observation provider was found. | No verified observation timestamp or successful ingestion. | 16 trend rows and 560 signal rows in Supabase; all were `demo`. | **BLOCKED** — `GET /api/trends?limit=2` returned HTTP 200 with `[]`; no external source fetch is implemented. | **BLOCKED** — Trend page displays its source-verified empty state. | Seeded/demo rows are excluded from the live endpoint; no source-attributed observations are available. | Kept the demo rows out of live results and preserved the empty state. No provider was added because no permitted, accessible source was verified. |
| Product | No connected product catalogue, inventory, or retailer feed. Gemini is configured for generated ideation, not verified product inventory; a successful Gemini request was not verified. | No verified source timestamp or ingestion. | 48 product rows in Supabase; all were `demo`; live endpoint returns none. | **BLOCKED** — `GET /api/products?limit=2` returned HTTP 200 with `[]`. | **BLOCKED** — Product page explains that verified trends/evidence are required and shows no verified product records. | Existing records are demo concepts, not source-backed products or offers. | Preserved the evidence gate and empty state; did not present generated concepts as live catalogue data. |
| Retail | No connected retailer, point-of-sale, pricing, or assortment provider was found. | No verified observation timestamp or successful ingestion. | 64 retail-signal rows in Supabase; all were `demo`; zero verified retail observations. | **BLOCKED** — `GET /api/retail` returned HTTP 200 with `data_status: insufficient_data`, zero signal records, and no regions/categories. | **BLOCKED** — Retail page shows `INSUFFICIENT_DATA` and says no source-verified retail observations are connected. | There is no observed retailer feed; demo signals cannot support retail metrics. | Kept demo values excluded and displayed the missing-source state. No unapproved scraping or fabricated prices were added. |
| Forecast | No independent provider; forecasts are calculated from verified, timestamped TrendSignal observations. | No qualifying history. The API found 0 observations; at least 6 are required. | 16 forecast rows in Supabase; all were `demo`; 0 qualifying observations. | **BLOCKED** — `GET /api/forecast/digital-nature` returned HTTP 200 with `status: insufficient_data` and the exact 0-of-6 requirement. | **BLOCKED** — Forecast page displays insufficient telemetry and states that at least 6 chronological, source-attributed observations are required. | No valid historical input exists, so a forecast cannot responsibly be calculated. | Kept the minimum-history and provenance checks; no forecast was generated from demo history. |
| Prophecy | No independent source; it requires verified observations, a backtested forecast, and validated scenario evidence. | No qualifying history or forecast. | 80 prophecy rows in Supabase; all were `demo`; live verified timeline has 0 items. | **BLOCKED** — `GET /api/prophecy/digital-nature` returned HTTP 200 with `Found 0 verified observations; 6 are required.` | **BLOCKED** — Prophecy page displays `NO SCENARIO` and says no verified supporting evidence is available. | Demo scenario rows cannot substantiate a live prediction. Before the fix, the insufficient-data response also claimed `current_stage: emerging`. | The insufficient-data response now returns `current_stage: null`; isolated test confirms it makes no unsupported stage claim. The evidence gate and explanatory message remain. |
| Fashion news | Vogue publisher RSS: <https://www.vogue.com/feed/rss>. | Newest returned article observation: `2026-10-11T16:47:08+00:00`. Feed fetched successfully at `2026-10-11T19:21:01.969862+00:00`; `stale: false` when checked around 19:21 UTC. | 20 articles in the current API response/cache; 0 persisted news rows (there is no news table). | **PASS** — `GET /api/news/current` returned HTTP 200, `success: true`, `data_status: observed`, Vogue provenance, and 20 items. | **PASS** — Browser shows `SOURCE: VOGUE`, article headlines, publisher links, and publisher timestamps. The UI states that no market metrics are inferred from headlines. | The publisher feed is fetched and cached in memory; it is not persisted as database news history. | Existing RSS ingestion and UI provenance were verified. No additional news provider or invented summary was added. |
| Vision Lab | User-uploaded image bytes processed locally with OpenCV. Supabase Storage reports configured but unverified; Gemini is configured, but an actual successful vision request was not verified. | No production image observation or verified upload time. | 0 production image rows. A generated PNG was processed in an isolated test only; it was not stored remotely. | **PARTIAL / BLOCKED for live providers** — Isolated `POST /api/images/analyze` returned HTTP 200 using temporary local storage and an in-memory SQLite database. Gemini and Supabase Storage were deliberately not called. | **BLOCKED for browser upload-result verification** — Existing Vision Lab result UI is present, but this audit did not submit the test file through the browser. | A configured Supabase upload that failed could silently fall back to a local file and return success; private-image signed-URL refresh errors were swallowed. Gemini reachability and remote Storage permissions remain unverified. | Configured Supabase upload failures now fail explicitly instead of returning local-storage success; image listing now surfaces signed-URL refresh failures. Isolated image test produced 320×320 derived metrics and 5 dominant colors. |
| Dashboard metrics | No connected sources were found for runway, social, search, retail, or culture metrics. Vogue news is a separate provider and does not establish these measures. | No verified signal timestamp or successful ingestion. | No verified dashboard observations; all five metric channels were `null`. | **BLOCKED** — `GET /api/dashboard` returned HTTP 200, empty trend/product/forecast/prophecy highlights, and `insufficient_data` live signals. | **BLOCKED for live metrics** — Dashboard has honest no-data states. Its separate Vogue article list renders successfully. | No source-backed signal data feeds the dashboard aggregates. The dashboard does not turn headlines into metrics. | Preserved null metrics and no-data states; no values were inferred or fabricated. |

## Provider and database evidence

- The live backend health endpoint reported PostgreSQL connected, Supabase Postgres configured and connected, Supabase Storage `configured_unverified`, and Gemini configured. Configuration flags do not establish that Storage uploads or Gemini generation succeed.
- The Supabase project identity was checked against the API configuration before the prior read-only database audit; SSL was required and the database transaction was confirmed read-only. This verification made no remote writes, schema changes, migrations, or seed calls.
- The database snapshot found demo-only records for trends (16), trend signals (560), products (48), retail signals (64), forecasts (16), and prophecies (80). The image-record count was 0. The news API is in-memory and no news table was present.
- The API responses and browser checks were read-only. The Vision Lab POST check used an isolated in-memory SQLite database, a generated PNG, and temporary local storage; all were discarded after the check. It did not call Gemini or upload to Supabase.
- Browser checks confirmed the existing Trend, Product, Retail, Forecast, and Prophecy pages render evidence-gated empty/insufficient states. The Home page rendered the Vogue feed and retained article links and timestamps.

## Exact files changed

- `backend/app/services/supabase_service.py` — configured Storage upload failures no longer silently succeed through local fallback.
- `backend/app/routers/images.py` — private-image signed-URL refresh errors are no longer swallowed.
- `backend/app/routers/prophecy.py` — insufficient-evidence responses no longer state an unsupported current stage.
- `backend/tests/test_supabase_storage.py` — added configured-provider failure tests.
- `backend/tests/test_prophecy_data_integrity.py` — added an isolated insufficient-evidence regression test.
- `supabase/proposals/REAL_DATA_VERIFICATION.md` — this audit report.

No frontend files, environment files, remote schema, or database records were changed.

## Validation

- Frontend production build: `npm run build` — passed (`tsc -b` and Vite build).
- Isolated backend tests: 16 passed, 2 endpoint tests deselected. Tests ran with `--noconftest` to avoid the repository's autouse fixture, which calls `seed_database`.
- Vision Lab isolated image request: HTTP 200; one image row in the temporary database; temporary local file confirmed; dimensions 320×320; five dominant colors; local metrics marked `derived`. Gemini was not invoked.
- Prophecy live response after the code change: HTTP 200, `data_status: insufficient_data`, `current_stage: null`, 0 timeline entries, and the 0-of-6 observation message.
- Pylance diagnostics on changed Python files: no errors.

## Unresolved dependencies

1. Trend, Product, Retail, and Dashboard metrics need an explicitly authorized, accessible source feed (and credentials/terms where required) with timestamped records and source provenance. No such provider was verified in this workspace.
2. Forecast needs at least 6 chronological observations marked observed, with a source name, timezone-aware fetch timestamp, and HTTPS source URL or user-upload provenance.
3. Prophecy additionally needs a forecast backtested against those observations and a validated scenario.
4. Vision Lab's local OpenCV metrics work, but live Gemini semantic analysis and a successful Supabase Storage upload remain unverified. The running health flags report only that the providers are configured; remote upload/model calls were intentionally not made during this audit.

## Phase 1.1 implementation note (2026-10-12)

- `GET /api/news/candidate-trends` returns in-memory, `News-derived` editorial candidates with publisher counts and linked article provenance. Its response does not include trend metrics or database `data_status`.
- The Trend page loads these candidates separately from `GET /api/trends`, so editorial candidates can render even when the persisted-observation response is empty. Article frequency is not presented as consumer demand, sales, search volume, runway prevalence, or predictive accuracy.
- `POST /api/news/ingest` remains the privileged persistence path. This phase did not call that endpoint or verify live database rows; no live persistence is claimed.
