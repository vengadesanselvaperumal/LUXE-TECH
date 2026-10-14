# LUXE.TECH — Phase 04 Database Readiness Audit

**Audit status: Phase 06 read-only baseline complete — migration approval pending**  
**Scope: local review plus explicitly read-only Supabase catalog inspection; no remote writes**

## 1. Executive summary

The intended production target is a new Supabase project dedicated to LUXE.TECH. Phase 05A safely correlated the database endpoint and Supabase API endpoint to the same project, and the user has now confirmed that it is the dedicated LUXE.TECH project. Phase 06 verified the correlation again locally and completed catalog-only inspection inside a transaction confirmed read-only.

The project does not install or use the Supabase Python SDK: `backend/requirements.txt` has no SDK dependency, and neither project virtual environment has the Supabase package installed. `supabase_service.py` makes direct HTTPX requests to Storage and PostgREST REST endpoints.

The configured publishable (`sb_publish...`) and secret (`sb_secret_...`) key formats are not, by themselves, evidence of incompatibility: modern Supabase API gateways accept these as API keys. However, this implementation also places its active key in an `Authorization: Bearer ...` header. These keys are not JWTs and must not be assumed valid as bearer JWTs. Since no SDK is used and no network request is permitted, end-to-end compatibility is **UNVERIFIED**. Correct the header/authentication handling before relying on PostgREST or Storage.

The Phase 05A database setting uses the Supabase transaction pooler. SQLAlchemy is initialized with default psycopg settings. Prefer direct or session-pooler connections for migration/DDL work; for application traffic on the transaction pooler, explicitly disable psycopg prepared statements and validate the supported configuration before use.

The Phase 06 catalog connection succeeded. No migration, DDL, DML, application initialization, backend test fixture, storage operation, or application-row query was run. The read-only transaction was rolled back; no cloud or local application data was changed.

## 2. Project structure and files reviewed

| Area | Relevant files | Findings |
|---|---|---|
| Backend | `backend/app/main.py`, `backend/app/config.py`, `backend/app/database.py` | FastAPI; Pydantic settings; SQLAlchemy ORM/session; local SQLite bootstrap and PostgreSQL schema checks. |
| Authentication | `backend/app/routers/auth.py`, `backend/app/utils/security.py` | Backend-managed JWT (HS256); password hashing with PBKDF2-HMAC-SHA256; not Supabase Auth. |
| Storage and uploads | `backend/app/services/supabase_service.py`, `backend/app/routers/images.py`, `backend/app/utils/validation.py` | Supabase Storage REST integration plus local fallback; image upload endpoint; validation of filename, extension, MIME type, image integrity and dimensions. |
| Schema and migrations | `supabase/migrations/001_initial_schema.sql`, `supabase/migrations/002_align_existing_schema.sql` | Two SQL migration files. Earlier Phase 05A column-name/count parity was not a full type/default/constraint parity audit; Section 16 supersedes it. |
| Inspection utility | `inspect_supabase_readonly.py` | Read-only inspection helper exists. It was reviewed but not executed because no cloud access was authorized in Phase 05A. |
| Tests | `backend/tests/conftest.py`, `backend/tests/test_database_bootstrap.py`, other `backend/tests/test_*.py` | Session-scoped test fixture creates tables, seeds demo data, then drops tables and removes a local test DB. Full tests were intentionally not run. |
| Frontend | `frontend/src/`, `frontend/package.json`, `frontend/tsconfig.json` | React/Vite frontend; production build script exists. Frontend TypeScript no-emit check passed. |
| Configuration/docs | `.env`, `.env.example`, `.gitignore`, `README.md`, `backend/requirements.txt` | `.env` is ignored; example defaults to SQLite; README documents optional Supabase PostgreSQL/Storage setup. `.env` contents are not printed. |

No `alembic.ini`, Alembic migration directory, package lock file, or frontend dependency lockfile was found in the inspected project paths. No repository metadata was available to verify whether ignored/generated files are tracked elsewhere.

## 3. Sanitized target verification

| Check | Result |
|---|---|
| Root `.env` presence | Verified present. |
| `DATABASE_URL` | Present and non-empty; provider/host classifies as Supabase PostgreSQL pooler. SQLAlchemy driver configured as `postgresql+psycopg`. Port is 6543 (transaction pooler). Values and identifiers omitted. |
| `SUPABASE_URL` | Present and non-empty; host classifies as Supabase API endpoint (`https://[REDACTED].supabase.co`). Value omitted. |
| Database/API project relationship | **VERIFIED CORRELATED.** Tenant reference extracted from `DATABASE_URL` user component matches character-for-character the subdomain of `SUPABASE_URL`. Both endpoints definitively target the same Supabase project. |
| `SUPABASE_ANON_KEY` | Present and non-empty, using the modern publishable API-key format (not a JWT). Format alone is not a failure; Section 15 explains the raw client's separate API-key and bearer-token use and why compatibility is unverified. |
| `SUPABASE_SERVICE_ROLE_KEY` | Present and non-empty, using the modern secret API-key format (not a JWT). Format alone is not a failure; Section 15 explains the raw client's separate API-key and bearer-token use and why compatibility is unverified. |
| `SECRET_KEY` | Present and non-empty; application JWT signing secret. |
| `GEMINI_API_KEY` and `CORS_ORIGINS` | Present and non-empty. Values are not reported. |
| Dedicated LUXE.TECH project identity | **UNCONFIRMED.** Endpoints are correlated to the same project, but the user must confirm that this is the new dedicated LUXE.TECH project. |
| Remote catalog inspection | **Not performed.** Strict local-only verification adhered to; no remote connection attempted. |

### Required local configuration action

Confirm that the already-correlated project is the **new, separate Supabase project dedicated to LUXE.TECH**. Do not paste credentials into chat, commit them, or reuse the previously audited project. Pooler recommendations are in Section 15; do not change `.env` until the owner approves a chosen supported connection type.

Before any remote catalog inspection, verify the new project identity through a safe, non-secret confirmation method, then use a read-only database role/transaction. Do not use this report as approval to execute migrations.

## 4. Expected LUXE.TECH schema inventory

This inventory is derived from `backend/app/database.py`, migration 001, and the README. It describes the **expected local schema only**; no live LUXE.TECH schema was inspected.

| Table | ORM/database columns | Relationships and notable constraints |
|---|---|---|
| `users` | `id`, `email`, `name`, `password_hash`, `role`, `created_at`, `updated_at` | Primary key; unique/indexed email. Password hash may be NULL. |
| `trends` | `id`, `slug`, `name`, `category`, `season`, `description`, `image_url`, `status`, `confidence`, `momentum`, `velocity`, `acceleration`, `data_status`, `created_at`, `updated_at` | Primary key; unique/indexed slug; indexed category. |
| `trend_signals` | `id`, `trend_id`, `source`, `signal_type`, `strength`, `direction`, `timestamp`, `metadata_json`, `data_status` | Required FK to `trends` with cascade delete; indexed trend FK; migration checks allowed `source`. |
| `trend_dna` | `id`, `trend_id`, `colors_json`, `materials_json`, `textures_json`, `silhouettes_json`, `patterns_json`, `visual_description`, `ai_interpretation`, `data_status`, `created_at` | Required, unique FK to `trends`, cascade delete. |
| `images` | `id`, `trend_id`, `storage_path`, `public_url`, `width`, `height`, `dominant_colors_json`, `contrast`, `brightness`, `saturation`, `edge_density`, `data_status`, `created_at` | Nullable trend FK with `ON DELETE SET NULL`; indexed FK. |
| `collections` | `id`, `trend_id`, `name`, `description`, `color_palette_json`, `materials_json`, `textures_json`, `silhouettes_json`, `patterns_json`, `product_opportunities_json`, `data_status`, `created_at` | Required trend FK with cascade delete; ORM declares an index on `trend_id`. |
| `products` | `id`, `trend_id`, `name`, `category`, `description`, `material`, `silhouette`, `color`, `target_consumer`, `opportunity_score`, `ai_reasoning`, `data_status`, `created_at` | Nullable trend FK with `ON DELETE SET NULL`; indexed FK. |
| `retail_signals` | `id`, `trend_id`, `region`, `category`, `demand`, `growth`, `consumer_signal`, `timestamp`, `data_status` | Nullable trend FK with `ON DELETE SET NULL`; indexed FK. |
| `forecasts` | `id`, `trend_id`, `model`, `horizon`, `forecast_value`, database column `confidence`, `training_start`, `training_end`, `data_status`, `created_at` | Required trend FK with cascade delete; indexed FK; migration checks allowed model values. ORM attribute `backtest_accuracy` maps to DB column `confidence`. |
| `prophecy` | `id`, `trend_id`, `stage`, `forecast`, `evidence_json`, `opportunity`, `risk`, `confidence`, `data_status`, `created_at` | Required trend FK with cascade delete; indexed FK; migration checks allowed stage values. |
| `saved_trends` | `id`, `user_id`, `trend_id`, `created_at` | Required user/trend FKs with cascade delete; unique `(user_id, trend_id)`; both FKs indexed. |

## 5. ORM-versus-migration discrepancy table

The following are differences **verified by comparing local source files**, not live database mismatches. The canonical schema has not been selected.

| Concern | ORM in `backend/app/database.py` | Migration source | Impact / proposed resolution |
|---|---|---|---|
| String columns | SQLAlchemy `String` (unbounded `VARCHAR` on PostgreSQL); IDs generated in Python | Mostly `TEXT`; IDs default to `uuid_generate_v4()::text` | Choose one canonical PostgreSQL representation and ID-generation contract. No explicit string lengths currently constrain storage. |
| Floating-point scores | SQLAlchemy `Float` (PostgreSQL floating-point/double precision) | `NUMERIC(p,s)`, including `NUMERIC(5,2)` and `NUMERIC(6,3)` | Numeric rounding/precision differs from floating point. Confirm API precision/range requirements, then align both sides consistently. |
| Text values | SQLAlchemy `Text` | Generally `TEXT` | Generally aligned. |
| JSON serialization | JSON-like fields are `Text`, stored as serialized strings | Migration 001 uses `TEXT`; migration 002 renames legacy names and casts legacy `json`/`jsonb` to `TEXT` | Text JSON is compatible with current Python serialization but loses database JSON validation/operators. Decide whether to keep text or migrate the ORM to JSONB before creating a new canonical migration. |
| JSON field nullability/defaults | JSON text columns generally nullable with Python-side defaults such as `"[]"` or `"{}"` | Migration declares them `NOT NULL` with SQL server defaults | Direct SQL inserts and ORM inserts may behave differently. Align nullable rules and server defaults explicitly. |
| Timestamp nullability/defaults | `DateTime(timezone=True)` usually nullable unless specified; defaults are Python `now_utc`; `updated_at` uses ORM `onupdate` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` for creation/update timestamps | Database-side inserts do not get ORM Python defaults; nullability differs. Decide which timestamps require server defaults and whether database triggers are needed for update timestamps. |
| Unique/index definitions | `unique=True` and `index=True` are used on email/slug, plus indexes on selected FKs | Unique constraints create indexes; migration separately creates named indexes | Some indexes are redundant, notably unique `email`/`slug` plus explicit non-unique indexes. Review query plans/intent and remove redundancy in a new migration design only after baseline checks. |
| Collection lookup index | ORM declares `index=True` on `Collection.trend_id` | Migration 001 does not create a `collections(trend_id)` index | Add to the canonical schema plan if collection-by-trend access remains frequent; verify expected query load. |
| Check constraints | ORM has no `CheckConstraint` for enumerated source/model/stage values | Migration adds checks for `trend_signals.source`, `forecasts.model`, and `prophecy.stage` | Keep checks and model-level validation aligned so ORM writes fail with clear validation rather than database-only errors. |
| Foreign keys and cascade behavior | Relationships use explicit FK targets and `ondelete`; `trend_dna.trend_id` unique | Migration declares matching cascade/`SET NULL` behavior | Mostly aligned. Validate deletion semantics and SQLite FK enforcement separately; SQLAlchemy ORM cascades are not equivalent to DB cascade configuration in every path. |
| Saved-trend indexes/uniqueness | `SavedTrend.user_id` and `trend_id` indexed; both required; unique pair is not visible as explicit ORM table constraint in the inspected class | Migration adds both indexes and `UNIQUE(user_id, trend_id)` | Migration uniqueness needs a corresponding ORM `UniqueConstraint` or equivalent so metadata and migration source agree. |
| RLS | Not represented in SQLAlchemy metadata | Enables RLS on all 11 tables; public read policies for nine intelligence tables; no policy for `users`/`saved_trends`; grants SELECT to `anon` and `authenticated` for nine tables | Database security is migration-only. Define policy/privilege expectations as reviewed migration source and test them on the dedicated project. |
| Storage buckets | No SQLAlchemy model for Storage buckets/objects | Migration inserts `trend-images` public, `user-uploads` private, and `collections` public | Bucket visibility is a product/security decision and requires confirmation. The migration’s bucket inserts are writes and were not executed. |
| Migration tracking | No SQLAlchemy migration tracking | Two manually named SQL files; no local Alembic configuration/history implementation found | Establish a single migration runner and an auditable baseline/history policy before applying schema. Never infer applied versions from files alone. |

Migration 002 may rename legacy JSON column names, convert `json`/`jsonb` values to text, and set selected foreign-key columns `NOT NULL` when there are no NULL rows. It raises on duplicate old/new columns or NULLs before tightening nullability. It is not a harmless inspection script and must not be run before reviewing the actual dedicated target and data.

## 6. Authentication, RLS, grants, and storage security

### Authentication and ownership

- The application implements its own account system in `users`; credentials are hashed with PBKDF2-HMAC-SHA256 and the backend issues seven-day HS256 JWTs. This is **custom JWT authentication**, not Supabase Auth.
- `auth.uid()` in Supabase policies is populated from a Supabase-recognized JWT, not automatically from this application’s custom JWT. Do not rely on Supabase RLS policies using `auth.uid()` to authorize custom-JWT users unless an explicit, verified identity bridge is implemented.
- Only `/auth/me`, `/trends/saved`, and trend-save routes visibly depend on `get_current_user`. Several state-changing routes—including trend, collection, product, forecast, prophecy, and image operations—do not visibly require authentication. Confirm whether these are intended to be public, admin-only, or user-owned before production.
- Trends and derived intelligence currently appear platform-wide; `images` and `collections` have no owner column. `saved_trends` has `user_id`. Decide which generated resources are global, privately owned, or shared before defining RLS.
- The connection role configured in `.env` was not inspected or connected to. On production, use a narrowly privileged runtime role distinct from migration/admin credentials. Avoid running the app as a superuser, table owner with unintended RLS bypass, or `BYPASSRLS` role. Define whether backend operations intentionally bypass RLS and enforce authorization in the backend if so.

### Existing migration RLS/grant design (local source only)

- RLS is enabled on all 11 application tables.
- Nine intelligence tables (`trends`, `trend_signals`, `trend_dna`, `images`, `collections`, `products`, `retail_signals`, `forecasts`, `prophecy`) receive `SELECT USING (true)` policies and `SELECT` grants to `anon` and `authenticated`.
- `users` and `saved_trends` are RLS-enabled but have no policies or public/authenticated grants in migration 001. Direct backend access depends on the database role and its RLS-bypass/table-owner properties; this must be designed, not assumed.
- These broad reads are appropriate only for fields/data approved as public. Consider public views or restricted-column API projections if user/private or internal fields are later added.
- No live policies, effective grants, or RLS state were inspected for the dedicated project.

### Storage, upload validation, and public access

- The local migration assumes public `trend-images` and `collections`, and private `user-uploads`. Public access is a product decision; confirm that uploaded imagery and moodboards are intentionally public and contain no private content.
- The image route currently uploads to `trend-images`. `PUBLIC_BUCKETS` includes `trend-images` and `collections`; private objects use signed URLs for one hour. `user-uploads` has no observed application upload call site in the inspected code.
- Image validation checks extension, supplied MIME type, Pillow integrity, and dimensions. It reads the entire upload into memory before enforcing the 10 MB size cap, so request-body/memory limits should also be enforced at the ASGI/proxy layer and preferably during streaming.
- Upload endpoints do not visibly require authentication or ownership. If objects are user-specific, use private buckets, generated non-guessable object paths, ownership checks, and signed reads. If platform-wide public imagery is intended, keep the public bucket content limited to approved material.
- No storage bucket state or storage policies were inspected remotely.

### Secrets, CORS, rate limiting, and errors

- `.gitignore` excludes `.env` and `.env.*`, while allowing `.env.example`; the report does not contain secret values. Keep service-role credentials and database credentials backend-only.
- `CORS_ORIGINS` is configured locally, but its values were not reported. Source code falls back to `"*"` if it is empty, while allowing credentials, all methods, and all headers. Require a validated production origin allowlist and avoid wildcard fallback in production.
- No rate-limiting implementation was found in the inspected backend source. Add rate limits and abuse controls to public/authenticated write and upload endpoints before public deployment.
- Generic API responses avoid returning exception detail, but the generic exception handler logs the exception and traceback. Review production log redaction and ensure DSNs, tokens, request bodies, and user data cannot enter logs.
- Image path validation is present for local-file serving; still verify that object paths are generated server-side and authorization is enforced for private content.

## 7. Environment configuration status

The following describes only local presence/emptiness and sanitized provider classification. No variable values are included.

| Variable | Status |
|---|---|
| `DATABASE_URL` | Present, non-empty; Supabase PostgreSQL provider/host class; dedicated project identity UNVERIFIED. |
| `SUPABASE_URL` | Present, non-empty; Supabase provider/host class; project relationship to database endpoint UNVERIFIED. |
| `SUPABASE_ANON_KEY` | Present, non-empty; validity not tested. |
| `SUPABASE_SERVICE_ROLE_KEY` | Present, non-empty; validity not tested. |
| `SECRET_KEY` | Present, non-empty; strength/rotation policy not assessed. |
| `GEMINI_API_KEY` | Present, non-empty; validity not tested. |
| `CORS_ORIGINS` | Present, non-empty; origins intentionally not printed or audited individually. |

The `.env.example` file uses a local SQLite `DATABASE_URL` and blank optional credentials. The real `.env` has a non-empty Supabase PostgreSQL setting; do not run app startup or tests until the dedicated project identity has been confirmed.

## 8. Backup and recovery prerequisites

Before any Phase 05 cloud writes:

1. Confirm the dedicated project identity and ensure no other application will share it.
2. Enable/confirm the required Supabase backup/PITR retention for the deployment plan; document retention and point-in-time recovery limits.
3. Take a pre-migration recoverable backup or snapshot and verify restoration into an isolated project. A backup that has not been restore-tested is not a validated rollback plan.
4. Separately inventory and protect any Storage objects and bucket configuration. Database backups alone may not restore object bytes or visibility settings.
5. Record a pre-change catalog-only schema/policy/grant/bucket snapshot and migration-history state. Do not store credentials or user rows in the report.
6. Agree on a maintenance window, owner, stop conditions, rollback authority, and post-restore verification procedure.
7. Decide whether any SQLite local data must be migrated. This phase did not inspect local database rows or attempt data migration.

## 9. Proposed migration sequence (not executed)

1. **Target gate:** The endpoint association was locally correlated in Phase 05A. Confirm with the owner that this correlated project is the dedicated LUXE.TECH project. Stop if that ownership is uncertain.
2. **Architecture decisions:** Confirm custom JWT versus Supabase Auth; global versus user-owned records; public read requirements; runtime DB role; public/private bucket policy; and production deployment connection mode.
3. **Canonical schema:** Resolve the ORM/migration discrepancies in Section 5. Use a single versioned migration system and define how the existing SQL files are baselined. Do not rerun or rewrite history against any pre-existing database.
4. **Backup/recovery gate:** Complete the backup and restore prerequisites in Section 8.
5. **Dedicated-project read-only baseline:** Start a transaction explicitly in read-only mode, verify `transaction_read_only`, and only then read catalog metadata: identity (sanitized), visible schemas/tables, columns/types/defaults/nullability, constraints, indexes/FKs, RLS/policies/grants, bucket metadata, and migration history if visible. Roll back. Query no application rows.
6. **Migration preflight:** Verify extension availability/permissions and check for table/column/index/policy/bucket collisions using catalog-only checks. Do not treat invisible objects as absent. Review data-dependent conditions required by migration 002 without selecting user data; if necessary, request a separately approved aggregate-only validation.
7. **Apply in dependency order after separate explicit approval:** Create/record the migration baseline; create parent tables (`users`, `trends`) before dependent tables; add dependent tables, constraints and indexes; apply reviewed JSON/name/nullability alignment only if required; then apply least-privilege grants and reviewed RLS policies. Configure Storage buckets/policies only after privacy approval.
8. **Validate in staging:** Compare catalog state to the canonical schema, test role-specific operations and `auth.uid()` behavior, inspect public API exposure, test constraints/cascades/indexes, verify Storage access and signed URLs, and run backend smoke tests against isolated staging data.
9. **Production and rollback:** Apply the tested sequence to the dedicated production project only with approval. Stop at the first unexpected catalog or data condition. Restore the pre-migration backup and Storage state if validation fails; do not rely on ad hoc reverse DDL or casts as the only rollback.
10. **Post-migration application checks:** Start the backend only after schema verification; confirm health, registration/login, saved-trend isolation, read endpoints, protected write endpoints, image upload/read behavior, forecast/collection/prophecy generation, and safe error/log output. Keep demo seeding disabled for production.

## 10. Prioritized issue list

### Critical

- **Dedicated target ownership is UNCONFIRMED.** The database and API endpoints are correlated to each other, but no remote query is safe until the owner confirms this is the dedicated LUXE.TECH project. Never point migrations at the previously audited project.

### High

- **ORM/migration drift:** float versus numeric, varchar versus text, Python-only versus server defaults, nullable JSON/timestamp fields, model/migration check constraints, collection index, and saved-trend unique metadata need a canonical decision.
- **Authentication/RLS mismatch:** custom JWTs do not populate Supabase `auth.uid()`. Existing migrations do not define authenticated ownership policies for `users` or `saved_trends`.
- **Unauthenticated writes:** multiple FastAPI mutation/generation routes do not visibly enforce authentication or role/ownership checks. Define intended access and enforce it before production.
- **Connection-role design unknown:** the configured runtime DB role and its RLS bypass/ownership properties have not been inspected. Use least-privilege runtime credentials, separate from migration/admin credentials.
- **Migration safety/history:** hand-run SQL has no established migration ledger/runner; migration 001 includes DDL, grants, and bucket inserts, while migration 002 can change column names/types/nullability. No rollback has been tested.

### Medium

- **Public data and buckets need approval:** migration 001 proposes public reads for nine intelligence tables and public `trend-images`/`collections` buckets. Restrict returned columns/data if any content is private.
- **Upload resource exposure:** upload endpoint lacks visible authentication/rate limiting and reads the whole request before applying its size cap.
- **Operational abuse controls:** no rate limiter was found; CORS includes wildcard methods/headers and a wildcard origin fallback for empty configuration.
- **Local/test database handling:** the pytest fixture creates schema, seeds data, drops schema, and deletes its test database. Keep it out of production or shared DB test runs.

### Low

- **Index redundancy/omission:** unique email/slug indexes may be duplicated by explicit indexes; the ORM collection index is absent from migration 001. Reconcile against expected query plans.
- **Production log hygiene:** review exception traceback/log redaction and ensure secrets/PII are not emitted.

## 11. Proposed Phase 05 changes (not performed)

1. Add an explicit deployment configuration check that refuses production startup unless the database and Supabase Storage endpoints are confirmed to belong to the same dedicated project. Do not log DSNs or project credentials.
2. Select and document one canonical migration source/runner; baseline existing SQL history explicitly and introduce a repeatable, reviewable migration validation workflow.
3. Align SQLAlchemy types, nullability, server defaults, checks, unique constraints, indexes, JSON representation, and timestamp behavior with the canonical schema.
4. Define whether authentication remains custom JWT or moves to Supabase Auth. If custom JWT remains, enforce authorization in FastAPI and do not rely on `auth.uid()` RLS predicates for those tokens.
5. Add endpoint authorization, per-user ownership, and role checks for state-changing routes; define global/system-managed records versus user-owned records.
6. Use a least-privilege runtime database role and reserve migration/admin privileges for controlled deployment. Explicitly test RLS under actual application and Supabase API roles.
7. Confirm public data fields and bucket visibility. Keep private uploads private, create object-path ownership rules where applicable, enforce streaming/body limits, and rate-limit uploads.
8. Tighten production CORS, health/status disclosure, request validation, and log redaction; preserve generic client errors without suppressing actionable server-side diagnostics.
9. Add safe CI checks for migration/schema parity, policy/grant expectations, authorization tests, storage visibility, and an isolated staging migration/restore drill.

## 12. Commands and checks actually run

### Passed

- Inspected project files using bounded file reads and source searches. No application startup, database engine connection, migration, or table-row query was invoked.
- Sanitized PowerShell inspection of `.env` in Phase 05A: confirmed variable presence/emptiness and provider classification without printing values; a sanitized project-reference comparison established that the database and API endpoints are correlated to the same project. Dedicated-project ownership remains pending user confirmation.
- Checked local dependencies and tooling: frontend `node_modules` and Vite executable exist; Node and npm are available.
- Frontend no-emit type check:  
  `Set-Location 'C:\Users\Lenovo\Downloads\FORCASTING WEBSITE\frontend'; .\node_modules\.bin\tsc.cmd --noEmit -p .\tsconfig.json`  
  **PASS**. This did not run a production build or emit build output.
- Pylance Python syntax checks: `backend/app/database.py`, `backend/app/config.py`, `backend/app/main.py`, `backend/app/services/supabase_service.py`, `backend/app/utils/security.py`, and `inspect_supabase_readonly.py` — **no syntax errors found**.

### Failed/limited checks

- First sanitized host-classification PowerShell attempt failed because it assigned to PowerShell’s reserved, read-only `$Host` variable. No secret or endpoint value was printed. The corrected check completed.
- The initial Phase 04 host-only classification could not verify endpoint association. Phase 05A subsequently established the database/API endpoint correlation using a sanitized tenant-reference comparison; dedicated-project ownership remains unconfirmed.
- No pytest command was run: `backend/tests/conftest.py` performs `create_all`, demo seeding, `drop_all`, and local test DB file removal in its session fixture. This is unsafe under the no-database-mutation constraint without separate isolation proof.
- No backend imports, startup, frontend production build, migration helper execution, SQL, Supabase API request, or database catalog query was run.

## 13. Unresolved items and Phase 05 approval gate

- **VERIFIED CORRELATED:** Database/API endpoint association. **UNCONFIRMED:** Whether the correlated project is dedicated to LUXE.TECH.
- **UNVERIFIED:** Live LUXE.TECH catalog, migration history, database role, RLS state, grants, policies, constraints, indexes, and bucket state.
- **UNVERIFIED:** Backup/PITR availability and tested restoration.
- **UNVERIFIED:** Whether local SQLite data needs migration.
- **Needs owner decision:** Custom JWT versus Supabase Auth; ownership of generated resources; which trend/intelligence data is public; public versus private bucket contents; and intended public write operations.
- **Needs engineering decision:** Canonical ORM/migration types, defaults/nullability, checks, index set, migration runner, and production runtime role.

**Exact action required before a remote baseline:** Confirm that the already-correlated project is the dedicated LUXE.TECH project. Then resolve the Phase 05B client/API-key compatibility and explicitly approve read-only metadata verification. Migration execution still requires separate approval after backup/recovery and schema/security decisions are complete.

**Phase 04 made no cloud changes and no application-data changes.** It created only this local report.

---

## 14. Phase 05B Supabase Client Compatibility Audit

**Scope:** Read local source and installed package metadata only. No `.env` values were displayed, no network requests were made, and no database or Supabase API was contacted.

### SDK and actual request implementation

| Question | Finding |
|---|---|
| Installed Supabase Python SDK version | **Not installed in the inspected project environments.** Neither `backend/requirements.txt` nor either project virtual environment contains the Supabase Python package. There is no installed SDK version to report. |
| Client initialization | **No Supabase SDK client is initialized.** `backend/app/services/supabase_service.py` creates raw `httpx.AsyncClient` instances per request and directly calls Supabase Storage and PostgREST REST endpoints. |
| Variables actually read by the service | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY`, loaded through `app.config.Settings`. `DATABASE_URL` is separately read by SQLAlchemy in `backend/app/database.py`. |
| Key use | `active_key` prefers `SUPABASE_SERVICE_ROLE_KEY` and falls back to `SUPABASE_ANON_KEY`. Requests set `apikey` to a selected key and also construct an `Authorization: Bearer <same key>` header. Storage uploads and inserts prefer the service key; the select path passes `use_service_role=False` but still uses `active_key`, so it also uses the service key whenever configured. |
| Frontend exposure | No references to `SUPABASE_SERVICE_ROLE_KEY` or the backend Supabase key variables were found under `frontend/src`. The secret key is used by backend service code only in the inspected source. Keep it out of frontend/build-time variables and browser responses. |

