# LUXE.TECH — Fashion Intelligence Platform

A fashion intelligence application built with **FastAPI**, **React/Vite**, local statistical and computer-vision engines, and optional **Google Gemini** and **Supabase** services.

---

## Architecture

```text
                    LUXE.TECH
                         │
                  ┌──────┴──────┐
                  │  FRONTEND   │ (React + Vite + TypeScript)
                  └──────┬──────┘
                         │
                   REST API CLIENT (/js/api.js)
                         │
                  ┌──────┴──────┐
                  │   FASTAPI   │ (Uvicorn Async Backend)
                  └──────┬──────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
    SQL DATABASE      OPTIONAL        LOCAL AI
    SQLite default    GEMINI          Engines
    PostgreSQL opt.   Reasoning       OpenCV
    Supabase Storage  Vision          Pandas
                                      Statsmodels
        │                │                │
        └────────────────┼────────────────┘
                         │
                  FASHION INTELLIGENCE
                         │
       ┌─────────┬───────┼────────┬─────────┐
       │         │       │        │         │
     TREND    PRODUCT  RETAIL  FORECAST  PROPHECY
```

---

## 01 — Environment Variables

The platform uses `.env` in the root (and fallback `backend/.env`). A `.env.example` template is provided:

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash
YOUTUBE_API_KEY=

DATABASE_URL=sqlite:///./backend/luxe_tech.db

SECRET_KEY=

CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000
```

> **Security Guarantee:** Private credentials (`SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `DATABASE_URL`, `SECRET_KEY`) are accessed strictly by the backend server and are never bundled or exposed to the browser.

If `SECRET_KEY` is blank, the backend generates a random key at startup. Set a stable, private value in `.env` if tokens must survive restarts.

---

## 02 — Database and Optional Supabase Services

`DATABASE_URL` selects the SQLAlchemy database. Keep the SQLite URL for local development. PostgreSQL startup is read-only: the app verifies the migrated tables/columns and does not create schema or insert demo seed data. Apply reviewed SQL migrations manually before switching the app to Supabase PostgreSQL.

The authenticated social-observation submission slice adds `trend_submissions`. Its additive deployment SQL is proposal-only at [`supabase/proposals/20261012_trend_submissions.sql`](./supabase/proposals/20261012_trend_submissions.sql); review it for the target project and deploy it explicitly before enabling submissions against PostgreSQL. No remote migration is run by the application. The optional YouTube discovery page requires a backend-only `YOUTUBE_API_KEY`; without it, the provider reports unavailable and returns no fabricated results. User-submitted image uploads use the private `user-uploads` bucket when Supabase Storage is configured.

1. In the Supabase Dashboard, open **Project Settings → Database → Connect** and copy the PostgreSQL connection URI. Use the direct connection if supported by your network, otherwise use the **Session pooler** URI. Do not use the transaction pooler for this app's current SQLAlchemy connection.
2. Back up any existing database and inspect the SQL Editor target project. The migrations create tables/indexes/policies and buckets; `002` can rename legacy JSON columns and convert their values to the app's text-serialized JSON format. These scripts do not drop application rows, but they do alter schema and must be reviewed before execution.
3. In **SQL Editor**, run `supabase/migrations/001_initial_schema.sql`, then `supabase/migrations/002_align_existing_schema.sql`. The second migration is repeat-safe for columns already aligned and raises an error rather than guessing if both a legacy and replacement column exist.
4. Run the verification queries below. Confirm `user-uploads` is still private. `trend-images` and `collections` are intentionally public for fashion imagery and shareable moodboards; do not put private files in either bucket.
5. In the project root, open `.env` locally and replace only `DATABASE_URL` with the copied URI, using the SQLAlchemy driver prefix `postgresql+psycopg://`. URL-encode special characters in the username/password. Never paste the URI into chat or commit it. Restart the backend; `/api/health` reports the live dialect, and startup refuses to create or seed cloud schema.

The URL shape is `postgresql+psycopg://<dashboard-user>:<URL-encoded-password>@<dashboard-host>:<port>/<database>?sslmode=require`; use the exact host, port, username, and database shown by Supabase rather than the placeholders.

```powershell
Set-Location 'C:\Users\Lenovo\Downloads\FORCASTING WEBSITE'
notepad .env
Set-Location 'C:\Users\Lenovo\Downloads\FORCASTING WEBSITE\backend'
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Use the SQLite URL from `.env.example` to return to local development. Supabase URL/API keys configure Storage and PostgREST only; they do not select PostgreSQL. The current authentication implementation is backend-managed JWT authentication, not Supabase Auth. RLS protects PostgREST roles, while the backend's private PostgreSQL connection is trusted server access and must never be exposed to the browser.

### Supabase verification queries

Run these read-only queries in the Supabase SQL Editor after migrations:

```sql
SELECT c.relname AS table_name, c.relrowsecurity AS rls_enabled
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY c.relname;

SELECT schemaname, tablename, policyname, roles, cmd
FROM pg_policies
WHERE schemaname IN ('public', 'storage')
ORDER BY schemaname, tablename, policyname;

SELECT grantee, table_name, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
  AND grantee IN ('anon', 'authenticated')
ORDER BY grantee, table_name, privilege_type;

