# LUXE.TECH — Storage Proposal Security Audit (Offline Review)

**Document Location:** [`supabase/proposals/PHASE_STORAGE_SECURITY_AUDIT.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/PHASE_STORAGE_SECURITY_AUDIT.md)  
**Target Proposal:** [`supabase/proposals/luxe_phase16_storage_setup_proposal.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql)  
**Core Schema Reference:** [`supabase/proposals/luxe_phase18_hardened_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase18_hardened_first_install.sql)  
**Backend Storage Clients:** [`backend/app/services/supabase_service.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/services/supabase_service.py), [`backend/app/routers/images.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/images.py)  
**Execution Mode:** STRICTLY LOCAL & OFFLINE (Zero remote database connections, zero SQL executions, zero credential exposure)  
**Date:** October 11, 2026  
**Auditor:** Senior Cloud Security & Database Architecture Engineer  
**Final Status:** **READY FOR REVIEW** (With Recommended Pre-Execution Idempotency Hardening)

---

## 1. Executive Summary

This independent security audit evaluates [`supabase/proposals/luxe_phase16_storage_setup_proposal.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql) to verify that Supabase Storage bucket provisioning, access control policies, object isolation, and backend integration conform to least-privilege principles and zero-trust data protection standards.

### Summary of Audit Verdicts
* **Blockers Identified:** **0 BLOCKERS** (No critical vulnerabilities, data destruction vectors, or cross-tenant leakage).
* **Warnings Identified:** **2 WARNINGS** (Re-execution idempotency on policy creation; reliance on application-layer ownership checks due to custom FastAPI JWT architecture).
* **Checks Passed:** **6 PASSES** (Bucket scopes, public read isolation, fail-closed PostgREST defaults, non-destructive upserts, zero impact on the 11 core tables, MIME & size enforcement).
* **Final Recommendation:** **READY FOR REVIEW**. The proposal is architecturally sound and safe to apply following minor idempotency hardening.

---

## 2. Granular Verification Matrix

