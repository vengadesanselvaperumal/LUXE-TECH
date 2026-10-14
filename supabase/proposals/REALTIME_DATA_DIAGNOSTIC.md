# LUXE.TECH Real-Time Data Diagnostic

**Evidence date:** 2026-10-11 (UTC)  
**Scope:** Existing frontend, API routes, configured data services, current Supabase records, and safe local verification.  
**Safety:** The Supabase project/schema check was read-only. No remote SQL, migrations, uploads, resets, `.env` changes, or service-role values were used or disclosed. Browser/API verification ran against an isolated local SQLite database.

## Executive finding

The UI was rendering seed/demo data as if it were live intelligence. The checked Supabase tables contained only `data_status='demo'` records, and no scheduler or trend/product/retail ingestion provider was found. The configured Vogue RSS feed is the one verified external live data source. It now powers a request-driven current-news endpoint and the existing home-page news section; the 20 articles were fetched, returned by FastAPI, and rendered in the browser.

No live Trend, Product, Retail, Forecast, or Prophecy result is claimed. Their current response states accurately show empty, insufficient evidence, or a specific missing dependency. Local OpenCV image metrics are computed from uploaded bytes; a live Gemini image interpretation was not verified.

## Feature-by-feature trace and evidence

HTTP checks below were made against the edited FastAPI app on local SQLite, not against Supabase. A source response of HTTP 200 means the request succeeded; the `data_status` and result shape indicate whether there is usable source data. Hidden-demo detail requests use the API's standard failure envelope, whose `meta.http_status` carries the logical not-found code.

| Feature / UI path | API result and observed shape | Data evidence / root cause | Current behavior |
|---|---|---|---|
| Home current fashion news | `GET /api/news/current`: HTTP 200, `success=true`; object with 20 `items`, `source_name=Vogue`, publisher/feed URLs, article `observed_at`, request `fetched_at`, quality, and `data_status=observed`. | Latest verified fetch: `2026-10-11T18:14:43Z`; the first article in that response had `observed_at=2026-10-11T16:47:08Z` (about 88 minutes before fetch). The browser displayed article titles and publication times. No news table exists; records are held in a five-minute process cache and are not durable. `stale` indicates a failed refresh; there is no separate maximum publication-age cutoff. | Real publisher records are displayed with provenance, fetch time, refresh/loading/empty/error states, and stale-cache notice. This is request-driven, not scheduled ingestion. |
| Trend list, categories, details, signals | `GET /api/trends?limit=2`: HTTP 200, empty array. `GET /api/trends/categories`: HTTP 200, 16 categories with zero observed counts. `GET /api/signals/live`: HTTP 200, all channels null, `data_status=insufficient_data`, count 0. | Supabase snapshot: 16 demo trends, 560 demo trend signals, 16 demo DNA records. Latest stored signal timestamp was `2026-10-11T16:48:26Z`, but it was demo data, not a verified observation. No connected trend/signal ingestion provider or scheduler was found. | Trend, signal, dashboard, and search reads exclude demo data. Detail reads cannot turn demo rows into intelligence. The UI explains when no source-attributed trends exist. |
| Product | `GET /api/products?limit=2`: HTTP 200, empty array. Demo trend product-generation request is rejected by the app as `TREND_NOT_FOUND` (logical 404 in the response envelope). | Supabase snapshot: 48 demo products, latest `2026-10-11T16:48:31Z`. No verified product source/ingestion is connected; generated fallback concepts are not retail observations. | Product reads and search exclude demo rows. The empty state states that verified evidence is required; generation is disabled when there is no observed trend. |
| Retail | `GET /api/retail`: HTTP 200; empty signal/region/category arrays and `data_status=insufficient_data`. Trend view is also empty. | Supabase snapshot: 64 demo retail signals; latest `2026-10-04T16:48:26Z`. No retailer feed/API or ingestion job was found. Schema does not provide verified retailer identity, price, or sell-through provenance. | Retail aggregates use observed rows only; fabricated demand bars are removed. The UI shows unavailable metrics and an explicit no-source-records message. |
| Forecast | `GET /api/forecast/digital-nature`: HTTP 200, `status=data_status=insufficient_data`; 0 verified observations, minimum 6. Historical/projected points and model evaluations are not emitted without adequate observations. | Supabase contained 16 demo forecasts (latest `2026-10-11T16:48:30Z`). They are not usable training data. The forecast endpoint previously accepted demo signals; it now validates timestamp, fetch time, and publisher or explicit upload provenance. | Forecasting requires at least six verified historical observations; saved results are marked `forecast` and carry their training interval. UI explains the missing evidence and does not label an absent forecast as available. |
| Prophecy | `GET /api/prophecy/digital-nature`: HTTP 200, empty `timeline`, `data_status=insufficient_data`, message: `Found 0 verified observations; 6 are required.` | Supabase contained 80 demo scenarios, latest `2026-10-11T16:48:31Z`. No validated forecast/evidence chain supported them. | Demo scenarios are hidden. Generation requires verified observations, a backtested forecast, and validated AI output; otherwise the response explains which prerequisite is missing. |
| Image analysis | `GET /api/images`: HTTP 200, empty array in the isolated validation database. Remote Supabase snapshot had 0 image records. | Uploaded files are processed by local OpenCV feature extraction. Gemini image interpretation/provider accessibility was not verified; configured credentials alone are not evidence of a successful provider call. Remote storage upload was intentionally not exercised. | Real uploaded bytes yield derived image metrics locally. The Gemini fallback no longer invents an interpretation and instead reports provider unavailability. Upload/storage remains dependent on a reachable, correctly configured storage provider. |
| Dashboard and search | `GET /api/dashboard`: HTTP 200, object; with only seeded demo records, observed trend/product/forecast/prophecy lists are empty, signal channels are null, and current fashion summary is `insufficient_data`. Search returns no demo catalog records. | Seeded records previously populated dashboard summaries and search results despite `data_status=demo`. | Both surfaces now use verified/eligible records only. Current publisher news is supplied by its dedicated endpoint and home-page component. |