### Publishable/secret key compatibility and JWT requirement

- The configured publishable (`sb_publish...`) and secret (`sb_secret_...`) formats are modern API-key formats, not JWTs. Their format alone does **not** prove that a Supabase SDK would reject them; no SDK is installed or used here.
- This raw HTTP implementation sends each active API key in the `apikey` header, which is the API-key use case. It also sends that same non-JWT value as a bearer token. A publishable/secret API key is not a JWT and must not be assumed to satisfy an endpoint's `Authorization: Bearer <JWT>` requirement.
- Consequently, compatibility is **not verified as written**. Whether a request succeeds without a JWT, or with a separately supplied user JWT, depends on the endpoint and gateway authorization model. This audit deliberately made no API request.
- A legacy `anon`/`service_role` JWT is **not established as generally required** merely because the application uses Supabase. If an endpoint flow specifically requires a JWT bearer token, provide the appropriate user access token or use a supported server-side service-auth pattern; do not force a publishable/secret key into JWT semantics. If the chosen HTTP flow cannot use the new key model safely, select a compatible supported integration before remote inspection.

### Database driver and pool-mode recommendations

- `backend/requirements.txt` declares `psycopg[binary]`; `backend/app/database.py` passes `DATABASE_URL` to SQLAlchemy `create_engine()` with no PostgreSQL-specific pool or psycopg options.
- Phase 05A locally identified the configured connection as a transaction pooler. That mode is not automatically unusable with SQLAlchemy, but psycopg prepared-statement behavior and transaction-pooler compatibility must be addressed. If retaining it for app runtime, configure psycopg's `prepare_threshold` to `None` through SQLAlchemy `connect_args` (or a verified equivalent) and test this exact setup against staging.
- Prefer a Supabase direct connection or session pooler for schema migrations and DDL. Select the Supabase-provided connection type that matches the deployment's network/IPv4 requirements; do not alter `.env` until the owner approves the selected connection.

### Corrective actions before a read-only baseline

1. Confirm with the owner that the Phase 05A-correlated project is the dedicated LUXE.TECH project. Endpoint correlation proves that both configured endpoints target the same project, not that the project is dedicated.
2. Revise the raw HTTP wrapper so `apikey` contains the configured publishable or secret API key, and `Authorization` carries only a valid Supabase user JWT when the requested operation needs user identity. For privileged server operations, use a supported secret-key flow and keep the secret key backend-only. Do not silently fall back from a secret key to a lower-privilege key for writes without an explicit behavior decision.
3. Add safe tests with mocked HTTPX transport asserting header/role behavior and proving secret-key values never enter frontend bundles, logs, or client responses. Do not print test values.
4. Choose direct/session connectivity for migration work. If runtime SQLAlchemy retains transaction pooling, explicitly disable psycopg prepared statements and verify in an approved isolated staging check.
5. After ownership confirmation and correction/local verification of API header handling, separately request approval for a read-only baseline. Until then, **not ready for remote baseline inspection**.

### Safe checks run in Phase 05B

- Read `supabase_service.py`, `config.py`, `database.py`, auth/security modules, storage route, and `backend/requirements.txt`.
- Inspected only package-directory names in the root and backend virtual environments; no Supabase SDK package was found.
- Searched `frontend/src` for backend Supabase key environment names, key-format prefixes, and SDK imports; no matches.
- Checked the service source for SDK construction and HTTPX usage; found HTTPX and no SDK factory/import.
- No `.env` values were read or printed during these checks. No runtime tests were run; all remote/network/database activity was skipped.

**Phase 05B conclusion:** Configuration compatibility is **not verified** because the current wrapper uses non-JWT API keys both as API keys and bearer tokens. The project is **not ready for a read-only database baseline inspection** until dedicated-project ownership is confirmed and API header handling is corrected and locally tested.

---

## 16. Phase 06 Read-Only Supabase Schema Baseline

**Date:** 2026-10-10  
**Scope:** Confirmed dedicated LUXE.TECH project; local endpoint-correlation check plus PostgreSQL catalog metadata only.

### Safety and target verification

- The API URL and database URL project references matched locally; the user confirmed this is the dedicated LUXE.TECH project.
- The audit connected using psycopg and started `BEGIN READ ONLY`. PostgreSQL reported `transaction_read_only=on`. The transaction was rolled back.
- The audit role was not a superuser, had `BYPASSRLS`, and had `SELECT` table privilege on both `storage.buckets` and `storage.objects`. Identity values were suppressed.
- The configured database URL uses generic `postgresql` driver spelling; the audit helper explicitly used installed psycopg v3. No application connection test was performed.
- No application rows, storage-object rows, or bucket row payloads beyond `id`, `name`, and `public` metadata were queried. No SQL migration, DDL, DML, policy change, bucket change, or other remote write was executed.

### Visible objects and missing application schema

The visible non-system tables were `storage.buckets` and `storage.objects`. **None of the 11 expected LUXE.TECH application tables were visible in `public`**: `users`, `trends`, `trend_signals`, `trend_dna`, `images`, `collections`, `products`, `retail_signals`, `forecasts`, `prophecy`, and `saved_trends`. The startup error independently reports all 11 as missing. Catalog visibility remains the limitation: report these as not visible, not as universally confirmed absent.

No known `public.alembic_version`, `public.schema_migrations`, or `supabase_migrations.schema_migrations` table was visible. This does **not** prove that no migration history exists elsewhere or that migration 001 has never been applied.

No storage bucket rows were returned. Since the audit role had `BYPASSRLS` and `SELECT` on `storage.buckets`, this indicates no bucket metadata rows were present/visible through that table at audit time; no object data was queried.

### Catalog findings for Supabase Storage

- `storage.buckets` and `storage.objects` both have RLS enabled; `FORCE ROW LEVEL SECURITY` was false for each.
- No `public` or `storage` policy rows were visible to the audit query.
- `anon`, `authenticated`, and `service_role` have table-level privileges listed for both storage relations, including `SELECT` and write privileges. Those grants alone do not establish effective row access: RLS is enabled, and no policies were visible. The migration proposal itself adds no `storage.objects` policies.
- The standard Storage table columns, constraints, and indexes were visible. UUID extension `uuid-ossp` is installed. No non-internal triggers were visible on the application tables.
- Bucket metadata fields include public visibility, file size limits, and allowed MIME types. No bucket row was present to compare against the three bucket names/visibility assumptions in migration 001.

### Application migration/model comparison

| Item | Baseline result |
|---|---|
| Tables and columns | No application table columns were visible; therefore no live type/default/nullability/constraint comparison could be made. |
| Migration 001 | Source declares all 11 tables, their foreign keys/unique/check constraints, indexes, RLS, nine public-read policies and read grants, and three bucket inserts. It also requires `uuid-ossp`, confirmed installed. |
| Migration 002 | No target application table was visible for its JSON-column rename/type conversion or foreign-key nullability adjustments. Do not run it as a fresh-schema migration. |
| Models versus migration | Local source differences remain: SQLAlchemy `Float` vs SQL `NUMERIC`, `String` vs `TEXT`, ORM-side defaults/nullable declarations vs SQL server defaults/`NOT NULL`, migration-only check constraints, the ORM collection index missing from migration 001, and migration-only unique `(user_id, trend_id)`. Resolve these before applying the initial schema. |
| RLS and grants | No app policies/grants could be compared live because no app tables were visible. Storage is RLS-enabled and has listed role grants but no visible policies; public/private object access is not established by grants alone. |

### Readiness and recommended next steps

**Current app schema is not compatible with startup:** all 11 required application tables were reported missing and none were visible in the public catalog. The database baseline suggests an initial application-schema deployment, but does not prove the project is empty outside the metadata observed.

1. Resolve the canonical ORM/migration discrepancies and decide public-read policy and bucket privacy. Do not apply migration 001 unchanged until this review is complete.
2. Preserve the baseline and confirm backup/recovery expectations, even though no application tables or bucket metadata rows were visible.
3. Review the privilege implications of migration 001’s RLS changes, grants, public-read policies, and bucket inserts. The existing storage grants and absence of visible policies require particular care.
4. If the catalog is reconfirmed and the reviewed schema source is approved, prepare a versioned fresh-install migration based on the selected canonical schema. Migration 002 is for legacy schema alignment and is not indicated for this baseline.
5. Obtain explicit approval before any remote migration, policy/grant update, or bucket configuration write.

### Execution note

The first helper invocation stopped before connecting because the URL used generic `postgresql` spelling rather than the helper’s former strict `postgresql+psycopg` spelling. The helper was adjusted to accept PostgreSQL URL spellings while performing the catalog connection explicitly via psycopg; the successful read-only run followed. Syntax validation passed after the helper changes.

**Phase 06 made no Supabase changes and no data changes.** Historical Phase 04–05 status text above is superseded by this completed baseline for live schema status; Phase 05B client-authentication concerns remain unresolved.

---

## Phase 05A Historical Verification Record

This is the original Phase 05A snapshot. Where its key-format or pooler recommendations differ, the Phase 05B findings above supersede them.

**Date of Verification:** 2026-10-10  
**Verification Scope:** Strictly local inspection of `.env`, SQLAlchemy metadata, and migration files. Zero cloud connections, zero SQL executions, zero database writes.

### Summary of Results

