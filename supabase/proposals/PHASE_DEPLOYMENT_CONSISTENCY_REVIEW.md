# LUXE.TECH — Deployment Runbook Consistency Review

**Document Version:** 1.0.0  
**Status:** COMPLETE (Offline Audit Only — No Remote Execution)  
**Target:** Dedicated LUXE.TECH Supabase Project (`nmmtbbmksyyfjgtkczot`)  
**Audited Artifacts:**
- [`supabase/proposals/luxe_phase18_hardened_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase18_hardened_first_install.sql)
- [`supabase/proposals/luxe_phase16_storage_setup_proposal.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql)
- [`supabase/proposals/PHASE_STORAGE_SECURITY_AUDIT.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_STORAGE_SECURITY_AUDIT.md)
- [`backend/app/database.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/database.py)
- [`backend/app/services/supabase_service.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/services/supabase_service.py)
- [`backend/app/routers/images.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/images.py)

---

## 1. Executive Summary & Verification Findings

This consistency review performs an end-to-end reconciliation across the database schema DDL, the storage provisioning proposals, backend application authentication and authorization flows, and test/build artifacts.

### Overall Verdict:
- **Core Schema Parity:** **100% MATCH** between [`backend/app/database.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/database.py) and [`luxe_phase18_hardened_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase18_hardened_first_install.sql).
- **Deployment Runbook Table Names:** **4 MISMATCHES IDENTIFIED AND CORRECTED** (see Section 2).
- **Storage Security Audit Conclusion:** **VALIDATED**. The `READY FOR REVIEW` verdict in [`PHASE_STORAGE_SECURITY_AUDIT.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_STORAGE_SECURITY_AUDIT.md) is sound, with essential constraints documented regarding application-layer vs. database-layer ownership boundaries.
- **Storage SQL Scope & Isolation:** **VERIFIED**. Target statements strictly scope to the 3 application buckets and 2 explicit policies without touching foreign projects or unmanaged storage resources.
- **Custom JWT vs. Supabase Storage Compatibility:** **VERIFIED**. The fail-closed storage model correctly delegates tenant isolation to FastAPI, avoiding reliance on unsupported database-level `auth.uid()` evaluation.
- **Test Suite & Build Status:** **VERIFIED**. Both backend tests (42/42 passed) and frontend build (`tsc -b && vite build`) completed successfully with zero pending background processes.

---

## 2. Table Reconciliation: Migration vs. Runbook vs. SQLAlchemy

A critical discrepancy was discovered between the actual tables defined in [`luxe_phase18_hardened_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase18_hardened_first_install.sql) and the table list previously cited in the deployment runbook.

### 2.1 Table Reconciliation Matrix

| # | SQLAlchemy Model (`database.py`) | Phase 18 Schema Table (`luxe_phase18_...sql`) | Runbook Candidate List | Reconciliation Status | Notes & Source Locations |
|---|---|---|---|---|---|
| 1 | `User` (L38) | `public.users` (L72) | `users` | **MATCH** | Primary application user accounts |
| 2 | `Trend` (L52) | `public.trends` (L86) | `trends` | **MATCH** | Core trend intelligence catalog |
| 3 | `TrendSignal` (L81) | `public.trend_signals` (L109) | `signals` | **MISMATCH (CORRECTED)** | Schema & model table is `trend_signals`, not `signals` |
| 4 | `TrendDNA` (L108) | `public.trend_dna` (L125) | `categories` | **MISMATCH (CORRECTED)** | Category is a column attribute; actual table is `trend_dna` |
| 5 | `ImageRecord` (L141) | `public.images` (L146) | `images` | **MATCH** | Vision metrics and storage asset catalog |
| 6 | `Collection` (L168) | `public.collections` (L166) | `collections` | **MATCH** | Curated capsules and design palettes |
| 7 | `Product` (L187) | `public.products` (L185) | `products` | **MATCH** | Commercial product opportunities |
| 8 | `RetailSignal` (L207) | `public.retail_signals` (L205) | `retail_metrics` | **MISMATCH (CORRECTED)** | Schema & model table is `retail_signals`, not `retail_metrics` |
| 9 | `Forecast` (L223) | `public.forecasts` (L224) | `forecasts` | **MATCH** | Statistical forecasts and backtest metrics |
| 10 | `Prophecy` (L240) | `public.prophecy` (L242) | `collection_items` | **MISMATCH (CORRECTED)** | Items are JSON in `collections`; actual table is `prophecy` |
| 11 | `SavedTrend` (L257) | `public.saved_trends` (L258) | `saved_trends` | **MATCH** | User personal bookmarks |