| # | Audit Item | Classification | Verification Summary | Line Reference |
|---|---|:---:|---|---|
| **1** | Bucket Configuration & Visibility | **PASS** | Provisions `trend-images` (public), `collections` (public), and `user-uploads` (private) with 10 MB limit and image-only MIME types. | [Lines 17–43](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql#L17-L43) |
| **2** | Storage Policy Scoping & Operations | **PASS** | Policies explicitly filter on `bucket_id` and restrict operations strictly to `FOR SELECT`. | [Lines 47–53](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql#L47-L53) |
| **3** | Private Uploads Isolation (`user-uploads`) | **PASS** | Zero public policies defined on `user-uploads`. Direct PostgREST access fails closed (401/403/empty). Access requires backend signed URLs. | [Lines 34–39, 55–59](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql#L34-L39) |
| **4** | Cross-Project & Unrelated Objects Safety | **PASS** | Contains no broad `GRANT`, `REVOKE`, or un-scoped policy statements. Does not affect other Supabase buckets or schemas. | [Lines 14–60](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql#L14-L60) |
| **5** | Public Bucket Write/Delete Confinement | **PASS** | Public policies grant read-only (`FOR SELECT`). Mutations (`INSERT`, `UPDATE`, `DELETE`) are denied by default under RLS. | [Lines 47–53](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql#L47-L53) |
| **6** | Policy Idempotency & Overwrite Handling | **WARNING** | `CREATE POLICY` statements lack `DROP POLICY IF EXISTS`. Re-running script fails with `policy already exists`. | [Lines 47–53](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql#L47-L53) |
| **7** | Application Schema & 11-Table Parity | **PASS** | Strictly targets `storage.buckets` and `storage.objects`. Zero modifications to the 11 application tables in `public`. | [Lines 1–62](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql#L1-L62) |
| **8** | Application-Side Ownership Enforcement | **WARNING** | User asset paths (`{user_id}/*`) and signed URL generation are enforced in FastAPI, not by PostgreSQL RLS. | [Backend `images.py:46-65`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/images.py#L46-L65) |

---

## 3. Detailed Audit Findings & Technical Analysis

### 3.1 Item 1: Bucket Definitions, Capacity, and MIME Whitelists [PASS]
* **Target File:** [`supabase/proposals/luxe_phase16_storage_setup_proposal.sql:17-43`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql#L17-L43)
* **Analysis:**
  * `trend-images`: `id = 'trend-images'`, `public = true`, `file_size_limit = 10485760` (10 MB), `allowed_mime_types = ARRAY['image/jpeg', 'image/png', 'image/webp']`.
  * `collections`: `id = 'collections'`, `public = true`, `file_size_limit = 10485760` (10 MB), `allowed_mime_types = ARRAY['image/jpeg', 'image/png', 'image/webp']`.
  * `user-uploads`: `id = 'user-uploads'`, `public = false`, `file_size_limit = 10485760` (10 MB), `allowed_mime_types = ARRAY['image/jpeg', 'image/png', 'image/webp']`.
* **Conflict Resolution:** The `INSERT ... ON CONFLICT (id) DO UPDATE SET public = EXCLUDED.public, file_size_limit = EXCLUDED.file_size_limit, allowed_mime_types = EXCLUDED.allowed_mime_types` ensures idempotent bucket creation without dropping or recreating existing storage containers.
* **Verdict:** **PASS**. Configuration strictly matches backend storage requirements.

---

### 3.2 Item 2: Storage Policy Scoping & Operations [PASS]
* **Target File:** [`supabase/proposals/luxe_phase16_storage_setup_proposal.sql:47-53`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql#L47-L53)
* **Analysis:**
  * Policy 1: `"Public Read Trend Images"`:
    ```sql
    CREATE POLICY "Public Read Trend Images" ON storage.objects
        FOR SELECT
        USING (bucket_id = 'trend-images');
    ```
  * Policy 2: `"Public Read Collections"`:
    ```sql
    CREATE POLICY "Public Read Collections" ON storage.objects
        FOR SELECT
        USING (bucket_id = 'collections');
    ```
  * Both policies are strictly limited to `FOR SELECT` and explicitly predicate on their respective `bucket_id`.
  * No wildcard access across buckets or unintended storage schemas is possible.
* **Verdict:** **PASS**.

---

### 3.3 Item 3: Private Uploads Isolation (`user-uploads`) [PASS]
* **Target File:** [`supabase/proposals/luxe_phase16_storage_setup_proposal.sql:34-39, 55-59`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql#L34-L39)
* **Analysis:**
  * The `user-uploads` bucket is declared with `public = false`.
  * Crucially, **zero public policies** are created on `storage.objects` for `user-uploads`.
  * Because Row Level Security is enabled by default on `storage.objects` in Supabase Storage, any request made through PostgREST by `anon` or `authenticated` roles is denied by default.
  * Direct public CDN URLs (`/storage/v1/object/public/user-uploads/...`) return HTTP 400/404.
  * Private object access is possible **exclusively** via temporary signed URLs generated server-side by FastAPI using the Supabase Service Role Key with a 1-hour expiration (`SIGNED_URL_EXPIRES_SECONDS = 3600`).
* **Verdict:** **PASS**. Private asset isolation adheres to fail-closed principles.

---

### 3.4 Item 4: Cross-Project and Unrelated Storage Objects Safety [PASS]
* **Target File:** [`supabase/proposals/luxe_phase16_storage_setup_proposal.sql:14-60`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql#L14-L60)
* **Analysis:**
  * The script contains no `GRANT` or `REVOKE` statements affecting schema `storage` or table `storage.objects`.
  * It does not modify existing buckets that might be used by unrelated services or parent infrastructure.
  * The queries exclusively insert or update the three designated bucket rows in `storage.buckets` by explicit primary key (`id`).
* **Verdict:** **PASS**. No side effects on unrelated storage objects or external projects.

---

### 3.5 Item 5: Mutation Confinement on Public Buckets [PASS]
* **Target File:** [`supabase/proposals/luxe_phase16_storage_setup_proposal.sql:47-53`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql#L47-L53)
* **Analysis:**
  * While `trend-images` and `collections` are publicly readable, neither `anon` nor `authenticated` are granted `INSERT`, `UPDATE`, or `DELETE` policies on `storage.objects`.
  * External users cannot upload malicious files, deface trend assets, or delete catalog imagery directly via Supabase API.
  * All mutations on `trend-images` and `collections` originate exclusively from authenticated, privileged backend requests (`PRIVILEGED_ROLES` in [`backend/app/routers/images.py:52`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/images.py#L52)) using the backend service-role credential.
* **Verdict:** **PASS**. Public bucket write and delete operations are strictly protected.

---

### 3.6 Item 6: Policy Creation Idempotency & Overwrite Handling [WARNING]
* **Target File:** [`supabase/proposals/luxe_phase16_storage_setup_proposal.sql:47-53`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql#L47-L53)
* **Issue Description:**
  * While the `storage.buckets` insertion uses `ON CONFLICT (id) DO UPDATE` for safe re-runs, the policy creation statements use plain `CREATE POLICY`:
    ```sql
    CREATE POLICY "Public Read Trend Images" ON storage.objects ...
    CREATE POLICY "Public Read Collections" ON storage.objects ...
    ```
  * In PostgreSQL, `CREATE POLICY` does not support an `IF NOT EXISTS` clause.
  * If the migration is re-run or if a policy with the same name already exists in `storage.objects`, execution will abort with:
    `ERROR: policy "Public Read Trend Images" for table "objects" already exists`.
* **Recommended Correction:**
  Precede each policy creation with an explicit `DROP POLICY IF EXISTS`:
  ```sql
  DROP POLICY IF EXISTS "Public Read Trend Images" ON storage.objects;
  CREATE POLICY "Public Read Trend Images" ON storage.objects
      FOR SELECT
      USING (bucket_id = 'trend-images');

  DROP POLICY IF EXISTS "Public Read Collections" ON storage.objects;
  CREATE POLICY "Public Read Collections" ON storage.objects
      FOR SELECT
      USING (bucket_id = 'collections');
  ```
* **Verdict:** **WARNING (Non-Critical, Idempotency)**. Does not compromise security on a fresh deployment, but will fail if re-executed.

---

### 3.7 Item 7: Core Application Schema & Table Isolation [PASS]
* **Target File:** [`supabase/proposals/luxe_phase16_storage_setup_proposal.sql:1-62`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql#L1-L62)
* **Analysis:**
  * The storage setup script is completely decoupled from the 11 application tables defined in [`supabase/proposals/luxe_phase18_hardened_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase18_hardened_first_install.sql).
  * It executes zero DDL against `public.users`, `public.trends`, `public.images`, or any other table.
  * The application `images` table stores `storage_path` and `public_url` as `VARCHAR` columns, which seamlessly reference the objects stored under these buckets.
* **Verdict:** **PASS**. Complete separation of concerns and zero risk to relational tables.

---

### 3.8 Item 8: Database vs. Application-Enforced Ownership [WARNING]
* **Target File:** [`backend/app/routers/images.py:46-65`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/images.py#L46-L65), [`backend/app/services/supabase_service.py:42-120`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/services/supabase_service.py#L42-L120)
* **Issue Description:**
  * In standard Supabase architectures using built-in Supabase Auth (GoTrue), private object ownership is typically enforced at the database level using RLS policies such as:
    ```sql
    CREATE POLICY "User Owns Upload" ON storage.objects
        FOR ALL TO authenticated
        USING (bucket_id = 'user-uploads' AND (storage.foldername(name))[1] = auth.uid()::text);
    ```
  * In LUXE.TECH, custom JWT authentication is handled directly by FastAPI (`backend/app/utils/security.py`).
  * Because end-user browser requests never carry Supabase GoTrue tokens, `auth.uid()` is null for application traffic.
  * Consequently:
    1. Direct PostgREST access to `user-uploads` is completely denied (fail-closed, 0 policies).
    2. All private uploads and retrieval requests route through the FastAPI backend using `SUPABASE_SERVICE_ROLE_KEY`.
    3. User isolation (`{user_id}/{uuid}_{filename}`) is enforced **strictly at the Python application layer** in `images.py` and `supabase_service.py`.
    4. In the database, the `images` table currently lacks a relational `user_id` foreign key column (deferred to maintain 13-column parity with SQLAlchemy `ImageRecord`).
* **Security Assessment:**
  * This is an intentional architectural boundary decision resulting from decoupled FastAPI JWT authentication.
  * The database layer is secure because PostgREST access is blocked by default-deny RLS.
  * However, multi-tenant row isolation for user uploads relies 100% on application code correctness.
* **Recommended Architectural Enhancement (Future Migration):**
  * When `images.user_id` is introduced in a future migration, consider evaluating whether custom claims or signed URL token validation can bridge database-level RLS if direct client-to-storage uploads are ever implemented.
* **Verdict:** **WARNING (Architectural Boundary)**. Operates safely within the current backend design, but ownership is application-enforced rather than database-enforced.

---

## 4. Remediation Code Proposal

To resolve the idempotency warning (Item 6), the recommended production-ready version of [`supabase/proposals/luxe_phase16_storage_setup_proposal.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql) is:

```sql
-- ============================================================================
-- LUXE.TECH — Hardened Supabase Storage Setup (Reviewed & Idempotent)
-- ============================================================================

BEGIN;

-- 1. PROVISION STORAGE BUCKETS (IDEMPOTENT UPSERT)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES
    (
        'trend-images',
        'trend-images',
        true,
        10485760, -- 10 MB limit
        ARRAY['image/jpeg', 'image/png', 'image/webp']
    ),
    (
        'collections',
        'collections',
        true,
        10485760, -- 10 MB limit
        ARRAY['image/jpeg', 'image/png', 'image/webp']
    ),
    (
        'user-uploads',
        'user-uploads',
        false, -- Strictly Private
        10485760, -- 10 MB limit
        ARRAY['image/jpeg', 'image/png', 'image/webp']
    )
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- 2. STORAGE OBJECT ACCESS POLICIES (IDEMPOTENT CREATION)
-- Public CDN Read for 'trend-images'
DROP POLICY IF EXISTS "Public Read Trend Images" ON storage.objects;
CREATE POLICY "Public Read Trend Images" ON storage.objects
    FOR SELECT
    USING (bucket_id = 'trend-images');

-- Public CDN Read for 'collections'
DROP POLICY IF EXISTS "Public Read Collections" ON storage.objects;
CREATE POLICY "Public Read Collections" ON storage.objects
    FOR SELECT
    USING (bucket_id = 'collections');

-- Note on 'user-uploads':
-- Zero public policies are defined for 'user-uploads'.
-- Objects in 'user-uploads' can only be accessed via temporary signed URLs
-- generated server-side by FastAPI via the Supabase Storage Service Role Key.

COMMIT;
```

---

## 5. Final Decision & Sign-Off

### Audit Decision: **READY FOR REVIEW**
* The proposal introduces **zero destructive operations**, **zero table modifications**, and **zero cross-project side effects**.
* The storage model is secure, correctly enforces 10 MB and image-only MIME constraints, and keeps private uploads fail-closed.
* Applying the recommended `DROP POLICY IF EXISTS` statements ensures safe re-execution during live deployment.
* Once the 11 core tables in `luxe_phase18_hardened_first_install.sql` are applied and verified in the dedicated Supabase project, this storage setup script is approved for execution.