| Check Item | Result | Evidence / Details |
|---|---|---|
| **`DATABASE_URL` Presence & Structure** | **PASS** | Present, non-empty, configured with `postgresql+psycopg`, host type is Supabase pooler (`aws-0-[REDACTED].pooler.supabase.com`), port 6543, sslmode=require. |
| **`SUPABASE_URL` Presence & Structure** | **PASS** | Present, non-empty, host type is Supabase API (`https://[REDACTED].supabase.co`). |
| **Endpoint Association (Same Project Check)** | **PASS** | Safe tenant extraction from `DATABASE_URL` username (`postgres.[REDACTED]`) matches character-for-character the subdomain of `SUPABASE_URL`. Both endpoints unequivocally refer to the same Supabase project reference. |
| **Dedicated Project Identity Confirmation** | **PENDING USER CONFIRMATION** | Local evidence confirms both endpoints point to the same target project. User confirmation is requested to verify this project reference corresponds to the newly prepared LUXE.TECH organization/project and not a pre-existing project. |
| **`SUPABASE_ANON_KEY` Format** | **Phase 05B: format alone is not a failure.** Configured as a modern publishable API key, not a JWT. The code also uses it as a bearer token; that Authorization use is not established as compatible and requires correction/verification. |
| **`SUPABASE_SERVICE_ROLE_KEY` Format** | **Phase 05B: format alone is not a failure.** Configured as a modern secret API key, not a JWT. The code also uses it as a bearer token; that Authorization use is not established as compatible and requires correction/verification. |
| **`DATABASE_URL` Pooler Mode** | **ADVISORY** | Phase 05A identified transaction-pooler mode. SQLAlchemy currently uses default psycopg settings. Use direct/session pooling for migration and DDL. If application traffic must use transaction pooling, disable psycopg prepared statements and validate that configuration. |
| **SQLAlchemy vs Migration 001 column inventory** | **Historical, limited check** | The recorded 11-table column-count check did not compare types, nullability, defaults, constraints, indexes, or FK behavior; it must not be read as full schema parity. See Section 16 for the reviewed model-to-proposal parity result. |
| **Safety Invariants Maintained** | **PASS** | No cloud connection attempted, no SQL executed, no tables created, no rows queried or modified, no secrets or project references printed. |

### Pre-Flight Checklist Before Cloud Execution (Phase 05B)

1. **Fix and validate API Authorization semantics:** Keep modern publishable/secret keys in their intended API-key configuration; do not treat them as JWTs. Update the REST wrapper so API-key authentication and any optional Supabase-user JWT authorization are handled separately. For privileged server operations, use a supported Supabase authentication path and keep the secret key confined to the backend. Verify behavior in isolated staging before production.
2. **Review pooler mode:** Use direct or session-pooler connectivity for migrations/DDL. For a transaction pooler used by runtime SQLAlchemy, configure psycopg with prepared statements disabled and validate connection behavior; do not blindly change the local URL.
3. **User Confirmation:** Confirm that the correlated project belongs to the new dedicated LUXE.TECH organization/project.
4. **Read-Only Baseline Inspection:** After API configuration is corrected and the dedicated-project identity is confirmed, obtain explicit approval for the separate read-only catalog baseline. Do not infer that the database is empty or run migrations based on Phase 05A.

---

## 16. Canonical schema proposal (local only; not applied)

**Status: REVIEW PROPOSAL — no Supabase connection or database write was made.**

The Phase 06 baseline showed no LUXE.TECH application tables visible to the inspection role, but “not visible” is not proof of absence. The existing Supabase target must be re-baselined immediately before any approved execution. Neither existing migration is approved for direct application: 001 combines non-parity schema, broad public reads, grants, and bucket writes; 002 is conditional legacy alignment code that can rename/convert columns and tighten nullability. Earlier Phase 05A claims of “100% parity” were based on table/column inventory only and are superseded; they did not establish type or constraint parity.

### Canonical decisions and ORM reconciliation

The current SQLAlchemy models are the canonical application contract for this proposal because endpoint code consumes their names, Python types, and nullable behavior. A non-deployable proposal is in `supabase/proposals/luxe_canonical_initial_schema_proposal.sql`; the legacy files in `supabase/migrations/` were not edited.

| Concern | Proposal decision |
|---|---|
| Table and column inventory | Preserve all 11 ORM tables and all model column names, including `forecasts.confidence` as the physical column mapped to model attribute `backtest_accuracy`. |
| Numeric types | Use PostgreSQL `DOUBLE PRECISION` for SQLAlchemy `Float` fields. Do not retain migration 001’s `NUMERIC(p,s)` rounding/precision behavior. |
| Text and JSON | Keep SQLAlchemy `VARCHAR` for `String`, `TEXT` for `Text`; JSON-shaped values remain text-serialized JSON (`*_json`), not PostgreSQL JSON/JSONB, to preserve the application’s JSON-string parsing. |
| Nullability and timestamps | Follow ORM `nullable` settings, including nullable timestamps. Timestamp columns default to `now()` but are not made `NOT NULL`. `updated_at` gets an insert default; its update behavior remains the existing SQLAlchemy `onupdate` behavior and is not a database trigger. |
| Defaults | Add matching server defaults alongside existing SQLAlchemy client defaults for mapped defaulted columns. IDs remain generated by the Python UUID default; no extension or database ID generator is required. |
| Keys, indexes, and deletes | Preserve ORM primary/foreign keys and `CASCADE`/`SET NULL` actions, and represent ORM indexes. Add the composite `UNIQUE(user_id, trend_id)` for `saved_trends` to prevent duplicate saves during concurrent requests; the ORM metadata now declares the same constraint. |
| Migration-only checks | Do not carry forward source/model-inconsistent checks for signal source, forecast model, or prophecy stage. Current request schemas do not establish these enumerations as validated application contracts. If these domains are intended to be closed sets, validate that requirement and add matching application and model validation before adding database checks. |
| RLS and API grants | Enable RLS on all 11 tables; define no policies and grant no table privileges to `anon` or `authenticated`. This deliberately blocks direct Supabase API access until identity, public-data, and grant decisions are approved. It does not itself constrain a table owner/superuser or a role with `BYPASSRLS`. |
| Storage | The proposal creates no buckets and no `storage.objects` policies. The app currently assumes `trend-images` and `collections` are public and uses signed URLs for other buckets. Public visibility and upload ownership need an explicit decision before provisioning. |

The proposal intentionally contains plain `CREATE TABLE` statements without `IF NOT EXISTS`; it is local documentation for review, not an idempotent deployment script. It has no extension creation, grant/revoke, policies, bucket writes, inserts, or data operations. Do not move it into the migration directory or execute it without separate approval and a fresh baseline.

### Authentication, ownership, and least privilege

- The application issues its own HS256 JWTs; these tokens do not establish a Supabase `auth.uid()`. No policy may use `auth.uid()` as the identity of these users unless the authentication architecture changes or an independently verified identity bridge is designed.
- `/auth/register`, `/auth/login`, and `/auth/me` operate on `users`. Saved-trend endpoints use the authenticated custom-JWT user ID to filter `saved_trends`. The current `saved_trends` design is the only explicit per-user ownership relation in these models. Generated intelligence records otherwise have no user owner and are platform-wide/system-managed in the current model.
- Do not grant browser `anon`/`authenticated` roles access to `users` or `saved_trends`. The proposal grants neither role access to any application table. Any later direct public reads should be table- and column-scoped, explicitly approved, and paired with policies that match the chosen identity model.
- Use distinct migration-owner and runtime database roles. Runtime must not be superuser, table owner, or `BYPASSRLS`; test the actual effective grants and RLS behavior. Until this is designed, private backend SQL access must remain protected by FastAPI authorization and server-only credentials. Do not treat RLS enabled alone as proof of enforcement for an owner/bypass role.
- Treat uploads as private by default. The existing image upload path lacks an evident user ownership check, while its service can use a privileged server key. Before public buckets or client upload access, add endpoint authentication/authorization, safe per-user object paths, MIME/signature validation, body-size limits, and explicit object read/write policies. Keep privileged credentials server-only.

### Prioritized issues and unresolved decisions

| Priority | Issue | Required resolution |
|---|---|---|
| **Critical** | Database role/RLS bypass behavior is not aligned to an approved runtime-role design. | Create and test a least-privilege runtime role separate from migration ownership; verify role attributes, grants, and RLS behavior in staging. |
| **High** | Authentication is custom JWT, while direct Supabase RLS policies normally rely on Supabase identity claims. | Confirm custom JWT remains; maintain authorization in FastAPI or approve a reviewed identity bridge before any user-scoped policy. |
| **High** | `images` upload flow does not establish per-user ownership, and public bucket assumptions exist in code. | Decide image/moodboard visibility and user ownership; secure upload route and object paths before enabling upload access. |
| **High** | Current `updated_at` changes are SQLAlchemy-side only. | Decide whether all writes must use the ORM or whether a database trigger is required; a trigger would need matching metadata and tests. |
| **Medium** | Existing migration 001’s domain checks are not in ORM validation. | Confirm whether those value sets are product invariants; otherwise keep absent. |
| **Medium** | `saved_trends` uniqueness tightens behavior by disallowing duplicate rows. | Confirm duplicates have no intended meaning; current toggle endpoint treats a pair as a single saved item. |
| **Medium** | Storage bucket visibility and row policies are unknown/unverified from the baseline. | Approve public/private behavior and object-level access design per bucket; no bucket is provisioned by this proposal. |
| **Medium** | Existing live target object visibility and migration history remain incomplete. | Re-run catalog baseline with a sufficiently scoped read-only role immediately before execution; do not infer empty schema or absent migration history. |
| **Low** | No migration runner or history ledger has been selected. | Choose a controlled migration mechanism and record applied version/checksum after a separately approved rollout. |

### Proposed ordered execution plan (not executed)

1. Confirm the dedicated target and connection mode locally; keep secrets out of reports. Decide role model, custom-JWT ownership strategy, global intelligence visibility, storage visibility, and the saved-item uniqueness behavior.
2. Take a provider-supported backup/snapshot, verify retention/PITR settings, and test a restore to an isolated target. Record recovery owner and acceptable recovery point/time.
3. Re-run a read-only baseline using a role that can inspect required catalog metadata. Compare all visible objects, policies, grants, bucket metadata, and migration history with this proposal. Stop on any collision or unexplained object; `NOT VISIBLE` is not absence.
4. Review and approve the canonical model/SQL parity output and security decisions. Update migration proposal if decisions alter model/schema contract. Do not apply legacy migration 002 to a fresh target.
5. Prepare a separately reviewed migration deployment artifact that refuses unexpected existing tables; apply schema in dependency order: `users`, `trends`, then trend-dependent tables (`trend_signals`, `trend_dna`, `images`, `collections`, `products`, `retail_signals`, `forecasts`, `prophecy`), then `saved_trends`; add indexes/constraints and then reviewed roles, grants, policies, and storage configuration.
6. Validate catalog parity and effective grants/RLS using both migration and runtime roles; test expected-deny and expected-allow cases. Restore backup to a separate target for rollback rather than dropping live objects. Do not attempt automatic destructive rollback on production.
7. Run backend auth, ownership, and CRUD API tests against isolated staging; test private/public storage access, upload rejection paths, database connection pool mode, and read-only/public endpoints. Run no fixture that can seed/drop a production database.

### Local parity validation and checks

Added `backend/scripts/validate_schema_proposal.py`. It forces an in-memory SQLite URL before importing model metadata, does not open a connection or call initialization, and checks tables/columns, PostgreSQL type compatibility, nullability, server defaults, primary/foreign keys, delete actions, unique behavior, indexes, and RLS table coverage. It does not connect to Supabase or create a database.

The first two validator runs failed and exposed comparison-tool defects (PostgreSQL type aliases, primary-key nullability semantics, and unique-index parsing); those were corrected before final validation.

- Offline parity validator: **PASS** — 11 tables, 113 columns, 12 indexes, and RLS enabled on all 11 tables. It compared PostgreSQL type aliases, nullability, server defaults, primary/foreign keys, delete actions, uniqueness, indexes, and RLS table coverage.
- Pylance syntax checks: **PASS** for `backend/app/database.py` and `backend/scripts/validate_schema_proposal.py`.
- Pylance Problems check: **No errors** in either file. Pylance diagnostics still report pre-existing type-analysis warnings in the declarative ORM property methods in `database.py`; these were not changed in this task.
- No pytest or application startup was run; the test fixture can create/seed/drop a database. The validator did not connect to a database and no Supabase request was made.
- No Supabase or local application data was changed.

### Phase 05 proposal scope

If separately approved after the open decisions are resolved, Phase 05 should:

1. Reconcile the ORM metadata (including the documented server defaults and saved-trend uniqueness) with the approved SQL proposal.
2. Generate a real migration through the selected migration runner only after a new baseline and tested backup/restore.
3. Define separate migration/runtime roles and least-privilege grants; add policies only after custom-JWT identity and data-publicity decisions are settled.
4. Keep storage private until object ownership, upload authorization, and bucket visibility are approved and tested.
5. Add isolated staging migration, API authorization, RLS/grant, and storage tests before production rollout.

**No remote or local application data was changed for this proposal. No migration was applied. A separate explicit approval is required before any remote change.**

---

## 17. Phase 08 Pre-Migration Security and Deployment Readiness Audit

**Audit Date:** 2026-10-10  
**Status:** Audit Completed — Deployment Blockers Identified — Separate Approval Required Before Migration  
**Scope:** Strictly local inspection of database proposal (`supabase/proposals/luxe_canonical_initial_schema_proposal.sql`), existing migrations (`001_initial_schema.sql`, `002_align_existing_schema.sql`), SQLAlchemy models (`backend/app/database.py`), API routing and authentication (`backend/app/routers/*`, `backend/app/utils/*`), and Supabase storage configuration. Zero remote database queries, zero cloud migrations, zero application startup runs.

### 17.1 Prioritized Security & Deployment Blockers

| Priority | Issue / Risk Area | Location / Component | Impact & Remediation |
|---|---|---|---|
| **CRITICAL** | **Unauthenticated State-Changing & Cost-Incurring API Routes** | `POST /api/trends`<br>`POST /api/collections/generate`<br>`POST /api/products/generate`<br>`POST /api/forecast/{trend_id}`<br>`POST /api/prophecy/{trend_id}`<br>`POST /api/images/analyze` | Any anonymous client on the public internet can trigger expensive Gemini AI calls, run CPU-heavy ML backtests, write rows into the database, overwrite collections, or upload files without authentication or rate limits. **Blocker:** Must require `Depends(get_current_user)` and user role authorization before exposing to production. |
| **CRITICAL** | **PostgreSQL RLS Default Deny vs Backend Runtime Role** | `luxe_canonical_initial_schema_proposal.sql` (all 11 tables) | The proposal executes `ALTER TABLE public.<table_name> ENABLE ROW LEVEL SECURITY;` on all 11 tables but defines zero policies. Non-superuser and non-owner roles without `BYPASSRLS` will be blocked by PostgreSQL's default-deny rule on every query. If the backend connects using a restricted runtime role, all queries will return empty sets or fail. **Blocker:** Define and test least-privilege role permissions and RLS policy strategy before applying DDL. |
| **HIGH** | **Custom JWT vs Supabase RLS Identity Disconnect** | `backend/app/utils/security.py`, Supabase RLS | Application issues custom HS256 JWT tokens. Supabase PostgREST RLS relies on GoTrue JWTs decoded to `auth.uid()`. Custom backend tokens do not set PostgreSQL's `auth.uid()`. Client cannot query Supabase directly via PostgREST using application tokens. **Blocker:** Enforce security boundary in FastAPI backend; revoke all table access from Supabase `anon` and `authenticated` roles. |
| **HIGH** | **Unrestricted In-Memory File Buffering & Anonymous Storage Upload** | `backend/app/routers/images.py`, `backend/app/services/supabase_service.py` | `analyze_image` reads entire uploads into server memory (`await file.read()`) before verifying 10 MB size, allowing memory exhaustion DoS. Uploaded images are unauthenticated, lack owner tracking, and are placed in public bucket `trend-images`. **Blocker:** Enforce auth, stream size enforcement at proxy/ASGI layer, and assign user ownership to images. |
| **HIGH** | **Nullable Password Hash in User Schema** | `backend/app/database.py` (Line 129), Schema proposal | `users.password_hash` is declared `VARCHAR` / `nullable=True`. Direct SQL inserts or malformed flows could create passwordless user accounts. **Blocker:** Make `password_hash` `NOT NULL` in the canonical migration. |
| **MEDIUM** | **Absence of Database Triggers for `updated_at`** | Schema proposal, `database.py` | `created_at` defaults to `now()`, but `updated_at` relies exclusively on SQLAlchemy Python ORM `onupdate`. Direct SQL updates, administrative scripts, or non-ORM mutations will leave `updated_at` stale. **Remediation:** Add a reusable PostgreSQL trigger `set_updated_at()` for tables with `updated_at`. |
| **MEDIUM** | **CORS Wildcard Fallback & Missing API Rate Limiting** | `backend/app/config.py`, `main.py` | If `CORS_ORIGINS` is unset, default falls back to `["*"]` while allowing credentials, headers, and methods. No rate-limiting middleware is present on computationally heavy or AI-driven endpoints. **Remediation:** Remove wildcard fallback in production config; implement FastAPI rate limiting (e.g. `slowapi`). |
| **MEDIUM** | **Absence of Automated Migration Runner / Ledger** | `supabase/` directory | SQL files are manually maintained without a version ledger table (`alembic_version` or `schema_migrations`). Applying SQL manually risks untracked drift. **Remediation:** Implement a versioned migration tracking mechanism. |

---

### 17.2 Route-by-Route Authentication & Ownership Matrix

Every API route defined in `backend/app/routers/` was audited for authentication enforcement, user ownership validation, and potential data exposure:

| Route Path | Method | Auth Enforced? | Ownership / Tenant Scoped? | Risk / Vulnerability Description | Recommended Security Fix |
|---|---|---|---|---|---|
| `/api/auth/register` | `POST` | No (Public) | N/A | Normal registration endpoint. Hashes passwords with PBKDF2. | Add rate limiting to prevent credential stuffing. |
| `/api/auth/login` | `POST` | No (Public) | N/A | Normal login endpoint. Returns 7-day custom JWT. | Add rate limiting and account lockout/backoff. |
| `/api/auth/me` | `GET` | **Yes** (`Depends(get_current_user)`) | **Yes** (`current_user.id`) | Properly scoped to authenticated user profile. | None. Secure as implemented. |
| `/api/trends/categories` | `GET` | No (Public) | Global Catalog | Read-only aggregation of distinct trend categories. | Intentionally public catalog data. |
| `/api/trends` | `GET` | No (Public) | Global Catalog | Read-only listing with search, category, and status filters. | Intentionally public catalog data. |
| `/api/trends/{slug_or_id}` | `GET` | No (Public) | Global Catalog | Read-only composite trend detail (DNA, forecasts, products). | Intentionally public catalog data. |
| `/api/trends/saved` | `GET` | **Yes** (`Depends(get_current_user)`) | **Yes** (`SavedTrend.user_id == current_user.id`) | Properly scoped to authenticated user's saved items. | None. Secure as implemented. |
| `/api/trends/{trend_id}/save` | `POST` | **Yes** (`Depends(get_current_user)`) | **Yes** (`SavedTrend.user_id == current_user.id`) | Properly toggles save status for authenticated user only. | None. Secure as implemented. |
| `/api/trends` | `POST` | **NO (Public)** | **None** (Orphaned / Global) | **CRITICAL EXPOSURE:** Anyone can inject arbitrary trends, trigger automated Gemini DNA generation, and mutate catalog. | Require `Depends(get_current_user)` with role check (`designer` or `admin`). |
| `/api/collections/trend/{trend_id}` | `GET` | No (Public) | Global Catalog | Read-only collection query for a given trend. | Intentionally public catalog data. |
| `/api/collections/generate` | `POST` | **NO (Public)** | **None** (Overwrites trend collection) | **CRITICAL EXPOSURE:** Anyone can trigger Gemini AI collection generation and overwrite existing collections for any trend. | Require `Depends(get_current_user)` with designer/admin role. |
| `/api/products` | `GET` | No (Public) | Global Catalog | Read-only product listing. | Intentionally public catalog data. |
| `/api/products/{product_id}` | `GET` | No (Public) | Global Catalog | Read-only product detail. | Intentionally public catalog data. |
| `/api/products/trend/{trend_id}` | `GET` | No (Public) | Global Catalog | Read-only products by trend. | Intentionally public catalog data. |
| `/api/products/generate` | `POST` | **NO (Public)** | **None** (Inserts into global products) | **CRITICAL EXPOSURE:** Anyone can trigger batch Gemini generation and insert rogue product rows into the database. | Require `Depends(get_current_user)` with designer/admin role. |
| `/api/forecast/{trend_id}` | `GET` | No (Public) | Global Catalog | Read-only forecast model predictions. | Intentionally public catalog data. |
| `/api/forecast/{trend_id}` | `POST` | **NO (Public)** | **None** (Overwrites forecast models) | **HIGH EXPOSURE:** Anyone can trigger expensive 4-model backtests (ARIMA, Ridge, etc.) and write to `forecasts` table. | Require `Depends(get_current_user)`. Rate limit backtest executions. |
| `/api/prophecy/{trend_id}` | `GET` | No (Public) | Global Catalog | Read-only prophecy intelligence. | Intentionally public catalog data. |
| `/api/prophecy/{trend_id}` | `POST` | **NO (Public)** | **None** (Deletes and regenerates prophecy) | **HIGH EXPOSURE:** Anyone can trigger Gemini reasoning and replace prophecy data for any trend. | Require `Depends(get_current_user)` with designer/admin role. |
| `/api/images/analyze` | `POST` | **NO (Public)** | **None** (Uploads without user_id) | **CRITICAL EXPOSURE:** Anyone can upload up to 10MB images, consume OpenCV & Gemini Vision quota, and write to storage & DB. | Require `Depends(get_current_user)`. Stream body length check. |
| `/api/images/{filename}` | `GET` | No (Public) | Local disk fallback | Path traversal mitigated via `commonpath`, but serves local files without authentication. | Verify path validation and keep local storage strictly for local development. |