SELECT id, public
FROM storage.buckets
WHERE id IN ('trend-images', 'user-uploads', 'collections')
ORDER BY id;
```

The app migration grants only public `SELECT` on the listed intelligence tables; it adds no public table-write permissions and no Storage object policies. The backend uploads with its server-only service role. `user-uploads` remains private and its upload response uses a one-hour signed URL; public URLs are refused for buckets not explicitly configured as public.

### Tables
1. **`users`**: id, email, password_hash, name, role, created_at, updated_at
2. **`trends`**: id, slug, name, category, season, description, image_url, status, confidence, momentum, velocity, acceleration, data_status, created_at, updated_at
3. **`trend_signals`**: id, trend_id, source (`runway`, `social`, `search`, `retail`, `culture`), signal_type, strength, direction, timestamp, metadata, data_status
4. **`trend_dna`**: id, trend_id, colors, materials, textures, silhouettes, patterns, visual_description, ai_interpretation, data_status, created_at
5. **`images`**: id, trend_id, storage_path, public_url, width, height, dominant_colors, contrast, brightness, saturation, edge_density, data_status, created_at
6. **`collections`**: id, trend_id, name, description, color_palette, materials, textures, silhouettes, patterns, product_opportunities, data_status, created_at
7. **`products`**: id, trend_id, name, category, description, material, silhouette, color, target_consumer, opportunity_score, ai_reasoning, data_status, created_at
8. **`retail_signals`**: id, trend_id, region, category, demand, growth, consumer_signal, timestamp, data_status
9. **`forecasts`**: id, trend_id, model (`moving_average`, `simple_exponential_smoothing`, `holt_winters`, `linear_regression`), horizon, forecast_value, backtest_accuracy (stored in the legacy `confidence` column), training_start, training_end, data_status, created_at
10. **`prophecy`**: id, trend_id, stage (`current`, `emerging`, `accelerating`, `mainstream`, `next`), forecast, evidence, opportunity, risk, confidence, data_status, created_at
11. **`saved_trends`**: id, user_id, trend_id, created_at

### Storage Buckets
- `trend-images`: Public bucket for trend imagery
- `user-uploads`: Private bucket; never make it public
- `collections`: Public for intentionally shareable moodboards (user-confirmed)

---

## 03 — Local AI Engines & Gemini Integration

### Local Computer Vision (`app/services/vision_engine.py`)
- **K-Means clustering in OpenCV** extracts 5 dominant palette colors: HEX, RGB, HSV, and exact surface percentage.
- **Grayscale contrast and brightness** computed via pixel intensity standard deviation and mean.
- **Saturation** computed from HSV color-space.
- **Edge density** computed using OpenCV Canny edge detection.

### Statistical Time-Series Forecasting (`app/services/forecast_engine.py`)
- 4 competing models:
  1. **Moving Average (SMA)**
  2. **Simple Exponential Smoothing (SES)** via `statsmodels`
  3. **Holt-Winters Double Exponential Smoothing** via `statsmodels`
  4. **Linear Regression** via `scikit-learn`
- Chronological walk-forward backtesting calculates **MAE**, **RMSE**, and **MAPE** on held-out observations. Displayed MAPE accuracy is `max(0, 100 - MAPE)` and is not a probability or prediction interval.
- Automatically selects the champion model with minimum RMSE.
- Enforces strict data integrity: if observations `< 6`, returns `{"status": "insufficient_data"}` without fabricating statistical confidence.

### Gemini AI Reasoning (`app/services/gemini_service.py`)
- Uses the `google-genai` SDK and the configured `GEMINI_MODEL` (default: `gemini-3.8-flash`) for trend synthesis, product concepts, image interpretation, and 5-stage prophecy.
- Validates structured JSON schema outputs.
- In-memory SHA-256 caching ensures minimal API overhead.
- **Resilient Fallback Mode:** Local fallbacks remain available without a key or network and are labelled `demo`, not `ai_generated`.

---

## 04 — Standardized API Response & Data Status

Every endpoint responds using the standard envelope:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {}
}
```

Every intelligence record is strictly tagged with its origin:
- `observed`: Raw verified signal
- `derived`: Calculated dynamically by local math engines
- `forecast`: Statistical time-series model projection
- `ai_generated`: Synthesized by Gemini reasoning
- `demo`: Synthetic development baseline
- `insufficient_data`: Explicit lack of sufficient telemetry

---

## 05 — Running the Platform

### Option A: One-Click Windows Launch
Double-click:
```powershell
start.bat
```
This automatically boots the FastAPI backend on `http://127.0.0.1:8000` and the Vite frontend on `http://127.0.0.1:5173`.

### Option B: Manual Launch

#### 1. Backend
```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive Swagger API documentation:
`http://127.0.0.1:8000/docs`

#### 2. Frontend
```powershell
cd frontend
npx vite --host 127.0.0.1 --port 5173
```
Open in browser:
`http://127.0.0.1:5173`

---

## 06 — Running Tests

Run the backend test suite:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest
```
Tests cover:
- Authentication flow & JWT tokens
- Health check & database auto-seeding
- Dashboard intelligence aggregation
- 16-card trend grid and category filtering
- Live signal streams & trend signals
- OpenCV image feature extraction & vision API
- Collection & product AI generation
- Retail telemetry and category comparison
- Forecast 4-model backtesting & insufficient data detection
- 5-stage prophecy evolutionary trajectory
- Multi-domain search query grouping
- Invalid file upload protection