### 2.2 Root Cause of Runbook Mismatches
The 4 incorrect table names (`categories`, `collection_items`, `retail_metrics`, `signals`) originated from legacy feature labels rather than relational database entities:
1. `categories`: Categories are modeled as `category VARCHAR` columns inside `trends` and `products`. The fourth relational table is `trend_dna` (1:1 with `trends`).
2. `collection_items`: Collection items, palettes, and silhouettes are stored as serialized JSON arrays directly on `collections`. The tenth table is `prophecy` (5-stage predictive trajectory).
3. `retail_metrics`: The SQLAlchemy model and Phase 18 DDL explicitly name this table `retail_signals`.
4. `signals`: The multi-channel signal table is named `trend_signals`.

### 2.3 Corrected Gate 4 Post-Migration Verification Query
The post-migration verification query in the operator runbook must expect these exact 11 table names:

```sql
SELECT c.relname AS table_name, c.relrowsecurity AS rls_enabled
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY c.relname;
```

**Expected Result (11 rows, all `rls_enabled = true`):**
1. `collections`
2. `forecasts`
3. `images`
4. `products`
5. `prophecy`
6. `retail_signals`
7. `saved_trends`
8. `trend_dna`
9. `trend_signals`
10. `trends`
11. `users`

---

## 3. Storage Security Audit Evaluation (`READY FOR REVIEW`)

[`supabase/proposals/PHASE_STORAGE_SECURITY_AUDIT.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_STORAGE_SECURITY_AUDIT.md) evaluated [`luxe_phase16_storage_setup_proposal.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql) across 8 criteria and reached a verdict of `READY FOR REVIEW` (0 BLOCKERS, 2 WARNINGS, 6 PASSES).

### 3.1 Does the Audit Support Its Conclusion?
**Yes**, the conclusion is sound and justified, with the following qualifications:
1. **Isolation of DDL & Storage:** The proposal strictly interacts with `storage.buckets` and `storage.objects`. It executes zero DDL against `public` schema tables and contains zero destructive commands (`DROP TABLE`, `TRUNCATE`, `CASCADE`).
2. **Bucket Scoping:** The `INSERT ... ON CONFLICT (id)` clause specifies exact primary keys (`'trend-images'`, `'collections'`, `'user-uploads'`). It does not update or touch existing buckets from other applications.
3. **MIME & Size Restrictions:** Each bucket enforces a 10 MB payload ceiling (`10485760`) and restricts allowed MIME types to `image/jpeg`, `image/png`, and `image/webp`.
4. **Idempotency Warning Resolution:** The audit correctly identified that the original proposal lacked `DROP POLICY IF EXISTS`, which would cause failures if executed multiple times in the Supabase SQL Editor. The remediation script in Section 4 of the audit resolves this idempotency issue.

---

## 4. Resource Isolation & Policy Drop Safety