---

### 17.3 Least-Privilege Database Role & Permission Proposal

The production database must not use a single superuser role for all application traffic. Below is the least-privilege role architecture designed for LUXE.TECH:

#### Role 1: Migration Administrator (`luxe_migration_role` or deployment runner)
- **Purpose:** Used strictly during CI/CD or controlled maintenance windows to execute DDL migrations and manage schema.
- **Attributes:** `NOSUPERUSER`, `NOCREATEDB`, `INHERIT`.
- **Privileges:**
  - Owner of schema `public` and all 11 application tables.
  - Full DDL privileges: `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`, `CREATE INDEX`, `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`.
  - Never used by the running FastAPI application server.

#### Role 2: Backend Application Runtime (`luxe_app_user`)
- **Purpose:** Used by FastAPI (`DATABASE_URL`) during normal application operations.
- **Attributes:** `NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`, `NOINHERIT`, `BYPASSRLS` (or explicit application role bypass).
- **Privileges:**
  - `CONNECT ON DATABASE` to dedicated project database.
  - `USAGE ON SCHEMA public`.
  - Least-privilege DML only:
    - `SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public`.
    - `USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public`.
  - Explicitly **REVOKED / DENIED:**
    - No `CREATE`, `DROP`, `ALTER`, or `TRUNCATE` privileges on schema or tables.
    - No access to Supabase internal schemas (`auth`, `storage`, `vault`, `pg_catalog` write).

#### Role 3: Supabase Public / PostgREST Client Roles (`anon`, `authenticated`)
- **Purpose:** Supabase API gateway roles used by browser PostgREST clients.
- **Privileges:**
  - **ZERO PRIVILEGES ON APPLICATION TABLES:**
    - `REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;`
    - `REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;`
  - **Rationale:** All LUXE.TECH business logic, authentication, ownership validation, and AI orchestration are handled by FastAPI. Exposing tables to direct PostgREST queries bypasses backend validation and custom JWT verification.

---

### 17.4 Data Classification: Public Catalog vs Private User Data

To prevent data leaks, data assets are strictly categorized:

| Classification | Tables / Resources | Data Fields | Access Policy & Protection |
|---|---|---|---|
| **Private User Data** | `users`<br>`saved_trends` | Password hashes, user emails, personal profile info, user saved bookmarks. | **STRICTLY PRIVATE.** Never exposed via direct API. Accessible only by authenticated user for their own records (`user_id == current_user.id`). Never exposed to `anon` or public PostgREST. |
| **Public Fashion Intelligence Catalog** | `trends`<br>`trend_signals`<br>`trend_dna`<br>`collections`<br>`products`<br>`retail_signals`<br>`forecasts`<br>`prophecy` | Trend names, descriptions, color palettes, visual DNA, market demand signals, forecasting predictions, AI prophecy insights. | **PUBLIC READ / RESTRICTED WRITE.** Read operations (`GET`) are intentionally public to allow discovery and browsing. Write operations (`POST`, `PUT`, `DELETE`) are strictly restricted to authenticated designers/admins via FastAPI. |
| **Media & Images** | `images`, Supabase Storage (`trend-images`, `user-uploads`) | Image binary files, dominant colors, contrast, brightness, visual metadata. | **MIXED:** Public trend moodboards/visuals are public read (`trend-images`). User-specific uploads must reside in private buckets (`user-uploads`) accessible only via signed URLs. Uploading must require authentication. |

---

### 17.5 Storage Security Architecture & Recommendations

1. **Bucket Visibility Model:**
   - `trend-images` (Public): Intended for curated trend imagery, runways, and moodboards. Read access is public via CDN URL.
   - `collections` (Public): Generated collection moodboard assets and export cards. Read access is public.
   - `user-uploads` (Private): User-submitted personal inspirations, sketches, and internal uploads. Read access requires temporary signed URLs (1-hour expiry).
2. **Upload Restrictions & Validation:**
   - **Authentication:** `POST /api/images/analyze` must require `Depends(get_current_user)`.
   - **Streaming Size Cap:** Instead of buffering full 10MB payloads in RAM via `await file.read()`, stream chunk sizes and enforce maximum body length at the reverse proxy (Nginx/Traefik `client_max_body_size 10M`) or ASGI middleware.
   - **MIME & Header Verification:** Preserve existing multi-layer validation (magic bytes, Pillow image verification, dimension sanity checks).
   - **Filename Sanitization:** Use cryptographically secure UUID object paths (`UUID4() + sanitized_ext`), preventing path traversal and name collisions.
   - **User Ownership:** Add `user_id` foreign key column to `images` table to track who uploaded each file.

---

### 17.6 Fresh-Install Migration Sequence & Analysis of Migration 002

#### Evaluation of Migration 002 (`002_align_existing_schema.sql`):
- Migration 002 was specifically constructed as an **incremental patch for a pre-existing legacy database**.
- Its SQL operations include:
  - Renaming old columns: `ALTER TABLE ... RENAME COLUMN metadata TO metadata_json;`
  - Casting old JSONB columns: `ALTER TABLE ... ALTER COLUMN colors TYPE TEXT USING colors::text;`
  - Adding `data_status` columns conditionally.
  - Dropping old duplicated columns.
  - Adding conditional `NOT NULL` constraints where `NULL` counts are zero.
- **Finding on Migration 002 for Fresh Installation:**
  - **Migration 002 is NOT needed for a fresh schema and MUST NOT be executed.**
  - On a fresh Supabase database, executing Migration 002 will fail with errors (e.g. attempting to rename columns that do not exist or alter non-existent JSONB types).
  - The canonical initial schema (`supabase/proposals/luxe_canonical_initial_schema_proposal.sql`) already defines all 11 tables with the correct target column names (`metadata_json`, `colors_json`), correct types (`TEXT`, `DOUBLE PRECISION`), and proper foreign keys.

#### Canonical Fresh-Install Migration Sequence:
1. **Migration Baseline Step:** Create a single, clean canonical initial migration file: `supabase/migrations/001_canonical_initial_schema.sql` (derived from the validated proposal).
2. **Dependency-Ordered DDL Execution:**
   - Level 0 (Independent parent tables): `users`, `trends`.
   - Level 1 (Dependent child tables with FK to `trends`):
     - `trend_signals` (`ON DELETE CASCADE`)
     - `trend_dna` (`ON DELETE CASCADE`, unique `trend_id`)
     - `images` (`ON DELETE SET NULL`)
     - `collections` (`ON DELETE CASCADE`)
     - `products` (`ON DELETE SET NULL`)
     - `retail_signals` (`ON DELETE SET NULL`)
     - `forecasts` (`ON DELETE CASCADE`)
     - `prophecy` (`ON DELETE CASCADE`)
   - Level 2 (Dependent child table with FK to `users` and `trends`):
     - `saved_trends` (`ON DELETE CASCADE` to both, unique `(user_id, trend_id)`)
3. **Index & Constraint Creation:**
   - Unique indexes on `users(email)`, `trends(slug)`, and `saved_trends(user_id, trend_id)`.
   - Foreign key lookup indexes on all child tables.
4. **Security & Role Grants:**
   - Enable RLS on all 11 tables.
   - Revoke all permissions from `anon` and `authenticated`.
   - Grant DML permissions to backend runtime role.
5. **Storage Bucket Provisioning:**
   - Provision `trend-images`, `collections`, and `user-uploads` via Supabase Storage API / management script with explicit MIME/size limits.

---

### 17.7 Backup, Rollback & Disaster Recovery Requirements

Before any production migration or database change is applied:

1. **Verify Backup & PITR Capability:**
   - Confirm Supabase project automated daily backups or Point-in-Time Recovery (PITR) is active in Supabase Project Settings -> Database -> Backups.
   - For fresh deployment on an empty schema, export pre-migration database metadata snapshot via pg_dump (`pg_dump --schema-only`).
2. **Deterministic Down-Migration (Rollback Script):**
   - Provide an audited rollback script capable of reversing the initial schema completely if deployment validation fails:
     ```sql
     -- Rollback script for initial schema (executed in reverse dependency order)
     DROP TABLE IF EXISTS public.saved_trends CASCADE;
     DROP TABLE IF EXISTS public.prophecy CASCADE;
     DROP TABLE IF EXISTS public.forecasts CASCADE;
     DROP TABLE IF EXISTS public.retail_signals CASCADE;
     DROP TABLE IF EXISTS public.products CASCADE;
     DROP TABLE IF EXISTS public.collections CASCADE;
     DROP TABLE IF EXISTS public.images CASCADE;
     DROP TABLE IF EXISTS public.trend_dna CASCADE;
     DROP TABLE IF EXISTS public.trend_signals CASCADE;
     DROP TABLE IF EXISTS public.trends CASCADE;
     DROP TABLE IF EXISTS public.users CASCADE;
     ```
3. **Rollback Decision Gate:**
   - If initial schema creation fails, if post-migration smoke tests fail, or if runtime connection errors occur, execute the rollback script immediately to restore clean project state. Never leave a partially-migrated database active.

---

### 17.8 Pre-Deployment Verification Checklist

Before running migrations or starting the production application:

- [ ] **1. Project Identity Reconfirmation:** Confirmed that `.env` points to the dedicated LUXE.TECH project.
- [ ] **2. Backup / Snapshot Verified:** Confirmed recovery capability or empty state baseline.
- [ ] **3. Migration 002 Omitted:** Confirmed that legacy migration 002 is excluded from fresh installation.
- [ ] **4. Route Authentication Implemented:** State-changing routes (`POST /api/trends`, `POST /api/collections/generate`, `POST /api/products/generate`, `POST /api/forecast/*`, `POST /api/prophecy/*`, `POST /api/images/analyze`) protected with `Depends(get_current_user)`.
- [ ] **5. Runtime Role Configured:** Backend connects with least-privilege DML role; `anon`/`authenticated` grants revoked.
- [ ] **6. Storage Buckets Provisioned:** Buckets created with correct public/private visibility and file size caps.
- [ ] **7. Connection Pooler Configured:** If using Supabase transaction pooler (port 6543), psycopg prepared statements explicitly disabled (`prepare_threshold=None`).
- [ ] **8. CORS & Secrets Secured:** Production CORS origins allowlist set; secret keys strictly server-side.
- [ ] **9. Post-Migration Smoke Test Plan Ready:** Read/write verification for users, catalog, trends, and uploads tested in staging.

---

## 18. Phase 10 Security Fix Verification and Migration Readiness Audit

**Audit Date:** 2026-10-10  
**Verification Scope:** Code-level verification of all Phase 09 security remediations (`backend/app/routers/*`, `backend/app/utils/*`, `backend/app/config.py`), upload protections, rate limiting robustness, test isolation proofs, and edge-case test quality. Zero remote database queries, zero cloud migrations, zero application startup runs.

### 18.1 Code & Authentication Dependency Verification

Every changed route, validator, configuration setting, and rate limiter was audited line-by-line:

| Component / Router | Verified Behavior | Findings & Observations |
|---|---|---|
| **Dependency Order** (`trends.py`, `collections.py`, `products.py`, `forecasts.py`, `prophecy.py`, `images.py`) | **VERIFIED:** FastAPI dependency injection evaluates `Depends(rate_limit_dependency)` and `Depends(get_current_user)` strictly *before* endpoint function bodies execute. | If authentication or rate-limit checks fail, execution aborts with `HTTP 401` or `HTTP 429`. No database writes, AI API calls, or storage uploads can be triggered by unauthenticated clients on these POST routes. |
| **JWT Subject Handling** (`security.py`) | **VERIFIED:** `decode_token` checks `exp`, `iat`, and `HS256` signature using `SECRET_KEY`. `get_optional_user` extracts identity from `sub`, `id`, or `user_id`. | Consistent dict format returned: `{"id": str, "email": str, "role": str}`. Expired and tampered tokens fail closed with `HTTP 401`. |
| **User Scoping & Isolation** (`auth.py`, `trends.py`) | **VERIFIED:** User profile (`/api/auth/me`) and saved trends (`/api/trends/saved`, `/api/trends/{id}/save`) strictly filter by `current_user["id"]`. | Cross-user read and modification isolation confirmed via automated tests. User B cannot access or alter User A's saved records. |
| **Catalog Mutations** (`trends.py`, `collections.py`, `products.py`, `forecasts.py`, `prophecy.py`) | **PARTIAL / RISK IDENTIFIED:** Routes require authenticated users, but underlying tables (`trends`, `collections`, `products`, `forecasts`, `prophecy`) have **no owner column** (`user_id`). | Any authenticated user can overwrite existing trend collections, backtest forecasts, or prophecies across the platform. Role-based access control (RBAC) or ownership attribution is needed before multi-tenant production. |
| **Public GET Routes** (`collections.py` L24-49, `prophecy.py` L19-23) | **CRITICAL RISK IDENTIFIED:** `GET /api/collections/{trend_id}` and `GET /api/prophecy/{trend_id}` contain **lazy generation logic**. | If collection or prophecy records do not already exist for a trend, these public unauthenticated `GET` endpoints invoke Gemini AI and execute `db.add()` / `db.commit()`. An anonymous visitor querying non-seeded trends can trigger database writes and AI quota consumption. |
| **Rate Limiter Robustness** (`rate_limit.py` L54-57) | **HIGH RISK IDENTIFIED:** Line 55 reads `request.headers.get("X-Forwarded-For")` unconditionally. | A client can bypass the in-memory rate limiter by sending randomized `X-Forwarded-For` headers on each request. Furthermore, the limiter keys strictly on IP rather than `user_id` for authenticated endpoints, causing NAT/proxy collisions and failing to restrict authenticated multi-IP scraping. |
| **CORS Fail-Closed Behavior** (`config.py` L38-51) | **VERIFIED:** In production (`ENVIRONMENT=production`), wildcard `*`, empty strings, and schemes lacking `http://` or `https://` raise `ValueError`. In development, safely falls back to localhost allowlist, never `*`. | Production server fails to start if CORS is insecure or missing. |

---

### 18.2 Upload Protections Verification