### Supabase row counts and freshness snapshot

The prior read-only inspection reported the following snapshot at `2026-10-11T17:19:37Z`. These are existing project records, not rows created by this work.

| Table | Rows / status | Latest stored timestamp | Interpretation |
|---|---:|---|---|
| `trends` | 16 demo | `2026-10-11T16:48:30Z` | No observed trend rows |
| `trend_signals` | 560 demo | `2026-10-11T16:48:26Z` | Recent timestamp does not make demo data observed |
| `trend_dna` | 16 demo | `2026-10-11T16:48:31Z` | Seeded/demo |
| `products` | 48 demo | `2026-10-11T16:48:31Z` | No observed products |
| `retail_signals` | 64 demo | `2026-10-04T16:48:26Z` | Demo and older than other seed records |
| `forecasts` | 16 demo | `2026-10-11T16:48:30Z` | Not backtests on verified observations |
| `prophecy` | 80 demo | `2026-10-11T16:48:31Z` | Not evidence-backed scenarios |
| `collections` | 16 demo | `2026-10-11T16:48:30Z` | Demo |
| `images` | 0 | — | No remote image records |
| Fashion news | No table | — | News records are transient process-cache entries |

The read-only configuration/schema inspection found that the configured Supabase API and database references resolve to the dedicated LUXE.TECH project and that the ORM schema matches the inspected schema. Project identifiers and credentials are intentionally omitted here.

### Environment-variable names inspected