### 4.1 Bucket Protection
In [`luxe_phase16_storage_setup_proposal.sql:17-43`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql#L17-L43):
```sql
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (...)
ON CONFLICT (id) DO UPDATE SET ...;
```
- The statement uses explicit row values for 3 specified IDs.
- It cannot overwrite unrelated buckets because `ON CONFLICT (id)` triggers only when a row with `id = 'trend-images'`, `'collections'`, or `'user-uploads'` already exists.
- Foreign buckets in the project are untouched.

### 4.2 Policy Drop Safety
The remediation proposal uses:
```sql
DROP POLICY IF EXISTS "Public Read Trend Images" ON storage.objects;
DROP POLICY IF EXISTS "Public Read Collections" ON storage.objects;
```
- These statements drop only specifically named policies attached to `storage.objects`.
- They do not use wildcard policy removal or alter policies belonging to other buckets.
- To avoid dropping unapproved policies, the operator must execute this script only after reviewing that no conflicting policies with these exact names exist for other purposes.

---

## 5. Private Uploads, Access Control & Custom FastAPI JWT Compatibility

A critical security question is whether Supabase Storage policies can enforce user-level ownership on private uploads when the application uses custom JWT authentication.

### 5.1 Architecture & JWT Boundary
1. **Decoupled JWT System:**
   - The LUXE.TECH application issues custom JWT tokens signed by `JWT_SECRET_KEY` via FastAPI ([`backend/app/utils/security.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/utils/security.py)).
   - End-user browser requests send this custom token in the `Authorization: Bearer <token>` header to FastAPI endpoints (`/api/...`).
   - The browser never interacts directly with Supabase GoTrue authentication.
2. **Supabase Storage Evaluates GoTrue Claims Only:**
   - Supabase Storage RLS policies evaluate `auth.uid()`, which extracts the subject from Supabase GoTrue JWT tokens signed by the Supabase project JWT secret.
   - For any client connecting directly to Supabase PostgREST or Storage without a Supabase GoTrue token, `auth.uid()` evaluates to `NULL`.
3. **Implication for Storage Policies:**
   - **Any Supabase Storage policy written as `USING (auth.uid() = ...)` will fail to match legitimate application users.**
   - Attempting to configure database-level ownership policies in Supabase Storage based on `auth.uid()` is incompatible with the current custom JWT architecture.

### 5.2 The Fail-Closed Access Control Model
The application architecture accounts for this boundary through a server-mediated design:

```
[Browser / User] 
       │ (FastAPI JWT)
       ▼
[FastAPI Backend] ── (Authenticates JWT, extracts user_id, validates file)
       │
       ├─► Storage Path: "{user_id}/{uuid}_{safe_filename}"
       │
       ├─► Supabase Storage API ── (Authenticated via SUPABASE_SERVICE_ROLE_KEY)
       │      │
       │      ├─ Uploads object to 'user-uploads' bucket (public = false)
       │      └─ Requests 1-hour signed URL via /storage/v1/object/sign/user-uploads/...
       │
       ▼
[Returns Signed URL to User]
```

1. **Direct Access is Fail-Closed:**
   - Bucket `user-uploads` has `public = false`.
   - **Zero SELECT/INSERT/UPDATE/DELETE policies** exist on `storage.objects` for `user-uploads`.
   - Any direct HTTP attempt by an anonymous or authenticated user to read or write to `user-uploads` via Supabase APIs returns `400/403/404` (denied).
2. **Server-Mediated Uploads:**
   - In [`backend/app/routers/images.py:46-65`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/images.py#L46-L65), image uploads require `current_user = Depends(get_current_user)`.
   - Personal uploads are namespaced by user ID: `storage_path = f"{user_id}/{uuid.uuid4()}_{safe_filename}"`.
   - Uploads are transferred to Supabase Storage by [`backend/app/services/supabase_service.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/services/supabase_service.py) using the server's `SUPABASE_SERVICE_ROLE_KEY`.
3. **Server-Mediated Retrieval:**
   - After upload, `supabase_service._create_signed_url` requests a temporary signed URL with a 3,600-second (1-hour) expiration.
   - In local storage fallback mode ([`backend/app/routers/images.py:111-150`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/images.py#L111-L150)), FastAPI explicitly validates that `user.get("id")` matches the leading path segment `{user_id}/` or the user holds a privileged role.

### 5.3 Assessment of the Security Model
- **PostgREST/Storage Boundary:** Completely secure. External actors cannot read or write private assets.
- **Application Boundary:** User isolation is enforced by the FastAPI backend.
- **Future Enhancement Note:** If long-term access to private images beyond the initial 1-hour signed URL TTL is required, a dedicated endpoint `/api/images/{id}/signed-url` should be added in a future phase to regenerate signed URLs for authenticated owners.

---

## 6. Minimum Safe Storage Setup & Verification Runbook

### 6.1 Minimum Safe Provisioning SQL (Idempotent)
This is the minimal SQL required to establish storage buckets and public read access:

```sql
BEGIN;

-- 1. Provision Storage Buckets
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES
    ('trend-images', 'trend-images', true, 10485760, ARRAY['image/jpeg', 'image/png', 'image/webp']),
    ('collections', 'collections', true, 10485760, ARRAY['image/jpeg', 'image/png', 'image/webp']),
    ('user-uploads', 'user-uploads', false, 10485760, ARRAY['image/jpeg', 'image/png', 'image/webp'])
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- 2. Scoped Public Read Policies (CDN Distribution Only)
DROP POLICY IF EXISTS "Public Read Trend Images" ON storage.objects;
CREATE POLICY "Public Read Trend Images" ON storage.objects
    FOR SELECT USING (bucket_id = 'trend-images');

DROP POLICY IF EXISTS "Public Read Collections" ON storage.objects;
CREATE POLICY "Public Read Collections" ON storage.objects
    FOR SELECT USING (bucket_id = 'collections');

-- Note: 'user-uploads' intentionally has ZERO policies.
-- It remains strictly private and fail-closed.

COMMIT;
```

### 6.2 Step-by-Step Storage Verification Queries

#### Verification 1: Confirm Bucket Configurations
Run in Supabase SQL Editor:
```sql
SELECT id, name, public, file_size_limit, allowed_mime_types
FROM storage.buckets
WHERE id IN ('trend-images', 'collections', 'user-uploads')
ORDER BY id;
```
**Expected Result:**
| id | name | public | file_size_limit | allowed_mime_types |
|---|---|---|---|---|
| `collections` | `collections` | `true` | `10485760` | `{image/jpeg,image/png,image/webp}` |
| `trend-images` | `trend-images` | `true` | `10485760` | `{image/jpeg,image/png,image/webp}` |
| `user-uploads` | `user-uploads` | `false` | `10485760` | `{image/jpeg,image/png,image/webp}` |

#### Verification 2: Confirm Storage Policies
Run in Supabase SQL Editor:
```sql
SELECT policyname, tablename, cmd, roles, qual
FROM pg_policies
WHERE schemaname = 'storage' AND tablename = 'objects'
  AND policyname IN ('Public Read Trend Images', 'Public Read Collections');
```
**Expected Result:** Exactly 2 rows returned (`cmd = 'SELECT'`), with zero policies matching `user-uploads`.

#### Verification 3: Confirm Access Separation via HTTP
- **Public Bucket Test:**
  `GET https://nmmtbbmksyyfjgtkczot.supabase.co/storage/v1/object/public/trend-images/test.jpg`
  *Expected:* HTTP `404 Not Found` (confirming endpoint is reachable and public).
- **Private Bucket Test:**
  `GET https://nmmtbbmksyyfjgtkczot.supabase.co/storage/v1/object/public/user-uploads/test.jpg`
  *Expected:* HTTP `400 Bad Request` or `404 Not Found` with message: `"Bucket not found"` or `"Bucket is not public"`.

---

## 7. Test Suite and Frontend Build Verification Audit

To prevent ambiguity between background task dispatch and actual test completion, all local verification tasks have been audited:

| Task / Process | Command Line | Completed Timestamp | Exit Code | Result Summary | Verification Status |
|---|---|---|---|---|---|
| Backend Test Suite | `backend\venv\Scripts\python -m pytest` | 2026-10-11T07:50:23Z | `0` | **42 passed**, 1 warning in 40.84s | **VERIFIED PASS** |
| Frontend Build | `npm run build` (`tsc -b && vite build`) | 2026-10-11T07:53:26Z | `0` | Built in 3.59s (`dist/index.html`, assets compiled) | **VERIFIED PASS** |
| Background Process Queue | `manage_task(Action='list')` | 2026-10-11T08:03:02Z | `N/A` | **0 active tasks** | **VERIFIED IDLE** |

**Conclusion:** All safe local code verifications have terminated with exit code 0. No asynchronous test tasks remain running in the background.

---

## 8. Summary of Findings & Next Actionable Gates

### Blockers:
- **Zero Blockers.** The schema proposal, storage proposal, and application code are consistent, hardened, and safe for execution.

### Corrective Actions Taken:
1. **Runbook Table List Corrected:** Updated the Gate 4 verification table list to match the true 11 tables (`collections`, `forecasts`, `images`, `products`, `prophecy`, `retail_signals`, `saved_trends`, `trend_dna`, `trend_signals`, `trends`, `users`).
2. **Storage Ownership Model Documented:** Confirmed that `user-uploads` must remain fail-closed without GoTrue `auth.uid()` policies, delegating tenant checks to FastAPI.

### Pending Live Deployment Gates:
1. **Gate 3 (Core Schema Migration):** Operator runs [`supabase/proposals/luxe_phase18_hardened_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase18_hardened_first_install.sql) in Supabase SQL Editor.
2. **Gate 4 (Schema Verification):** Operator confirms 11 tables with `rls_enabled = true` using corrected table names.
3. **Gate 5 (Storage Setup):** Operator runs Section 6.1 SQL in Supabase SQL Editor and runs verification queries.
4. **Gate 6 (Runtime Configuration):** Operator updates `DATABASE_URL` in [`.env`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/.env) with `luxe_app_user`.
5. **Gate 7 (Live Health Verification):** Operator launches FastAPI and verifies `/api/health`.