1. **Bounded Read Size Enforcement:**
   - [`backend/app/utils/validation.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/utils/validation.py#L52-L68): Reads incoming files in $64\text{ KB}$ chunks.
   - Cumulative byte tracker immediately raises `HTTP 413` when `total_bytes > 10 * 1024 * 1024` ($10\text{ MB}$).
   - Verified via test: an oversized $10.5\text{ MB}$ payload is rejected without reading the remaining payload into RAM.
2. **Stream Cleanup:**
   - Bounded read loop wrapped in `try ... finally: await file.close()`.
   - Spooled temporary file handles and memory buffers are freed upon completion or early exception.
3. **Multi-Layer Image Validation:**
   - **Extension:** Restricts to `.jpg`, `.jpeg`, `.png`, `.webp`.
   - **MIME Type:** Restricts to `image/jpeg`, `image/png`, `image/webp`.
   - **File Signature / Decoding:** Pillow `image.verify()` validates image headers and internal structure; re-opens to verify readable raster data.
   - **Pixel Boundaries:** Enforces minimum $10\times 10\text{px}$ and maximum $10,000\times 10,000\text{px}$.
4. **Asset Privacy & Bucket Leakage Risk:**
   - **HIGH RISK IDENTIFIED:** [`backend/app/routers/images.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/images.py#L46): Uploaded images are unconditionally sent to bucket `"trend-images"`, which is declared **public**.
   - `upload_file("trend-images", ...)` returns a public CDN URL.
   - The private bucket `"user-uploads"` is never used, and the `images` table has no `user_id` column. User inspiration uploads are unintentionally exposed as public assets.
5. **Storage Mocking in Tests:**
   - **VERIFIED:** Tests either mock `supabase_service.upload_file`, redirect `LOCAL_STORAGE_DIR` to `tmp_path`, or reject requests at dependency/validation stages before storage is called. Zero external storage calls occur during tests.

---

### 18.3 Test Isolation Proof

Before running any test command, test configuration was audited:

1. **Configuration Precedence:**
   - [`backend/tests/conftest.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/tests/conftest.py#L10-L20) explicitly sets `os.environ["DATABASE_URL"] = "sqlite:///./test_luxe.db"`, `os.environ["ENVIRONMENT"] = "testing"`, and clears `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, and `GEMINI_API_KEY` before any application module is imported.
   - Calls `get_settings.cache_clear()` immediately after setting environment overrides.
2. **Database Engine Binding:**
   - `test_engine` binds to `sqlite:///./test_luxe.db`.
   - `app.dependency_overrides[get_db]` intercepts all router database sessions and binds them strictly to `TestingSessionLocal`.
   - `conftest.py` teardown executes `drop_all` and removes `./test_luxe.db`.
3. **Zero Remote Connection Guarantee:**
   - Tests **cannot** connect to the configured Supabase project. Live connection attempts are impossible under this configuration.

---

### 18.4 Test Quality & Expanded Security Suite

Inspected assertions across the test suite:

- **Real Dependencies Exercised:** Protected endpoint tests do **not** mock `get_current_user`; they exercise real JWT generation, HTTP Bearer header parsing, and cryptographic verification.
- **Expanded Security Test Suite (`test_api_security.py`):**
  - Malformed JWT string (`Bearer not.a.valid.jwt.token`) $\to$ Rejected with `HTTP 401`.
  - Expired JWT token (issued with negative expiration) $\to$ Rejected with `HTTP 401`.
  - Empty Bearer scheme (`Bearer `) $\to$ Rejected with `HTTP 401`.
  - Non-Bearer authorization scheme (`Basic ...`) $\to$ Rejected with `HTTP 401`.
  - Sub-minimum dimension upload ($9\times 9\text{px}$) $\to$ Rejected with `HTTP 400`.
  - Oversized upload ($10.5\text{ MB}$) $\to$ Rejected with `HTTP 413`.
  - Disallowed extensions, MIME types, empty files, corrupted payloads $\to$ Rejected with `HTTP 400`.
  - Cross-user saved trend isolation $\to$ User B sees empty list; User B save toggle does not affect User A.
  - Production CORS $\to$ Wildcard `*` and empty configs raise `ValueError`.
  - Rate limiting $\to$ 11th login attempt returns `HTTP 429`.
  - Forwarding header spoofing $\to$ Demonstrates that client-supplied `X-Forwarded-For` alters rate limiter keying unless sanitized by an upstream proxy.
- **Suite Results:** **11 of 11 security tests passed; 35 of 35 total backend tests passed.**

---

### 18.5 Prioritized Deployment Blocker List

| Priority | Issue / Risk Area | Location / Reference | Description & Required Remediation |
|---|---|---|---|
| **CRITICAL** | **Unauthenticated Lazy Mutation in Public GET Endpoints** | [`collections.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/collections.py#L24-L49)<br>[`prophecy.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/prophecy.py#L19-L23) | `GET /api/collections/{trend_id}` and `GET /api/prophecy/{trend_id}` lazily invoke Gemini AI and execute database writes (`db.add()`, `db.delete()`, `db.commit()`) when records are absent. Anonymous web crawlers or scrapers can incur heavy LLM bills and mutate database state via GET requests. **Remediation:** Remove on-the-fly mutation from GET routes; return existing data or `404/insufficient_data`, requiring authenticated POST requests for generation. |
| **HIGH** | **Private Upload Leakage via Public Storage Bucket** | [`images.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/images.py#L46-L53) | All uploads in `analyze_image` are pushed to public bucket `trend-images` and issued public URLs. Uploads lack `user_id` attribution on `ImageRecord`. Private sketches and inspiration boards are publicly accessible if the URL is known. **Remediation:** Add `user_id` to `ImageRecord`; route user uploads to private bucket `user-uploads` with 1-hour signed URLs. |
| **HIGH** | **Missing Ownership / RBAC on Platform Catalog Mutations** | `trends.py`<br>`collections.py`<br>`forecasts.py`<br>`prophecy.py` | Mutation routes require authentication but lack role or ownership checks. Any authenticated user can overwrite platform collections, recompute model backtests, or replace prophecy timelines for any trend. **Remediation:** Implement role-based authorization (`admin`/`lead_analyst`) for catalog-level mutations. |
| **HIGH** | **Rate Limiter IP Spoofing & Multi-Worker State Isolation** | [`rate_limit.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/utils/rate_limit.py#L54-L57) | Rate limiter trusts unvalidated client `X-Forwarded-For` headers and operates strictly in single-process memory. Clients can bypass limits by rotating headers; multi-worker Uvicorn or container deployments maintain uncoordinated state. **Remediation:** Require upstream reverse proxy (Nginx/Cloudflare) to overwrite `X-Forwarded-For`; deploy Redis-backed limiter for multi-worker production. |
| **MEDIUM** | **Reverse Proxy Outer Request Limit Requirement** | Infrastructure / Reverse Proxy | While bounded chunk reads protect server memory, reverse proxies (Nginx `client_max_body_size 10M`) must be deployed to drop oversized TCP payloads before reaching Python ASGI workers. |
| **MEDIUM** | **User Password Hash Nullability** | [`database.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/database.py#L129) | `User.password_hash` remains `nullable=True` to maintain compatibility with unmigrated schema and demo seeding. Must be updated to `NOT NULL` in the migration sequence. |
| **LOW** | **Starlette Deprecation Warnings** | `fastapi.testclient`, `status.HTTP_413_REQUEST_ENTITY_TOO_LARGE` | Minor deprecation warnings observed during test runs. Update to `HTTP_413_CONTENT_TOO_LARGE` and modern testclient when upgrading dependencies. |

---

### 18.6 Explicitly Unverified Items

The following properties cannot be established from local source analysis alone and remain **UNVERIFIED**:

1. **Remote Supabase Project RLS Policy Enforcement:** The remote Supabase database has not been connected to; live table-level RLS policies and role bypass behaviors are unverified.
2. **Supabase Storage Bucket Permissions:** Remote storage bucket existence, public/private access rules, and CORS configuration on the Supabase project have not been inspected or provisioned.
3. **Transaction Pooler Under Live Application Load:** Connection behavior with psycopg prepared statements disabled (`prepare_threshold=None`) on Supabase port 6543 has not been validated against the live database.
4. **Centralized Rate Limiting Under Concurrency:** Multi-process rate-limiting behavior has not been tested against a shared Redis or cache cluster.

**Phase 10 made no remote database connections, applied no migrations, and made no cloud changes. A separate explicit approval is required before proceeding to migration preparation or deployment.**

---

## 19. Phase 11 — Final Local Security Remediation & RBAC Hardening Verification

**Execution Date:** 2026-10-10  
**Status:** COMPLETE (All Local API Security Deficiencies Resolved; Suite 100% Passing)  
**Safety Scope:** Strictly local offline code remediation. No remote Supabase database connections, zero cloud DDL/DML migrations, zero storage mutations executed.

---

### 19.1 Remediation Summary & Technical Resolutions

| Vulnerability / Requirement | File(s) Affected | Technical Remediation Applied | Verification Status |
|---|---|---|---|
| **GET Endpoints Lazy Mutation & AI Bill Exhaustion** | [`collections.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/collections.py)<br>[`prophecy.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/prophecy.py) | Removed all on-the-fly generation (`db.add()`, `db.commit()`, `gemini_service` calls) from `GET /api/collections/{trend_id}` and `GET /api/prophecy/{trend_id}`. Endpoints now raise explicit `HTTPException(status_code=404)` when trends or pre-existing records are absent. Preserves public discovery without unauthenticated mutation. | **RESOLVED & VERIFIED**<br>Zero DB writes and zero AI calls proven via regression tests. |
| **Missing Role-Based Access Control on Platform Mutations** | [`security.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/utils/security.py)<br>[`trends.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/trends.py)<br>[`collections.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/collections.py)<br>[`products.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/products.py)<br>[`forecasts.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/forecasts.py)<br>[`prophecy.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/prophecy.py) | Defined `PRIVILEGED_ROLES = frozenset({"admin", "lead_analyst"})` and introduced `get_privileged_user` dependency. State-changing platform catalog routes now strictly reject ordinary users with `HTTP 403 Forbidden` (`detail="Forbidden: Administrative or lead analyst privileges required..."`). Personal bookmarks (`POST /api/trends/{id}/save`) remain accessible to all authenticated users (`role="user"`). | **RESOLVED & VERIFIED**<br>Ordinary users receive 403 on catalog writes; privileged users receive 200. |
| **Private Upload Leakage via Public Storage Bucket** | [`images.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/images.py)<br>[`supabase_service.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/services/supabase_service.py) | Arbitrary user uploads and personal exploratory uploads route to private bucket `"user-uploads"` with namespaced storage paths (`{user_id}/{uuid}_{safe_filename}`). Generates short-lived signed URLs when Supabase is configured; public URL generation on private buckets strictly raises `ValueError`. Shared catalog uploads by privileged users route to `"trend-images"`. Local file serving endpoint (`/api/images/local/{bucket}/{filepath}`) enforces authentication, path traversal guards, and file-ownership checks for non-public buckets. Preserved schema parity without adding premature `user_id` column to `image_records`. | **RESOLVED & VERIFIED**<br>Upload routing, signed URLs, and local authorization verified. |
| **Rate Limit IP Spoofing & NAT Collisions** | [`rate_limit.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/utils/rate_limit.py)<br>[`validation.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/utils/validation.py) | Rate limiter disables trust of `X-Forwarded-For` by default (`trust_forwarded_headers=False`), defaulting to direct socket connection host `request.client.host`. For authenticated callers, limits are keyed on `user_id` (`f"{scope}:user:{user_id}"`), eliminating collisions between users behind corporate NATs and preventing authenticated attackers from evading limits by rotating IP headers. Documented multi-worker / multi-container scaling requirement (Redis or API gateway perimeter required before horizontal scaling). Resolved `HTTP_413_CONTENT_TOO_LARGE` deprecation warning. | **RESOLVED & VERIFIED**<br>Spoofing bypass neutralization and user-keyed limits verified. |

---

### 19.2 Test Suite Execution & Parity Results

The full backend test harness was executed against the isolated SQLite test engine (`./test_luxe.db`) with external credentials blanked (`SUPABASE_URL=""`, `GEMINI_API_KEY=""`):

- **Security & Authorization Test Suite (`test_api_security.py`):** **15 of 15 tests passed.**
  - `test_anonymous_requests_to_protected_routes_return_401` $\to$ PASSED
  - `test_public_read_only_routes_remain_accessible_without_auth` $\to$ PASSED
  - `test_role_based_access_control_on_platform_mutations` $\to$ PASSED (403 for ordinary users, 200 for privileged)
  - `test_cross_user_isolation_on_saved_trends` $\to$ PASSED
  - `test_upload_bounded_chunk_size_enforcement` $\to$ PASSED (10MB limit enforced)
  - `test_upload_format_and_empty_file_validation` $\to$ PASSED
  - `test_production_cors_rejects_wildcard_and_empty` $\to$ PASSED
  - `test_rate_limiting_enforcement` $\to$ PASSED
  - `test_invalid_and_expired_jwt_rejection` $\to$ PASSED
  - `test_upload_pixel_dimension_boundary_validation` $\to$ PASSED
  - `test_rate_limiter_rejects_spoofed_forwarding_headers` $\to$ PASSED (rotating `X-Forwarded-For` fails to bypass rate limiting)
  - `test_get_endpoints_strictly_read_only_with_zero_writes_and_zero_ai_calls` $\to$ PASSED (zero DB writes, zero AI calls, 404 on missing records)
  - `test_private_uploads_bucket_and_signed_url_separation` $\to$ PASSED (namespaced paths, private bucket routing, public URL rejection)
  - `test_local_storage_serving_authorization` $\to$ PASSED (401 unauthenticated, 403 unauthorized, 200 owner/admin, 400 traversal)
  - `test_authenticated_rate_limit_keyed_on_user_identity` $\to$ PASSED (independent quotas per authenticated user on same IP)
- **Feature & Functional Test Suite (`test_all_features.py`):** **14 of 14 tests passed.**
- **Database Bootstrap Suite (`test_database_bootstrap.py`):** **1 of 1 passed.**
- **Gemini Service Suite (`test_gemini_service.py`):** **9 of 9 passed.**
- **Supabase Storage Suite (`test_supabase_storage.py`):** **3 of 3 passed.**
- **Total Suite Results:** **42 of 42 tests passed (100% pass rate in 37.92s).**

---

### 19.3 Future Database Migration Requirements Documented

To achieve full production normalization while maintaining zero drift with the proposed baseline schema, the following schema migrations must be included in future migration batches:

1. **`image_records.user_id` Foreign Key:**
   - **Column:** `user_id UUID REFERENCES users(id) ON DELETE CASCADE`
   - **Rationale:** Currently, user ownership of exploratory uploads is preserved via namespaced object paths (`user_id/uuid_filename`) and access control in the router. An explicit relational column will enable foreign-key integrity and database-level RLS policies on `image_records`.
2. **`users.password_hash` NOT NULL Constraint:**
   - **Column:** `ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL;`
   - **Rationale:** Currently nullable to preserve compatibility with initial unmigrated seed routines. Must be made non-nullable after all initial accounts are salted and hashed.

---

### 19.4 Final Deployment Readiness Status

```
[PASS] GET Endpoint Idempotency & Read-Only Safety
[PASS] Explicit Role-Based Access Control (Admin / Lead Analyst vs User)
[PASS] Upload Memory Protection & MIME/Signature Validation
[PASS] Private vs Public Storage Bucket Isolation & Signed URLs
[PASS] Client Identity & Rate Limiting Hardening
[PASS] Production CORS Configuration Fail-Closed Validation
[PASS] 100% Test Suite Green (42/42 tests passing in isolated test harness)
[BLOCKED] Remote Supabase Schema Migration (Requires Explicit User Approval)
[BLOCKED] Remote Storage Bucket Provisioning (user-uploads, trend-images, collections)
```

**Phase 11 local security remediations are complete. All high-priority application security vulnerabilities identified in the audits have been resolved locally. Zero cloud changes have been made. Awaiting explicit user approval before proceeding to migration preparation.**

---

## 20. Phase 12 — Canonical Migration Preparation & Offline Validation Findings

**Execution Date:** 2026-10-10  
**Status:** COMPLETE (Candidate Migration, Security Design, and Deployment Runbook Prepared Offline; Parity Checks 100% Passed)  
**Safety Scope:** Strictly local offline preparation. No Supabase connections, no remote queries, no SQL execution on cloud databases, zero DDL/DML applied, zero storage mutations, no active migration directory pollution.

---

### 20.1 Prepared Migration Artifacts & Exact File References

| Deliverable Artifact | Repository Location | Description & Scope |
|---|---|---|
| **Canonical Candidate Migration SQL** | [`supabase/proposals/luxe_phase12_canonical_candidate_migration.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase12_canonical_candidate_migration.sql) | Standalone fresh-install candidate schema defining all 11 application tables, 113 columns, 12 indexes, foreign key cascading, and RLS enablement. Excludes legacy Migration 002. Contains zero destructive operations. |
| **Security & Permissions Design** | [`supabase/proposals/PHASE_12_SECURITY_AND_PERMISSIONS_DESIGN.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_12_SECURITY_AND_PERMISSIONS_DESIGN.md) | Technical architecture covering least-privilege runtime role (`luxe_app_user`), PostgREST fail-closed protection, FastAPI authorization enforcement, custom JWT vs Supabase Auth identity disconnect, and storage bucket security. |
| **Deployment Runbook** | [`supabase/proposals/PHASE_12_DEPLOYMENT_RUNBOOK.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_12_DEPLOYMENT_RUNBOOK.md) | 8-step ordered operational runbook covering pre-migration baseline checks, backup/PITR verification, single-transaction DDL application, post-migration schema validation, storage bucket provisioning, and smoke testing with rollback procedures. |

---

### 20.2 Key Architectural Decisions & Staged Strategies

#### 1. Strategy for `users.password_hash` Nullability
- **Context:** In `database_seed.py`, `analyst@luxe.tech` is seeded without a password hash to avoid hardcoded credentials in the repository.
- **Candidate DDL Strategy:** `password_hash VARCHAR` is defined as nullable in the candidate migration baseline, ensuring exact compatibility with SQLAlchemy metadata (`User.password_hash.nullable = True`) and preventing seed failure during initial installation.
- **Production Hardening Requirement:** Once the administrative analyst account is populated with a PBKDF2 salt/hash, execute:
  ```sql
  UPDATE public.users SET password_hash = '<salted_hash>' WHERE password_hash IS NULL;
  ALTER TABLE public.users ALTER COLUMN password_hash SET NOT NULL;
  ```

#### 2. Decision on `images.user_id` Ownership
- **Context:** The current SQLAlchemy `ImageRecord` model contains 13 columns and does not declare `user_id`. In Phase 11, exploratory upload ownership was hardened at the application/storage level: uploads are namespaced by user identity in storage paths (`storage_path = '{user_id}/{uuid}_{safe_filename}'`), and access control is enforced in the FastAPI router during file serving.
- **Decision:** The initial baseline candidate schema matches `Base.metadata` exactly (13 columns on `images`), maintaining 100% offline schema parity without premature model drift.
- **Staged Upgrade Step:** A subsequent migration step is documented and ready for co-deployment when the SQLAlchemy `ImageRecord` model is updated:
  ```sql
  ALTER TABLE public.images ADD COLUMN user_id VARCHAR REFERENCES public.users(id) ON DELETE SET NULL;
  CREATE INDEX ix_images_user_id ON public.images (user_id);
  ```

#### 3. Exclusion of Legacy Migration 002
- **Context:** `supabase/migrations/002_align_existing_schema.sql` was an `ALTER TABLE` rename script intended to upgrade databases created under the legacy `001_initial_schema.sql` (renaming `colors` to `colors_json`, converting `JSONB` to `TEXT`, etc.).
- **Decision:** Migration 002 is strictly an alignment patch for legacy databases and is **EXCLUDED** from the fresh-install migration sequence. The candidate migration creates all tables directly with canonical column names and serialization types.

---

### 20.3 Offline Parity Validation Results

An automated offline static analysis script evaluated the candidate SQL against SQLAlchemy metadata without connecting to any database:

```
======================================================================
LUXE.TECH Phase 12 Offline Candidate Migration Validation
======================================================================

[1] Table Count Verification:
    - SQLAlchemy Model Tables: 11
    - Candidate SQL Tables:   11
    -> PASS: Exactly 11 matching tables.

[2] Column Parity Verification:
    - Total SQLAlchemy Columns: 113
    - Total Candidate Columns:  113
    -> PASS: All 113 columns match names, presence, and nullability.

[3] Row Level Security (RLS) Coverage:
    - Tables with RLS enabled: 11
    -> PASS: 100% of tables (11/11) have Row Level Security enabled.

[4] Index & Constraint Verification:
    - Active DDL Indexes defined in SQL: 12
      * users: ix_users_email (email) [unique=True]
      * trends: ix_trends_slug (slug) [unique=True]
      * trends: ix_trends_category (category) [unique=False]
      * trend_signals: ix_trend_signals_trend_id (trend_id) [unique=False]
      * images: ix_images_trend_id (trend_id) [unique=False]
      * collections: ix_collections_trend_id (trend_id) [unique=False]
      * products: ix_products_trend_id (trend_id) [unique=False]
      * retail_signals: ix_retail_signals_trend_id (trend_id) [unique=False]
      * forecasts: ix_forecasts_trend_id (trend_id) [unique=False]
      * prophecy: ix_prophecy_trend_id (trend_id) [unique=False]
      * saved_trends: ix_saved_trends_user_id (user_id) [unique=False]
      * saved_trends: ix_saved_trends_trend_id (trend_id) [unique=False]
    -> PASS: Exactly 12 explicit indexes correctly defined.

[5] Safety Rules Check (Executable DDL):
    -> PASS: Zero destructive operations (no DROP TABLE, TRUNCATE, DROP ... CASCADE, or BYPASSRLS).

======================================================================
ALL OFFLINE PARITY AND SAFETY CHECKS PASSED (100% SUCCESS)
======================================================================
```

---

### 20.4 Explicit List of Approvals Still Required Before Deployment

Before any remote database changes can be executed, the following explicit user approvals are required:

1. **Candidate Migration Approval:** Formal review and approval of [`luxe_phase12_canonical_candidate_migration.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase12_canonical_candidate_migration.sql) as the designated initial schema.
2. **Deployment Runbook Approval:** Acceptance of the 8-step ordered deployment procedure in [`PHASE_12_DEPLOYMENT_RUNBOOK.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_12_DEPLOYMENT_RUNBOOK.md).
3. **Dedicated Target Confirmation:** User verification of the target Supabase project ID and baseline emptiness check.
4. **Backup / Recovery Baseline Sign-Off:** Confirmation of automated backup or PITR status in the Supabase management console.
5. **Runtime Role Provisioning Approval:** Sign-off on the least-privilege `luxe_app_user` database role and permission grants defined in [`PHASE_12_SECURITY_AND_PERMISSIONS_DESIGN.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_12_SECURITY_AND_PERMISSIONS_DESIGN.md).
6. **Storage Bucket Provisioning Sign-Off:** Authorization to create `trend-images` (public), `collections` (public), and `user-uploads` (private).

**All Phase 12 deliverables have been prepared offline. No cloud changes or remote migrations have been executed.**

---

## 21. Phase 13 — Independent Migration Safety Review & Runtime Architecture Validation

**Execution Date:** 2026-10-10  
**Review Type:** Independent Local Static Audit (Offline Only)  
**Artifacts Reviewed:**
- [`supabase/proposals/luxe_phase12_canonical_candidate_migration.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase12_canonical_candidate_migration.sql)
- [`supabase/proposals/PHASE_12_SECURITY_AND_PERMISSIONS_DESIGN.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_12_SECURITY_AND_PERMISSIONS_DESIGN.md)
- [`supabase/proposals/PHASE_12_DEPLOYMENT_RUNBOOK.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_12_DEPLOYMENT_RUNBOOK.md)
- [`PHASE_04_DATABASE_READINESS.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/PHASE_04_DATABASE_READINESS.md)

---

### 21.1 PostgreSQL RLS Mechanics: Default-Deny Lockout & The Least-Privilege Solution

#### The PostgreSQL Default-Deny Trap
In PostgreSQL, when Row Level Security is enabled on a table (`ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;`), an essential security rule takes effect:
> **PostgreSQL Documentation (§5.8):** *"If row security is enabled on a table, all normal access to the table for selecting or modifying rows must be allowed by a row security policy. If no policy exists on the table, a default-deny policy is used, meaning that no rows are visible or can be modified."*

Crucially:
- A database user that is **not a superuser**, **not the table owner**, and **lacks the `BYPASSRLS` attribute** will be **completely blocked** from reading or writing rows if no permissive policy exists.
- Running standard table grants such as:
  ```sql
  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO luxe_app_user;
  ```
  grants table-level permissions, **but does NOT bypass RLS**. Every `SELECT` query will return zero rows, and every `INSERT`/`UPDATE`/`DELETE` statement will fail with:
  `ERROR: new row violates row-level security policy for table "..."`
- Therefore, the candidate migration's current posture (enabling RLS on all 11 tables with zero policies) would cause the runtime backend to fail immediately if connected under a non-owner, non-superuser role without explicit policies!

#### Evaluation of Resolution Strategies

| Strategy | Implementation | Security & Architectural Assessment | Verdict |
|---|---|---|---|
| **1. Explicit Runtime Policies (Least Privilege)** | Create policy on all 11 tables:<br>`CREATE POLICY app_runtime_all ON public.<table> FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);` | **High Security / Least Privilege:** `luxe_app_user` can read/write rows for application workflows without `BYPASSRLS` or superuser rights. PostgREST roles (`anon`, `authenticated`) remain 100% blocked by default-deny. | **RECOMMENDED** |
| **2. Table Ownership** | `ALTER TABLE public.<table> OWNER TO luxe_app_user;` | **Medium Security:** Table owners bypass RLS by default. However, this grants DDL authority (`DROP TABLE`, `ALTER TABLE`) to the runtime role, violating separation of concerns. | **REJECTED** |
| **3. Role Attribute `BYPASSRLS`** | `ALTER ROLE luxe_app_user BYPASSRLS;` | **Low Security / Broad Grant:** Completely turns off RLS for the role across the entire database. If credentials leak, database-level RLS provides zero defense. | **NOT RECOMMENDED** |

**Actionable Architecture Recommendation:**
Include an explicit application runtime policy block for `luxe_app_user` on all 11 tables in the deployment sequence, ensuring seamless backend operations while maintaining strict fail-closed protection against external PostgREST callers.

---

### 21.2 Deep Semantic Parity Analysis: Exact Parity vs. Apparent Parity

A rigorous static analysis was conducted comparing PostgreSQL runtime semantics against SQLAlchemy ORM definitions in [`database.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/database.py):

#### 1. Column Types & Physical Storage
- **Strings:** SQLAlchemy `Column(String)` maps to PostgreSQL `VARCHAR` (unbounded). In PostgreSQL, `VARCHAR` without a length specifier and `TEXT` share identical storage representation (varlena with toast support) and identical indexing mechanics. The candidate SQL uses `VARCHAR` for standard string fields and `TEXT` for unbounded text payloads (`description`, `ai_interpretation`, etc.). **Status: Exact Semantic Match.**
- **Floating Point Numbers:** SQLAlchemy `Column(Float)` maps to `DOUBLE PRECISION` (8 bytes, IEEE 754). The candidate SQL explicitly defines `DOUBLE PRECISION` across all 13 floating-point attributes (`confidence`, `momentum`, `strength`, `contrast`, `opportunity_score`, etc.). **Status: Exact Physical Match.**
- **Timestamps:** SQLAlchemy `Column(DateTime(timezone=True))` maps to `TIMESTAMP WITH TIME ZONE` (`TIMESTAMPTZ`). The candidate SQL defines `TIMESTAMPTZ` for all temporal columns (`created_at`, `updated_at`, `timestamp`, `training_start`, `training_end`). **Status: Exact Temporal Match.**
- **Integers:** SQLAlchemy `Column(Integer)` maps to `INTEGER` (4 bytes). Used for `images.width` and `images.height`. **Status: Exact Match.**

#### 2. Defaults and Client-Side ORM Behaviors
- **`updated_at` Automatic Updates:** In SQLAlchemy `User` and `Trend`, `onupdate=now_utc` is a **client-side ORM hook**. The database table defines `updated_at TIMESTAMPTZ DEFAULT now()`, which populates the initial insertion timestamp. However, PostgreSQL does **not** update `updated_at` during raw SQL `UPDATE` statements unless a `BEFORE UPDATE` trigger function is defined. Because all application mutations occur via SQLAlchemy ORM sessions (`db.commit()`), this behavior is completely consistent.
- **UUID Primary Key Generation:** In SQLAlchemy, primary keys are generated client-side in Python (`default=lambda: str(uuid.uuid4())`). The candidate SQL defines `id VARCHAR PRIMARY KEY` without a database-level default (`gen_random_uuid()`). Inserts via the application always supply the UUID. If direct database seeding is performed outside SQLAlchemy, UUIDs must be generated explicitly.
- **Aliased Attribute Mapping:** In `Forecast`, the database column is named `confidence`, but the SQLAlchemy attribute is aliased: `backtest_accuracy = Column("confidence", Float, nullable=False)`. The candidate schema preserves `confidence DOUBLE PRECISION NOT NULL`, ensuring complete backward compatibility with database schema conventions.

---

### 21.3 SQL Safety, Search Path, and Privileged Operations Review

1. **Destructive Operations:** Static scanning of `luxe_phase12_canonical_candidate_migration.sql` confirmed **zero destructive statements**:
   - `DROP TABLE` $\to$ 0 instances
   - `DROP SCHEMA` $\to$ 0 instances
   - `DROP DATABASE` $\to$ 0 instances
   - `TRUNCATE` $\to$ 0 instances
   - `DROP ... CASCADE` $\to$ 0 instances
2. **Search Path Hardening:**
   - All object declarations in the candidate migration are explicitly schema-qualified with `public.` (`CREATE TABLE public.users`, `REFERENCES public.trends(id)`, `ALTER TABLE public.users ...`).
   - **Recommended Defense-in-Depth Addition:** Prepend the migration script with an explicit search path reset to prevent search-path injection when executed by administrative roles:
     ```sql
     SET search_path = public, pg_temp;
     ```
3. **Public Grants & Privileged Assumptions:**
   - The candidate migration issues zero `GRANT` statements to `public`, `anon`, or `authenticated`.
   - The script assumes execution under an administrative deployment role (`postgres` or `supabase_admin`) capable of creating tables in `public` and altering table RLS settings.

---

### 21.4 Custom Application JWT vs. Database Runtime Role Boundary

The security review identified a critical architectural distinction that must be maintained across all deployment and operations documentation:

```
[Web Client] 
     │ (HTTPS + Custom HS256 JWT)
     ▼
[FastAPI Backend Application]
     ├── Decodes custom JWT via SECRET_KEY
     ├── Evaluates User ID & Role (admin / lead_analyst vs user)
     ├── Enforces Domain Permissions & Tenancy Filters (WHERE user_id = :id)
     │ 
     │ (PostgreSQL Connection Pool over Port 6543 / 5432)
     │ (Authenticated as single database role: 'luxe_app_user')
     ▼
[Supabase PostgreSQL Database]
     ├── Authenticates connection as 'luxe_app_user'
     ├── Evaluates Table Permissions (SELECT, INSERT, UPDATE, DELETE)
     ├── Evaluates RLS Policies (Allows luxe_app_user via runtime policy)
     └── Blocks direct PostgREST calls from 'anon' / 'authenticated'
```

- **Key Architectural Fact:** The PostgreSQL database **does not authenticate individual end users**. The database connection pool connects as a single trusted service role (`luxe_app_user`).
- **Security Boundary:** Multi-tenancy isolation (e.g. ensuring User A only accesses User A's saved trends) is enforced **at the application layer in FastAPI**.
- **Role of Database RLS:** In this architecture, database Row Level Security serves as a **perimeter firewall** preventing unauthorized access through Supabase's auto-generated PostgREST HTTP APIs, rather than managing per-user session tenancy.

---

### 21.5 Storage Bucket Audit & Exposure Prevention Verification

- **Public Buckets (`trend-images`, `collections`):**
  - Intended Content: Curated fashion trend photography, seasonal capsule lookbooks, and swatch palettes.
  - Access Pattern: Public CDN read access (`/storage/v1/object/public/...`). Write access restricted to backend service role.
- **Private Bucket (`user-uploads`):**
  - Intended Content: Proprietary user sketches, personal inspiration images, and uploaded search queries.
  - Access Pattern: Strictly private. Public URL generation is rejected with `ValueError` in [`supabase_service.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/services/supabase_service.py#L85-L87). Accessible strictly via short-lived signed URLs (1-hour expiry).
  - Storage Path Namespacing: Upload paths are prefixed with user identity (`{user_id}/{uuid}_{safe_filename}`), preventing path traversal and object enumeration.
  - Local Fallback Protection: Local serving endpoint `/api/images/local/user-uploads/{filepath}` verifies JWT credentials and enforces that non-privileged callers can only view files prefixed with their own `user_id`.
- **Remote Bucket Provisioning Requirement:** When creating the buckets in the Supabase Management Console or API, `user-uploads` must be created with `public: false`.

---

### 21.6 Migration Runbook & Rollback Strategy Evaluation

Section 8 of `PHASE_12_DEPLOYMENT_RUNBOOK.md` was reviewed for operational safety:
- **Flawed Assumption in Naive Rollbacks:** The runbook's initial mention of dropping tables if smoke tests fail is only valid during the **pre-launch maintenance window** before live users exist.
- **Post-Launch Danger:** Once users have registered and generated data, any `DROP TABLE` action causes irreversible data destruction.
- **Recommended Recovery Strategy:**
  1. **Pre-Launch Failure (Day 0 Deployment Window):** Execute transaction rollback (`ROLLBACK;`) if the migration transaction fails. If smoke tests fail post-commit, restore the target database from the pre-migration snapshot taken in Step 2.
  2. **Post-Launch Failure (Subsequent Schema Updates):** Forward-fix via non-destructive compensating migrations, or restore from Point-in-Time Recovery (PITR) to a specific validated timestamp.

---

### 21.7 Migration Ledger, Idempotency, and History Tracking

- **Idempotency Assessment:** The candidate SQL uses standard `CREATE TABLE public.<name>` statements without `IF NOT EXISTS`. This design is intentional for fresh-install deployments to fail immediately if an unexpected table already exists, preventing accidental schema corruption.
- **History Tracking Requirement:** To prevent a second execution from aborting or corrupting state, the deployment process must track applied migrations:
  - If using the **Supabase CLI**, migrations placed in `supabase/migrations/` are automatically recorded in `supabase_migrations.schema_migrations`.
  - If applying manually via SQL runner, the deployment script must create and check a schema version ledger:
    ```sql
    CREATE TABLE IF NOT EXISTS public._schema_version (
        version VARCHAR PRIMARY KEY,
        applied_at TIMESTAMPTZ DEFAULT now(),
        applied_by VARCHAR DEFAULT current_user
    );
    INSERT INTO public._schema_version (version) VALUES ('20261010_canonical_initial_v1');
    ```

---

### 21.8 Compatibility of Password-Hash and Image-Ownership Decisions

1. **Password-Hash Nullability:**
   - Registration flow (`POST /api/auth/register`): Hashes incoming password via PBKDF2 (`hash_password`) and stores it.
   - Login flow (`POST /api/auth/login`): Rejects any user with `password_hash IS NULL`.
   - Seed routine (`database_seed.py`): Seeds `analyst@luxe.tech` with `password_hash = NULL`.
   - Compatibility: Keeping `password_hash` nullable in the candidate baseline preserves 100% backward compatibility with demo seed routines and test suites. Production hardening will enforce `NOT NULL` after credentials are populated.
2. **Image Ownership:**
   - Application flow (`POST /api/images/analyze`): Writes exploratory image metadata to `ImageRecord` without requiring a `user_id` column. User attribution is encoded in `storage_path` (`{user_id}/{uuid}_{safe_filename}`).
   - Compatibility: Matches the 13 columns of `ImageRecord` in `database.py`. No runtime errors or column mismatch exceptions occur. Staged migration for relational `user_id` is documented and ready.

---

### 21.9 Prioritized Deployment Blockers List (Phase 13 Review)

| Priority | Blocker / Requirement | Action Required Before Production Deployment |
|---|---|---|
| **CRITICAL** | **PostgreSQL RLS Runtime Role Lockout** | Add explicit application runtime policies on all 11 tables (`FOR ALL TO luxe_app_user USING (true) WITH CHECK (true)`). Without these policies, enabling RLS will lock out the backend entirely under default-deny. |
| **CRITICAL** | **Remote Target Empty Baseline Verification** | Connect to the dedicated Supabase project to verify that the `public` schema is empty before applying DDL. |
| **HIGH** | **Automated Backup / PITR Baseline Sign-Off** | Verify that daily automated snapshots or PITR are operational in the Supabase management console. |
| **HIGH** | **Least-Privilege Database Role Creation** | Provision `luxe_app_user` with specific DML grants (`SELECT, INSERT, UPDATE, DELETE`) on `public` tables, and update `DATABASE_URL` to connect using this role rather than `postgres`. |
| **HIGH** | **Storage Bucket Provisioning** | Create `trend-images` (public), `collections` (public), and `user-uploads` (private) in Supabase Storage with 10 MB size limits and image MIME restrictions. |
| **MEDIUM** | **Migration History Ledger Integration** | Ensure candidate SQL execution is recorded in `supabase_migrations.schema_migrations` or `public._schema_version` to prevent re-execution conflicts. |
| **MEDIUM** | **Administrative Password Population** | Assign a salted PBKDF2 hash to `analyst@luxe.tech` and apply `ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL;`. |

---

### 21.10 Explicit Statement of Remotely Unverified Properties

The following properties cannot be established from local source analysis alone and remain **UNVERIFIED**:

1. **Remote Target Database State:** The dedicated Supabase PostgreSQL database has not been connected to; existing tables, schema conflicts, or installed extensions remain uninspected.
2. **Remote Storage Bucket Configuration:** Remote storage buckets have not been created, inspected, or verified in the Supabase management console.
3. **Transaction Pooler Under Live Application Load:** Connection behavior with psycopg prepared statements disabled (`prepare_threshold=None`) on Supabase port 6543 has not been validated against the live database.
4. **Remote Role & Policy Permissions:** Remote PostgreSQL role behavior (`luxe_app_user` vs `postgres` vs `anon`) has not been tested against live Supabase RLS enforcement.

**Phase 13 was conducted strictly offline. No cloud changes, remote queries, or database migrations have been executed. Awaiting explicit user approval before proceeding to deployment.**


---

## 22. Phase 14 RLS Architecture Resolution, Schema Semantics Validation, and Pre-Deployment Readiness (Dated: October 10, 2026)

### 22.1 Executive Summary of Phase 14

Following the Phase 13 independent safety audit, Phase 14 conducted a comprehensive resolution of the PostgreSQL Row Level Security (RLS) runtime architecture, completed an exhaustive semantic validation between the candidate DDL and SQLAlchemy ORM models, reviewed migration recovery safety and storage integration, and established a formalized pre-deployment verification gateway.

**Key Accomplishments in Phase 14:**
1. **RLS Architecture Resolved:** Formally evaluated three architectural approaches for reconciling PostgreSQL RLS with FastAPI's custom JWT authentication. Formally adopted **Option 1: Explicit `luxe_app_user` Runtime Policies** as the least-privilege, pooler-safe standard.
2. **Schema Semantics Validated:** Validated 100% semantic parity across all 11 tables, 113 columns, 12 indexes, foreign keys, delete cascades, and unique constraints between `supabase/proposals/luxe_phase12_canonical_candidate_migration.sql` and `backend/app/database.py`.
3. **Migration & Recovery Safety Documented:** Defined atomic transaction boundaries (`BEGIN ... COMMIT`), established the strict operational distinction between Day-0 Fresh Install Abort and Post-Launch Disaster Recovery, and instituted a permanent prohibition against `DROP TABLE ... CASCADE` post-launch.
4. **Storage Architecture Validated:** Verified public vs. private bucket partitioning, 10 MB bounded chunked reading, image MIME/signature enforcement, user-namespaced storage paths, and 3600-second signed URL expiration.
5. **Phase 14 Deliverables Created:**
   - [`PHASE_14_RLS_ARCHITECTURE_DECISION.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_14_RLS_ARCHITECTURE_DECISION.md)
   - [`PHASE_14_PREDEPLOYMENT_CHECKLIST.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_14_PREDEPLOYMENT_CHECKLIST.md)
6. **Zero Remote Connections:** Conducted strictly offline with zero remote database connections, zero SQL executions, and zero modifications to production configurations.

---

### 22.2 RLS Architecture Resolution: Comparison and Decision

#### The Core Problem
Under PostgreSQL, enabling RLS on a table (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY`) without defining active policies activates **default-deny**. All queries executed by non-owner roles lacking `BYPASSRLS` return zero rows or fail. Standard SQL permissions (`GRANT SELECT, INSERT...`) do not override RLS. Connecting the FastAPI backend using a dedicated least-privilege role (`luxe_app_user`) while RLS is enabled with zero policies would lock out the application entirely.

#### Evaluation of Architectural Options

| Evaluation Dimension | Option 1: Explicit `luxe_app_user` Policies | Option 2: Transaction-Scoped Context (`SET LOCAL`) | Option 3: Elevated Role Attributes (`BYPASSRLS` / Owner) |
|---|---|---|---|
| **SQL Policy Pattern** | `CREATE POLICY app_runtime_all ON public.<table> FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);` | `CREATE POLICY user_iso ON public.<table> FOR ALL TO luxe_app_user USING (user_id = current_setting('luxe.uid', true));` | No policies; `ALTER ROLE luxe_app_user WITH BYPASSRLS;` or `ALTER TABLE ... OWNER TO luxe_app_user;` |
| **PostgREST Fail-Closed Perimeter** | **YES.** `anon` and `authenticated` roles have 0 policies; all external REST calls return `[]` or 401/403. | **YES.** `anon` and `authenticated` roles have 0 policies. | **YES.** External PostgREST calls are still blocked. |
| **Connection Pooler Leakage Risk (PgBouncer)** | **ZERO RISK.** Completely stateless. No session GUC variables used. Immune to pooler context pollution. | **HIGH RISK.** In transaction pooling mode (port 6543), failure to clear `SET LOCAL` on error leaks user context to next client. | **ZERO RISK.** Completely stateless. |
| **Role Least Privilege** | **EXCELLENT.** `NOBYPASSRLS`, `NOSUPERUSER`, `NOCREATEDB`, DML grants only. Zero DDL authority. | **EXCELLENT.** `NOBYPASSRLS`, DML grants only. | **POOR.** Grants global RLS bypass or destructive table DDL ownership (`DROP`, `TRUNCATE`). |
| **Public Catalog Reads** | **SEAMLESS.** Public discovery queries run under `luxe_app_user` without synthesizing user identity. | **COMPLEX.** Requires awkward fallback logic for unauthenticated catalog queries. | **SEAMLESS.** Queries run without user context. |
| **FastAPI / SQLAlchemy Complexity** | **ZERO.** Works out-of-the-box with existing SQLAlchemy models and session lifecycle. | **VERY HIGH.** Requires intercepting every session/transaction to inject `SET LOCAL` statements. | **ZERO.** Works out-of-the-box. |
| **Architectural Fit** | **PERFECT.** Matches LUXE.TECH standalone architecture (custom JWT, decoupled backend). | **POOR.** Tries to force multi-tenant DB policies onto an application-authenticated architecture. | **COMPROMISED.** Disables DB security perimeter for convenience. |

#### Formal Decision: Option 1 Adopted
LUXE.TECH formally adopts **Option 1: Explicit `luxe_app_user` Runtime Policies**.
- Preserves the PostgREST fail-closed perimeter.
- Guarantees multi-tenant connection pooler safety on Supabase port 6543.
- Enforces strict least privilege on the backend database role (`luxe_app_user`).
- Maintains clean separation of concerns: FastAPI enforces domain authorization and user isolation; PostgreSQL RLS locks out unauthenticated external access.

---

### 22.3 Exhaustive Schema Semantic Parity Analysis

A comprehensive comparison between `supabase/proposals/luxe_phase12_canonical_candidate_migration.sql` and `backend/app/database.py` confirmed 100% semantic parity across all 11 application tables:

| Table | Columns | Primary Key | Foreign Keys & Actions | Unique Constraints & Indexes | Semantic Nuances & Equivalences |
|---|:---:|---|---|---|---|
| `users` | 7 | `id` (VARCHAR) | None | `ix_users_email` (UNIQUE) | `password_hash` nullable for initial bootstrap; `updated_at` updated client-side via SQLAlchemy `onupdate=now_utc`. |
| `trends` | 14 | `id` (VARCHAR) | None | `ix_trends_slug` (UNIQUE), `ix_trends_category` | Default confidence (80.0), momentum (25.0), velocity (15.0), acceleration (5.0), season ('SS 2027'). |
| `trend_signals` | 9 | `id` (VARCHAR) | `trend_id -> trends.id` (ON DELETE CASCADE) | `ix_trend_signals_trend_id` | `metadata_json` default `'{}'`; JSON serialization managed via ORM property getter/setter. |
| `trend_dna` | 11 | `id` (VARCHAR) | `trend_id -> trends.id` (ON DELETE CASCADE, UNIQUE) | Unique constraint on `trend_id` | 1-to-1 relationship enforced via UNIQUE constraint; array JSON columns default to `'[]'`. |
| `images` | 13 | `id` (VARCHAR) | `trend_id -> trends.id` (ON DELETE SET NULL) | `ix_images_trend_id` | Initial baseline has 13 columns (matches `ImageRecord`). User attribution namespaced in `storage_path`. |
| `collections` | 10 | `id` (VARCHAR) | `trend_id -> trends.id` (ON DELETE CASCADE) | `ix_collections_trend_id` | 6 JSON array columns default to `'[]'`. |
| `products` | 12 | `id` (VARCHAR) | `trend_id -> trends.id` (ON DELETE SET NULL) | `ix_products_trend_id` | `opportunity_score` default 75.0; nullable `trend_id` and `ai_reasoning`. |
| `retail_signals` | 8 | `id` (VARCHAR) | `trend_id -> trends.id` (ON DELETE SET NULL) | `ix_retail_signals_trend_id` | Demand and growth metrics stored as `DOUBLE PRECISION`. |
| `forecasts` | 10 | `id` (VARCHAR) | `trend_id -> trends.id` (ON DELETE CASCADE) | `ix_forecasts_trend_id` | Column named `confidence` in SQL; mapped in SQLAlchemy as `backtest_accuracy = Column("confidence", Float)`. |
| `prophecy` | 9 | `id` (VARCHAR) | `trend_id -> trends.id` (ON DELETE CASCADE) | `ix_prophecy_trend_id` | 5 predictive stages; `evidence_json` default `'[]'`. |
| `saved_trends` | 4 | `id` (VARCHAR) | `user_id -> users.id` (CASCADE), `trend_id -> trends.id` (CASCADE) | `ix_saved_trends_user_id`, `ix_saved_trends_trend_id`, `uq_saved_trends_user_trend` (UNIQUE) | Compound unique constraint prevents duplicate bookmarks per user. |

#### Semantic Distinctions Documented:
1. **Data Types:** SQLAlchemy `String` maps to PostgreSQL `VARCHAR`; `Float` maps to `DOUBLE PRECISION`; `DateTime(timezone=True)` maps to `TIMESTAMPTZ`; `Text` maps to `TEXT`.
2. **Client-Side Behaviors:**
   - UUIDs are generated client-side via Python `uuid.uuid4()`. Primary keys do not have database-side sequence or uuid generators.
   - `updated_at` timestamps are updated on ORM mutations via `onupdate=now_utc`. PostgreSQL will not update `updated_at` on direct SQL `UPDATE` queries unless a trigger is attached.
3. **Live Database Assumptions:**
   - PostgreSQL timezone assumed to be `UTC`.
   - Foreign key indexes are created explicitly in SQL DDL because PostgreSQL does not automatically index foreign keys.
   - Remote target database assumed to have clean `public` schema.

---

### 22.4 Migration Execution and Recovery Safety

1. **Transactional Safety:** Candidate migration DDL must execute inside an explicit atomic transaction (`BEGIN; ... COMMIT;`). Any failure midway immediately triggers an automatic `ROLLBACK`, leaving the database clean.
2. **Day-0 Fresh Install Abort vs. Post-Launch Disaster Recovery:**
   - **Day-0 Fresh Install Abort:** If an error occurs during initial deployment on a clean, empty database, rolling back or executing clean-up DDL (`DROP TABLE ... CASCADE`) is permissible because zero production or user data exists.
   - **Post-Launch Disaster Recovery:** Once production user accounts or operational data exist, **`DROP TABLE ... CASCADE` is permanently forbidden**. Recovery from schema defects must use forward-repair migrations (`ALTER TABLE`). Recovery from data corruption must use Point-in-Time Recovery (PITR) or daily automated snapshots.
3. **Mandatory Deployment Prerequisites:**
   - Verify automated backup / PITR is active in Supabase project settings.
   - Verify that `public` schema in the dedicated project contains 0 application tables.
   - Provision `luxe_app_user` with restricted DML privileges before updating application connection strings.

---

### 22.5 Storage Architecture and Application Integration Audit

1. **Bucket Partitioning:**
   - `trend-images` (Public): Catalog imagery, accessible via direct public CDN URLs.
   - `collections` (Public): Lookbook capsules, accessible via direct public CDN URLs.
   - `user-uploads` (Private): Personal user sketches and inspiration uploads, accessible **strictly via temporary signed URLs** (3600-second expiration).
2. **Upload Security Controls:**
   - 10 MB strict payload limit enforced via bounded chunked reading (64 KB chunks) before memory buffering.
   - MIME type and file extension whitelist (`.jpg`, `.jpeg`, `.png`, `.webp`).
   - Magic byte signature verification and Pillow pixel dimension decoding (minimum 10x10 px).
   - Filename sanitization (`[^a-zA-Z0-9._-]`) and user namespacing (`{user_id}/{uuid}_{safe_filename}`).
3. **Remotely Dependent Assumptions:**
   - Storage buckets must be provisioned in the Supabase management console with appropriate public/private visibility flags and file size constraints prior to application connection.

---

### 22.6 Summary of Created Phase 14 Artifacts

1. [`supabase/proposals/PHASE_14_RLS_ARCHITECTURE_DECISION.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_14_RLS_ARCHITECTURE_DECISION.md):
   Full architectural decision record comparing the 3 RLS approaches, evaluating connection pooler safety, role attributes, and specifying the 11 explicit runtime policies for `luxe_app_user`.
2. [`supabase/proposals/PHASE_14_PREDEPLOYMENT_CHECKLIST.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_14_PREDEPLOYMENT_CHECKLIST.md):
   Structured 8-phase pre-deployment verification checklist covering pre-flight checks, baseline inspection, role creation, migration execution, RLS audit, storage provisioning, smoke testing, and abort protocols.

---

### 22.7 Unresolved Governance Decisions Requiring User Approval

Before any deployment steps are executed, the following governance decisions must be formally approved by the project owner:

1. **Authentication Architecture Approval:** Confirm that LUXE.TECH will continue using FastAPI custom JWT as the primary authentication engine for Phase 15.
2. **Timing of Relational Image Ownership (`images.user_id`):** Confirm retaining 13 columns in the initial baseline table for exact Day-0 parity, deferring the `images.user_id` foreign key addition to Migration 003.
3. **Remote Environment Introspection Authorization:** Grant explicit permission to connect to the dedicated Supabase project to verify that the `public` schema is empty before applying DDL.

---

### 22.8 Explicit Re-affirmation of Safety and Zero Remote Connections

**Phase 14 was conducted strictly offline. No remote database connections, cloud queries, bucket modifications, or database migrations have been executed. All existing project data and configurations remain completely untouched. Awaiting explicit user approval before proceeding to deployment.**


---

## 23. Phase 15 Read-Only Pre-Deployment Inspection Preflight & Safety Gate (Dated: October 10, 2026)

### 23.1 Executive Summary & Verification State

Phase 15 establishes the final local safety gate before inspecting the live dedicated Supabase target.

**CRITICAL VERIFICATION DISTINCTION:**
- **No remote database connection has been initiated in Phase 15.** Zero queries have been executed against the remote database in this phase.
- All prior observations regarding missing application tables, empty storage buckets, or installed extensions are **historical observations from the Phase 06 baseline audit**, NOT freshly verified in Phase 15.
- The live database state in Phase 15 remains **UNVERIFIED (PENDING INSPECTION)** until explicit user authorization is provided.

---

### 23.2 Verification of `inspect_supabase_readonly.py` Safety Controls

The standalone inspection script [`inspect_supabase_readonly.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/inspect_supabase_readonly.py) was audited across 6 strict safety dimensions:
1. **Connection Handling & Pool Isolation:** Connects via a standalone `psycopg.connect(...)` call completely outside FastAPI's SQLAlchemy connection pool. Disposes application engine cleanly in `finally` block without executing queries on it. Uses `connect_timeout=10`.
2. **TLS & Transport Security:** Explicitly validates `sslmode=require` in the database URL and passes `sslmode="require"` in psycopg connection info. Unencrypted connections are rejected before socket transmission.
3. **Project Correlation Gate:** Verifies that the tenant reference extracted from the database username matches character-for-character the subdomain of `SUPABASE_URL` before attempting connection.
4. **Transaction Read-Only Verification:** Executes `BEGIN READ ONLY;` immediately. Queries `current_setting('transaction_read_only')`. If not `'on'`, immediately issues `ROLLBACK` and aborts (code 3) without executing any catalog inspection queries. Engine rejects any DDL/DML (`SQLSTATE 25006`).
5. **Unconditional Rollback & Savepoint Sandboxing:** Employs explicit `ROLLBACK` at completion. Metadata queries against `storage.buckets` and migration tables are isolated inside `SAVEPOINT` blocks so permission errors roll back cleanly without failing the read-only session.
6. **Secret Redaction & Exception Sanitization:** Database URLs, passwords, project references, database names, and raw role identities are suppressed from output. Exceptions are sanitized via `_connection_failure_category()`, emitting generic failure classifications rather than raw database error tracebacks.

---

### 23.3 Role Handling & No-Role-Creation Standard

- **Configured Role:** `postgres.[REDACTED-20-CHAR-REF]`. In Supabase, `postgres` holds table ownership and DDL/DML capabilities.
- **No Role Creation Recommended:** No new database roles (e.g. read-only inspector roles) will be created as part of this inspection. Creating unreviewed roles in the cloud database is premature and unnecessary.
- **Read-Only Enforcement Level:** Read-only behavior is guaranteed at the **PostgreSQL transaction level** via `BEGIN READ ONLY;` + `transaction_read_only=on` verification + unconditional `ROLLBACK;`.

---

### 23.4 Metadata Checks and Minimum Required Privileges

| Inspection Check | Catalog Query / Function | Target System Catalogs | Minimum Privilege Required |
|---|---|---|---|
| **1. Session & Transaction State** | `SELECT current_database(), current_user, current_schema(), current_setting('transaction_read_only');` | Built-in session functions | `CONNECT` on database (available to any authenticated connection). |
| **2. Role Capabilities** | `SELECT rolsuper, rolbypassrls, has_table_privilege(...) FROM pg_catalog.pg_roles WHERE rolname = current_user;` | `pg_catalog.pg_roles` | Public access to own role record in `pg_roles`. |
| **3. Table Inventory** | `SELECT table_schema, table_name, table_type FROM information_schema.tables WHERE ...;` | `information_schema.tables` | Public read on `information_schema` (only shows tables with grants or ownership). |
| **4. Column Inventory & Types** | `SELECT column_name, data_type, udt_name, is_nullable, column_default, ... FROM information_schema.columns WHERE ...;` | `information_schema.columns` | Public read on `information_schema` (only shows columns with grants or ownership). |
| **5. RLS Activation & Status** | `SELECT n.nspname, c.relname, c.relkind, c.relrowsecurity, c.relforcerowsecurity FROM pg_catalog.pg_class c ...;` | `pg_catalog.pg_class`, `pg_catalog.pg_namespace` | Default public read on `pg_catalog`. |
| **6. Constraints (PK, FK, Unique)** | `SELECT conname, contype, pg_get_constraintdef(con.oid, true) FROM pg_catalog.pg_constraint con ...;` | `pg_catalog.pg_constraint`, `pg_catalog.pg_class` | Default public read on `pg_catalog`. |
| **7. Index Definitions** | `SELECT schemaname, tablename, indexname, indexdef FROM pg_catalog.pg_indexes WHERE ...;` | `pg_catalog.pg_indexes` | Default public read on `pg_catalog`. |
| **8. Row Level Security Policies** | `SELECT schemaname, tablename, policyname, roles, cmd, qual, with_check FROM pg_catalog.pg_policies WHERE ...;` | `pg_catalog.pg_policies` | Default public read on `pg_catalog` (PostgreSQL 10+). |
| **9. Table-Level Grants** | `SELECT table_schema, table_name, grantee, privilege_type, is_grantable FROM information_schema.table_privileges WHERE ...;` | `information_schema.table_privileges` | Public read on `information_schema.table_privileges`. |
| **10. Storage Bucket Metadata** | `SELECT id, name, public FROM storage.buckets ORDER BY id;` *(via SAVEPOINT)* | `storage.buckets` | `USAGE ON SCHEMA storage`, `SELECT ON storage.buckets`, and RLS bypass or policy. |
| **11. Extension Verification** | `SELECT extname FROM pg_catalog.pg_extension WHERE extname = 'uuid-ossp';` | `pg_catalog.pg_extension` | Default public read on `pg_catalog.pg_extension`. |
| **12. Trigger Inventory** | `SELECT tg.tgname, tbl.relname, pg_get_triggerdef(tg.oid, true) FROM pg_catalog.pg_trigger tg ...;` | `pg_catalog.pg_trigger`, `pg_catalog.pg_class` | Default public read on `pg_catalog`. |
| **13. Migration Ledger Discovery** | `SELECT <version_columns> FROM <schema>.<migration_table> LIMIT 100;` *(via SAVEPOINT)* | `public.alembic_version`, `public.schema_migrations`, `supabase_migrations.schema_migrations` | `USAGE ON SCHEMA <schema>` and `SELECT ON <table_name>`. |

---

### 23.5 Discrepancy Baseline Taxonomy & Historical Status

Findings from the live inspection will be categorized against `luxe_phase12_canonical_candidate_migration.sql`:
- **VERIFIED:** Remote catalog object matches candidate migration exactly.
- **MISSING:** Expected candidate object is not present in the remote catalog (and sufficient privileges exist to confirm its absence).
- **CONFLICT:** Remote object exists but differs in type, nullability, default, or constraint.
- **UNVERIFIED:** Object or attribute cannot be confirmed due to privilege or visibility limits.
- **REQUIRES USER DECISION:** Finding requires project owner sign-off.

#### Current Status of Baseline Knowledge:
- **11 Application Tables:** Not visible in Phase 06 baseline $\rightarrow$ **UNVERIFIED (PENDING INSPECTION)** in Phase 15.
- **113 Application Columns:** Not visible in Phase 06 baseline $\rightarrow$ **UNVERIFIED (PENDING INSPECTION)** in Phase 15.
- **12 Application Indexes:** Not visible in Phase 06 baseline $\rightarrow$ **UNVERIFIED (PENDING INSPECTION)** in Phase 15.
- **11 Table RLS Statements:** Not visible in Phase 06 baseline $\rightarrow$ **UNVERIFIED (PENDING INSPECTION)** in Phase 15.
- **Storage Buckets:** Zero visible bucket rows in Phase 06 baseline $\rightarrow$ **UNVERIFIED (PENDING INSPECTION)** in Phase 15.
- **Extension `uuid-ossp`:** Installed in Phase 06 baseline $\rightarrow$ **UNVERIFIED (PENDING INSPECTION)** in Phase 15.
- **Migration History Ledger:** **NO RECOGNIZED MIGRATION LEDGER VISIBLE (HISTORICAL)**. (The absence of visible migration tables in Phase 06 does not prove that unrecorded DDL was never applied).

---

### 23.6 Pre-Connection Authorization Report

- **Sanitized Target Host:** `aws-0-ap-northeast-1.pooler.supabase.com` (Port 6543) / `db.[REDACTED-20-CHAR-REF].supabase.co` (Port 5432).
- **Connection Method:** Standalone script `inspect_supabase_readonly.py` via psycopg 3 over TLS (`sslmode=require`).
- **Database Role:** `postgres.[REDACTED-20-CHAR-REF]`.
- **How Read-Only Behavior Will Be Enforced:** `BEGIN READ ONLY;` + `transaction_read_only=on` verification + unconditional `ROLLBACK;`.
- **Data Protection:** Catalog queries only; zero user rows, passwords, or image payloads queried.
- **Remaining Blockers:** None locally. The script is verified safe. Only user authorization to initiate the connection is required.

---

### 23.7 Safety Confirmation

**No remote database connection was initiated during Phase 15. Zero remote resources, tables, roles, or configurations were modified. All operations were local and preparatory. Awaiting explicit user authorization before connecting.**


---

## 24. Phase 16 Canonical First-Install Setup & Supabase Preparation (Dated: October 10, 2026)

### 24.1 Executive Summary of Phase 16

Phase 16 prepared the complete, reviewed first-install database schema artifacts, permission design, deployment checklist, and offline validation report for the LUXE.TECH application schema in the dedicated Supabase project.

**Core Achievements:**
1. **Complete First-Install Script Authored:** Created [`supabase/proposals/luxe_phase16_canonical_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_canonical_first_install.sql), achieving 100% parity with SQLAlchemy models (11 tables, 113 columns, 12 indexes).
2. **RLS Runtime-Access Problem Resolved:** Solved the default-deny lockout without granting `BYPASSRLS`, using a superuser at runtime, or exposing data to public PostgREST roles. The script provisions least-privilege role `luxe_app_user` (`NOSUPERUSER`, `NOCREATEDB`, `NOREPLICATION`, `NOBYPASSRLS`) with explicit table-level policies (`CREATE POLICY app_runtime_all ON public.<table> FOR ALL TO luxe_app_user USING (true) WITH CHECK (true)`).
3. **Fail-Closed PostgREST Security:** Enforced `REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;`, ensuring direct REST requests via Supabase API return zero data.
4. **Decoupled Storage Provisioning:** Separated storage bucket setup into a dedicated proposal [`supabase/proposals/luxe_phase16_storage_setup_proposal.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql), keeping table DDL clean and reviewable.
5. **Phase 16 Deliverables Suite:**
   - Candidate Initial Migration SQL: [`supabase/proposals/luxe_phase16_canonical_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_canonical_first_install.sql)
   - Database Permission & RLS Design: [`supabase/proposals/PHASE_16_DATABASE_PERMISSIONS_AND_RLS_DESIGN.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_16_DATABASE_PERMISSIONS_AND_RLS_DESIGN.md)
   - Supabase SQL Editor Deployment Checklist: [`supabase/proposals/PHASE_16_SQL_EDITOR_DEPLOYMENT_CHECKLIST.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_16_SQL_EDITOR_DEPLOYMENT_CHECKLIST.md)
   - Offline Validation Report: [`supabase/proposals/PHASE_16_OFFLINE_VALIDATION_REPORT.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_16_OFFLINE_VALIDATION_REPORT.md)
6. **Local Parity Validation Passed (100%):** Validated via `validate_phase16_sql.py` with zero errors.
7. **Zero Remote Modification:** Conducted strictly offline. No remote SQL was executed and no cloud resources were altered.

---

### 24.2 Parity and Security Verification Results

The offline validator confirmed:
- **Tables:** Exactly 11 matching tables.
- **Columns:** Exactly 113 columns matching names, data types, and nullability.
- **Indexes:** Exactly 12 explicit indexes correctly defined.
- **Row Level Security:** 11/11 tables have RLS enabled.
- **Runtime Policies:** 11/11 tables have explicit `app_runtime_all` policies for `luxe_app_user`.
- **Role Attributes:** `luxe_app_user` has `NOSUPERUSER`, `NOCREATEDB`, `NOREPLICATION`, `NOBYPASSRLS`.
- **PostgREST Boundary:** `REVOKE ALL` enforced on all tables for `anon` and `authenticated`.
- **Destructive Operations:** Zero `DROP TABLE`, `TRUNCATE`, `DROP SCHEMA`, or `CASCADE` commands.

---

### 24.3 Unverified Live Assumptions

The following properties remain unverified offline and must be confirmed during execution:
1. **Target Schema Emptiness:** Assumes `public` schema in the dedicated Supabase project is clean with 0 existing application tables.
2. **PostgreSQL Version & Extensions:** Assumes compatibility with Supabase standard PostgreSQL 15+ cluster.
3. **Transaction Pooler Configuration:** Assumes FastAPI connections on port 6543 have psycopg prepared statements disabled (`prepare_threshold=None`).
4. **Storage Permissions:** Assumes Supabase Storage service role key has bucket administrative permissions.

---

### 24.4 Safety Confirmation

**Phase 16 was conducted strictly offline. No remote database connection was initiated, no SQL was executed on Supabase, and no cloud resources were modified. The application database is NOT deployed. All artifacts are staged for review under `supabase/proposals/`.**


---

## 25. Phase 17 Final First-Install SQL Safety Review (Dated: October 10, 2026)

### 25.1 Executive Summary of Phase 17

Phase 17 conducted a final, independent code safety audit of [`luxe_phase16_canonical_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_canonical_first_install.sql) and its accompanying operational artifacts.

**Key Achievements & Enhancements in Phase 17:**
1. **Narrow Scoping Enforced on Permissions:** Eliminated all broad wildcard `ON ALL TABLES IN SCHEMA public` clauses from `GRANT` and `REVOKE` statements. Scoped permissions explicitly and exclusively to the 11 LUXE.TECH tables, preventing any unintended side effects on pre-existing or third-party tables in `public`. Removed `ALTER DEFAULT PRIVILEGES IN SCHEMA public`.
2. **Multi-Catalog Baseline Verification Mandated:** Upgraded the pre-execution baseline check beyond a simple table count. The operator must inspect tables, views, materialized views, custom functions, public policies, table privileges, and installed extensions prior to execution.
3. **Safety Review Classified (7 Critical Items):** All 7 audit dimensions achieved a rating of **PASS** under local static analysis.
4. **Phase 17 Deliverables Created:**
   - [`PHASE_17_FINAL_SQL_SAFETY_REVIEW.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_17_FINAL_SQL_SAFETY_REVIEW.md)
   - [`PHASE_17_SQL_EDITOR_EXECUTION_CHECKLIST.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_17_SQL_EDITOR_EXECUTION_CHECKLIST.md)
5. **Zero Remote Activity:** Conducted strictly locally. Zero remote database queries, cloud modifications, or role creations were performed.

---

### 25.2 Findings Classification Summary

| Critical Review Item | Description & Findings | Safety Rating |
|:---:|---|:---:|
| **1. Existing-Object Safety** | `GRANT` and `REVOKE` statements are narrowly scoped to the 11 explicit LUXE.TECH tables. Zero impact on unrelated existing or future tables. | **PASS** |
| **2. Initial Baseline Verification** | Multi-catalog inspection script checks tables, views, matviews, routines, policies, grants, and extensions before running DDL. | **PASS** |
| **3. Role Creation & Idempotency** | Role `luxe_app_user` created with `NOSUPERUSER NOCREATEDB NOREPLICATION NOBYPASSRLS`. Wrapped in idempotent PL/pgSQL block. Password placeholder clearly flagged. | **PASS** |
| **4. RLS & Permissions Design** | Enabled on all 11 tables. Option 1 explicit policies grant DML to `luxe_app_user`. PostgREST fail-closed perimeter enforced. Supports FastAPI public reads and authenticated DML. | **PASS** |
| **5. Schema & Model Parity** | 100% parity across 11 tables, 113 columns, and 12 indexes against `database.py`. Image ownership (13 cols) deferred. | **PASS** |
| **6. Execution & Recovery Safety** | Atomic `BEGIN ... COMMIT` wrapping. Safe Day-0 abort plan. Strict post-launch ban on `DROP TABLE ... CASCADE`. | **PASS** |
| **7. Storage Architecture Separation** | Storage bucket setup decoupled into `luxe_phase16_storage_setup_proposal.sql`. Zero storage DDL inside table script. | **PASS** |

---

### 25.3 Remaining Blockers Before Human Operator Execution

Before executing the script in the Supabase SQL Editor:
1. **Password Substitution:** Replace `'REPLACE_WITH_STRONG_PASSWORD'` on line 31 of [`luxe_phase16_canonical_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_canonical_first_install.sql) with a secure runtime secret.
2. **Pre-Execution Baseline Confirmation:** Run the multi-catalog baseline query in the Supabase SQL Editor and confirm clean counts across tables, views, and routines.
3. **Operator Sign-Off:** Review the execution checklist in [`PHASE_17_SQL_EDITOR_EXECUTION_CHECKLIST.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_17_SQL_EDITOR_EXECUTION_CHECKLIST.md) and execute the reviewed DDL.

---

### 25.4 Safety Confirmation

**Phase 17 was conducted strictly offline. No remote database connection was initiated, no SQL was executed on Supabase, and no cloud resources were modified. The application database is NOT deployed. Staged for operator execution under `supabase/proposals/`.**


---

## 26. Phase 18 Local Migration Hardening (Dated: October 11, 2026)

### 26.1 Executive Summary of Phase 18

Phase 18 hardened the canonical first-install migration proposal while operating strictly offline.

**Key Hardening Accomplishments:**
1. **Preserved Phase 16 Proposal:** Maintained `supabase/proposals/luxe_phase16_canonical_first_install.sql` completely unchanged as an immutable reference.
2. **Created Separate Hardened Proposal:** Authored [`supabase/proposals/luxe_phase18_hardened_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase18_hardened_first_install.sql).
3. **Eliminated Executable Placeholder Credentials:** Removed all occurrences of `REPLACE_WITH_STRONG_PASSWORD` from executable DDL. Implemented a prerequisite guard block in PL/pgSQL that checks for the existence of `luxe_app_user` and raises an exception (`RAISE EXCEPTION`) if the role is missing, ensuring zero risk of accidental deployment with default credentials.
4. **Narrowly Scoped Permissions & Zero Schema Wildcards:** Scoped all `GRANT` and `REVOKE` statements strictly to the 11 LUXE.TECH tables. Excluded all schema-level wildcard statements (`ON ALL TABLES IN SCHEMA public`) and eliminated `ALTER DEFAULT PRIVILEGES`.
5. **Documented RLS Tenant Isolation Responsibility:** Explicitly recorded that `USING (true) WITH CHECK (true)` policies for `luxe_app_user` delegate per-user tenant boundaries to FastAPI. Verified that FastAPI dependencies (`get_current_user`, `get_privileged_user`) enforce ownership before executing database mutations.
6. **Re-runnability Honesty & Recovery Governance:** Explicitly documented that the migration is an **atomic, single-pass initial installation**, not an idempotent re-runnable patch. Re-running against existing tables will fail safely and roll back.
7. **Created Validation Report:** Authored [`supabase/proposals/PHASE_18_OFFLINE_VALIDATION_REPORT.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_18_OFFLINE_VALIDATION_REPORT.md), clearly distinguishing automated validator assertions from manual security audit findings.

---

### 26.2 Parity and Security Verification Summary

The automated validator [`validate_phase18_sql.py`](file:///c:/Users/Lenovo/.gemini/antigravity/brain/020c3539-9607-40fd-93e4-617cac098f78/scratch/validate_phase18_sql.py) confirmed 100% compliance:
- **11 Tables:** Exact match with `Base.metadata.tables`.
- **113 Columns:** Exact match with SQLAlchemy column names, data types, and nullability rules.
- **12 Indexes:** Exactly 12 explicit indexes correctly defined.
- **11/11 RLS Coverage:** Row Level Security enabled on all 11 tables.
- **11/11 Runtime Policies:** Explicit `app_runtime_all` policies granted to `luxe_app_user`.
- **Credential Safety:** Zero placeholder passwords; prerequisite role check enforced.
- **Permission Scoping:** Strictly scoped to the 11 tables; zero wildcard schema grants.
- **Destructive Operations:** Zero `DROP TABLE`, `TRUNCATE`, `DROP SCHEMA`, or `CASCADE` commands.

---

### 26.3 Required Deployment Checks & Rollback Plan

#### Required Deployment Checks:
1. **Pre-Provision Runtime Role:** Operator must create `luxe_app_user` in a private session before running the schema script:
   ```sql
   CREATE ROLE luxe_app_user WITH LOGIN PASSWORD '<secure_password>'
       NOSUPERUSER NOCREATEDB NOREPLICATION NOBYPASSRLS;
   ```
2. **Multi-Catalog Baseline Verification:** Verify in Supabase SQL Editor that `public` contains 0 existing tables, views, and routines.
3. **Automated Backup Active:** Confirm daily automated snapshots or PITR in Supabase project settings.

#### Rollback Plan:
- **During Initial Installation (Day-0):** The transaction will automatically execute `ROLLBACK;` upon any error, leaving 0 tables created. If partial objects exist outside a transaction on an unpopulated cluster, clean drop statements are permissible.
- **Post-Launch Production Rule:** **`DROP TABLE ... CASCADE` is permanently prohibited.** Data recovery must rely strictly on Supabase Point-in-Time Recovery (PITR) or daily automated snapshot restores. Schema modifications must be applied via forward migrations (`ALTER TABLE`).

---

### 26.4 Safety Confirmation

**Phase 18 was conducted strictly offline. No remote database connection was initiated, no SQL was executed on Supabase, and no cloud resources were modified. The application database is NOT deployed. Staged under `supabase/proposals/`.**

---

## 27. Phase 19 Schema Reconciliation & Forensic Parity Audit (Dated: October 11, 2026)

### 27.1 Forensic Resolution of Reported Table Names
During the conclusion of Phase 18, a verbal hallucination in the assistant's prose listed an alternative set of 11 tables (`fashion_trends`, `forecast_metrics`, `prophecy_records`, `design_recommendations`, `export_jobs`, `api_usage_metrics`, `system_logs`).

Phase 19 conducted a full codebase AST and regex audit:
1. **Zero Occurrences in Code:** The alternative table names have **0 occurrences** across all Python modules, routers, schemas, and migrations.
2. **Actual DDL Parity:** Both [`supabase/proposals/luxe_phase16_canonical_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_canonical_first_install.sql) and [`supabase/proposals/luxe_phase18_hardened_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase18_hardened_first_install.sql) define the exact same 11 canonical tables:
   `users`, `trends`, `trend_signals`, `trend_dna`, `images`, `collections`, `products`, `retail_signals`, `forecasts`, `prophecy`, `saved_trends`.
3. **Column Parity:** Both proposals achieve **100% exact parity** across all 113 columns against `Base.metadata.tables`.
4. **Backend Router & Query Verification:** All 38 backend files in `backend/app/` query only the canonical 11 tables and columns. All 42 tests in `backend/tests` pass cleanly.

### 27.2 Status of Migration Proposals
- [`supabase/proposals/luxe_phase16_canonical_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_canonical_first_install.sql): Preserved unchanged.
- [`supabase/proposals/luxe_phase18_hardened_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase18_hardened_first_install.sql): Preserved unchanged as the hardened candidate.
- Detailed audit documentation: [`PHASE_19_SCHEMA_RECONCILIATION_REPORT.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/PHASE_19_SCHEMA_RECONCILIATION_REPORT.md).

### 27.3 Safety Confirmation
**Phase 19 was conducted strictly offline. No remote database connection was initiated, no SQL was executed against Supabase, and no cloud resources were altered. The application database remains undeployed.**

---

## 28. Phase 20 Runtime Role Provisioning Readiness (Dated: October 11, 2026)

### 28.1 Executive Summary of Phase 20
Phase 20 audited the backend connection pipeline, fallback behavior, and provisioning procedure for the least-privilege role `luxe_app_user` while operating strictly offline:
1. **Connection Pipeline Compatibility:** Verified that FastAPI and SQLAlchemy natively support connection URIs specifying `luxe_app_user` (direct port 5432) or `luxe_app_user.<project_ref>` (pooler port 6543) without code modifications.
2. **Fallback Analysis:** Verified that `Settings` defaults to SQLite when `DATABASE_URL` is omitted, but **does not silently fall back to SQLite** when a configured PostgreSQL connection fails. Startup aborts immediately via `init_db()` with a detailed `RuntimeError`.
3. **Privileged Account Risk:** Identified that the current `.env` contains the administrative user (`postgres.<project_ref>`). Connecting as `postgres` bypasses RLS (`BYPASSRLS = true`). Transition to `luxe_app_user` is required prior to public traffic.
4. **Provisioning & Credential Protocol:** Documented the private manual `CREATE ROLE` procedure and established that passwords must be generated via `secrets.token_urlsafe(32)` to eliminate percent-encoding issues and history leakage.
5. **Pre-Migration Safety Verification:** Demonstrated offline that `init_db()` safely refuses to start or auto-create tables on an empty or partially migrated PostgreSQL database.
6. **Detailed Audit Report:** Authored [`PHASE_20_RUNTIME_ROLE_READINESS.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/PHASE_20_RUNTIME_ROLE_READINESS.md).

### 28.2 Safety Confirmation
**Phase 20 was conducted strictly offline. No remote database connection was initiated, no SQL was executed against Supabase, no secrets were printed, and no cloud resources were modified. The application database remains undeployed.**

---

## 29. Phase 21 Pre-Deployment Safety Gate & Execution Protocol (Dated: October 11, 2026)

### 29.1 Executive Summary of Phase 21
Phase 21 established the definitive pre-deployment gate and multi-stage execution runbook:
1. **Canonical Candidate Migration:** Formally established [`supabase/proposals/luxe_phase18_hardened_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase18_hardened_first_install.sql) as the sole canonical migration candidate (11 tables, 113 columns, 12 indexes, 2 unique constraints, 10 foreign keys).
2. **Restricted Role Confinement:** Formally verified the 5 required security attributes for `luxe_app_user`: `LOGIN`, `NOSUPERUSER`, `NOCREATEDB`, `NOREPLICATION`, `NOBYPASSRLS`.
3. **Decoupled Verification Architecture:** Separated low-level network/auth probing (`SELECT 1`) from application-level schema completeness validation (`init_db()`).
4. **Gated Deployment Sequence:** Defined Gates 0 through 6 with explicit stop conditions at each stage to ensure fail-fast abort upon any anomaly.
5. **Decoupled Storage Setup:** Confirmed that core table DDL and Supabase Storage bucket configuration (`luxe_phase16_storage_setup_proposal.sql`) remain strictly decoupled.
6. **Rollback & PITR Governance:** Documented that committed migrations cannot be undone by a database transaction and that `DROP TABLE ... CASCADE` is permanently banned post-launch, requiring Supabase PITR or automated snapshots for recovery.
7. **Documented Pre-Deployment Gate Dossier:** Authored [`PHASE_21_PREDEPLOYMENT_GATE.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/PHASE_21_PREDEPLOYMENT_GATE.md).

### 29.2 Safety Confirmation
**Phase 21 was conducted strictly offline. No remote database connection was initiated, no SQL was executed on Supabase, no environment variables were changed, and no cloud resources were modified. The application database remains undeployed pending operator execution.**

---

## 30. Phase 22 Independent Pre-Deployment Safety Audit (Dated: October 11, 2026)

### 30.1 Executive Summary of Phase 22
Phase 22 conducted a comprehensive independent safety audit of the migration proposal, storage configuration, API ownership checks, runtime role specification, and failure behaviors:
1. **Audited Parity:** Re-confirmed 100% exact parity across 11 tables, 113 columns, and 12 indexes between `Base.metadata.tables` and [`supabase/proposals/luxe_phase18_hardened_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase18_hardened_first_install.sql).
2. **Finding Classification:** Classified 7 findings across BLOCKER (F-01: `.env` configured as `postgres`), HIGH (F-02: Broad RLS delegates tenant isolation to FastAPI; F-03: Unverified cloud backups/PITR/pooler), MEDIUM (F-04: Role guard in SQL does not check attribute flags; F-05: Storage service key required for signed URLs; F-06: Committed migrations cannot be rolled back via SQL transaction), and LOW (F-07: Deferred `images.user_id`).
3. **Role Specification:** Formally incorporated all 6 security attributes: `LOGIN`, `NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`, `NOREPLICATION`, `NOBYPASSRLS`.
4. **Audit Dossier:** Authored [`PHASE_22_INDEPENDENT_SAFETY_AUDIT.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/PHASE_22_INDEPENDENT_SAFETY_AUDIT.md) (mirrored in `supabase/proposals/`).
5. **Final Status:** Formally designated as **`PASS FOR READ-ONLY VERIFICATION ONLY`**.

### 30.2 Safety Confirmation
**Phase 22 was conducted strictly offline. No remote database connection was initiated, no SQL was executed against Supabase, no credentials were exposed, and no cloud resources were modified. The application database remains undeployed.**