`DATABASE_URL`, `DIRECT_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `SECRET_KEY`, `CORS_ORIGINS`, and frontend `VITE_API_URL`. Values are not included in this report. Presence/configuration of a variable is not treated as proof that its provider is reachable.

## Providers and ingestion

- **Verified connected source:** Vogue's public RSS feed (`https://www.vogue.com/feed/rss`), fetched on request. Latest verified fetch during browser validation: `2026-10-11T18:14:43Z`; 20 article records were parsed and displayed. The newest returned article observation time was `2026-10-11T16:47:08Z`.
- **Trend, product, retail:** No permitted/accessibly configured real provider or ingestion implementation was found. No values were fabricated to fill the gap.
- **Forecast and Prophecy:** These are analysis layers, not source providers. Forecast needs six verified historical observations; Prophecy additionally requires a backtested forecast and validated AI scenario.
- **Images:** Local OpenCV metrics work on uploaded files. Gemini may be configured, but successful access/interpretation was not demonstrated. Supabase storage credentials were reported configured but unverified; no remote upload was attempted.
- **Scheduling:** No scheduled ingestion job was found.
- **Persistence limitation:** There is no fashion-news table, so publisher articles and provenance cannot be persisted without a separately reviewed schema proposal/migration. None was applied.
- **Required external dependencies for more live features:** a permitted and accessible fashion-trend and retailer/product source, provider credentials/terms where required, a reviewed way to persist provenance, and verified Gemini/storage availability if those services are expected to provide image interpretation/storage.

## Root causes addressed

1. Demo seed records were returned through public list, detail, aggregate, dashboard, and search paths without consistently excluding them.
2. Forecast and Prophecy could consume or expose demo rows instead of requiring source-attributed observations and validated evidence.
3. The home page had no current-news provider request; no news ingestion or news table existed.
4. UI state and static fallback values could suggest current retail demand, trend season, or forecast availability with no connected source.
5. Image interpretation had a success-shaped fallback; local image features are genuine derived measurements, but an unavailable AI provider must not imply a semantic interpretation.
6. A SQLAlchemy datetime model attribute was used as a boolean in serialization, producing Pylance's `Column[datetime]` conditional-operand diagnostic. Serialization now narrows the ORM value explicitly before formatting.

## Files changed

- `backend/app/database.py`
- `backend/app/main.py`
- `backend/app/routers/dashboard.py`
- `backend/app/routers/forecasts.py`
- `backend/app/routers/news.py` (new)
- `backend/app/routers/products.py`
- `backend/app/routers/prophecy.py`
- `backend/app/routers/signals.py`
- `backend/app/routers/trends.py`
- `backend/app/services/fashion_news_service.py` (new)
- `backend/app/services/forecast_engine.py`
- `backend/app/services/gemini_service.py`
- `backend/app/services/observations.py` (new)
- `backend/app/services/prophecy_engine.py`
- `backend/app/services/retail_engine.py`
- `backend/app/services/search_engine.py`
- `backend/tests/test_all_features.py`
- `backend/tests/test_api_security.py`
- `backend/tests/test_fashion_news.py` (new)
- `frontend/src/App.tsx`
- `frontend/src/services/api.ts`

No Supabase migration, SQL proposal execution, schema reset, or remote write was performed.

## Verification

- Backend: `pytest backend/tests -q` — **46 passed**, one existing Starlette/httpx deprecation warning.
- Frontend: `npm run build` (`tsc -b && vite build`) — **passed**.
- Browser: Vite UI was loaded against the isolated API; Network showed successful dashboard, trend, category, signal, product, retail, and current-news requests. Vogue articles and source/fetch metadata rendered. Demo-only features displayed empty/insufficient evidence instead of seed values.
- API: Health, current news, trends, dashboard, live signals, products, retail, forecast, prophecy, and images were checked with GET requests on the isolated SQLite app. The Vogue request returned 20 items; demo-only data reads were empty; forecast and Prophecy returned their insufficient-evidence messages.
- Provider errors: No Vogue provider exception occurred in the verified fetch. News-service failure/stale-cache behavior is covered by unit tests. No Gemini or remote storage availability claim is made.
