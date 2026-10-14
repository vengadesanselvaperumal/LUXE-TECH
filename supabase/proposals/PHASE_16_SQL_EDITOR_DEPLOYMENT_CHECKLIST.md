# LUXE.TECH — Phase 16: Supabase SQL Editor Deployment Checklist

**Document Location:** `supabase/proposals/PHASE_16_SQL_EDITOR_DEPLOYMENT_CHECKLIST.md`  
**Status:** BINDING OPERATIONAL CHECKLIST (Requires Human Operator Sign-Off)  
**Target Environment:** Dedicated LUXE.TECH Supabase Project  
**Author:** LUXE.TECH Senior Backend & Database Security Engineering  
**Date:** October 10, 2026  

---

## Deployment Gateway Overview

This checklist defines the required verification gates for executing the initial database setup using the **Supabase SQL Editor**. Every check must be confirmed prior to, during, and after execution.

---

## Phase 1: Pre-Execution Prerequisites & Dashboard Verification

| Step | Check Item | Verification Query / Procedure | Pass Criteria | Status |
|:---:|---|---|---|:---:|
| **1.1** | **Dedicated Project Identity** | In browser, check URL: `https://supabase.com/dashboard/project/<PROJECT_REF>`. | `<PROJECT_REF>` matches the 20-character reference configured in `.env`. | `[PENDING]` |
| **1.2** | **Zero Collision with Other Apps** | Verify project name in Supabase Dashboard header. | Dedicated to LUXE.TECH; no other projects or applications share this cluster. | `[PENDING]` |
| **1.3** | **Clean Baseline in `public`** | In SQL Editor, run:<br>`SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';` | Exactly `0 rows` returned (no existing application tables). | `[PENDING]` |
| **1.4** | **Backup & PITR Operational** | Navigate to **Settings** $\rightarrow$ **Database** $\rightarrow$ **Backups**. | Automated daily backups or PITR are active and operational. | `[PENDING]` |

---

## Phase 2: Local Script Preparation & Review

| Step | Check Item | Action Required | Status |
|:---:|---|---|:---:|
| **2.1** | **Target Script File** | Locate [`supabase/proposals/luxe_phase16_canonical_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_canonical_first_install.sql). | `[CONFIRMED]` |
| **2.2** | **Password Substitution** | Open script and locate line 31: `PASSWORD 'REPLACE_WITH_STRONG_PASSWORD'`. Replace with a generated, high-entropy password for `luxe_app_user`. | `[PENDING OPERATOR]` |
| **2.3** | **Atomic Transaction Check** | Verify script opens with `BEGIN;` (line 20) and concludes with `COMMIT;` (line 295). | `[CONFIRMED]` |
| **2.4** | **Zero Destructive Commands** | Confirm absence of `DROP TABLE`, `TRUNCATE`, `DROP SCHEMA`, or `CASCADE` statements. | `[CONFIRMED]` |
| **2.5** | **Storage Separation** | Confirm that storage bucket DML is **not** included in the table creation script. | `[CONFIRMED]` |

---

## Phase 3: SQL Editor Execution Steps

1. [ ] Log in to **Supabase Dashboard** and select the dedicated LUXE.TECH project.
2. [ ] In the left sidebar, click **SQL Editor**.
3. [ ] Click **New Query** and title the tab `001_luxe_canonical_first_install`.
4. [ ] Copy the entire contents of [`luxe_phase16_canonical_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_canonical_first_install.sql).
5. [ ] Paste into the SQL Editor.
6. [ ] Replace `'REPLACE_WITH_STRONG_PASSWORD'` with your generated runtime password.
7. [ ] Click **Run** (or press `Ctrl+Enter`).
8. [ ] Verify result banner displays: **`Success. No rows returned`** (or transaction committed).

---

## Phase 4: Immediate Post-Execution Verification Queries

Open a new query tab in SQL Editor and execute each verification query:

### Check 4.1: Verify All 11 Application Tables Exist
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;
```
- [ ] **Expected Output (11 tables):** `collections`, `forecasts`, `images`, `products`, `prophecy`, `retail_signals`, `saved_trends`, `trend_dna`, `trend_signals`, `trends`, `users`.

### Check 4.2: Verify Row Level Security Is Enabled on All Tables
```sql
SELECT relname AS table_name, relrowsecurity AS rls_enabled
FROM pg_class
WHERE relnamespace = 'public'::regnamespace AND relkind = 'r'
ORDER BY relname;
```
- [ ] **Expected Output:** All 11 tables show `rls_enabled = true`.

### Check 4.3: Verify 11 Runtime Policies for `luxe_app_user`
```sql
SELECT tablename, policyname, roles, cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename;
```
- [ ] **Expected Output:** Exactly 11 policies named `app_runtime_all`, targeting `{luxe_app_user}` with `cmd = ALL`.

### Check 4.4: Verify 12 Explicit Indexes Exist
```sql
SELECT tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public' AND indexname LIKE 'ix_%'
ORDER BY tablename, indexname;
```
- [ ] **Expected Output (12 indexes):**
  - `collections` $\rightarrow$ `ix_collections_trend_id`
  - `forecasts` $\rightarrow$ `ix_forecasts_trend_id`
  - `images` $\rightarrow$ `ix_images_trend_id`
  - `products` $\rightarrow$ `ix_products_trend_id`
  - `prophecy` $\rightarrow$ `ix_prophecy_trend_id`
  - `retail_signals` $\rightarrow$ `ix_retail_signals_trend_id`
  - `saved_trends` $\rightarrow$ `ix_saved_trends_trend_id`, `ix_saved_trends_user_id`
  - `trend_signals` $\rightarrow$ `ix_trend_signals_trend_id`
  - `trends` $\rightarrow$ `ix_trends_category`, `ix_trends_slug`
  - `users` $\rightarrow$ `ix_users_email`

### Check 4.5: Verify Least-Privilege Role Attributes for `luxe_app_user`
```sql
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls
FROM pg_roles
WHERE rolname = 'luxe_app_user';
```
- [ ] **Expected Output:** `rolsuper = false`, `rolcreaterole = false`, `rolcreatedb = false`, `rolbypassrls = false`.

### Check 4.6: Verify PostgREST Fail-Closed Status
```sql
SELECT table_name, privilege_type, grantee
FROM information_schema.table_privileges
WHERE table_schema = 'public' AND grantee IN ('anon', 'authenticated');
```
- [ ] **Expected Output:** `0 rows` (All direct privileges revoked from public roles).

---

## Phase 5: Storage Bucket Provisioning (Decoupled Step)

1. [ ] Review [`supabase/proposals/luxe_phase16_storage_setup_proposal.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql).
2. [ ] In SQL Editor, execute the script OR create the buckets in **Storage** $\rightarrow$ **New Bucket**:
   - `trend-images`: Public, 10 MB limit, image MIME whitelist (`image/jpeg`, `image/png`, `image/webp`).
   - `collections`: Public, 10 MB limit, image MIME whitelist (`image/jpeg`, `image/png`, `image/webp`).
   - `user-uploads`: Strictly Private, 10 MB limit, image MIME whitelist.
3. [ ] Verify buckets appear in Supabase Storage dashboard with correct public/private toggles.

---

## Phase 6: Application Runtime Configuration

1. [ ] Update `DATABASE_URL` in backend `.env` to connect as `luxe_app_user`:
   ```env
   DATABASE_URL="postgresql+psycopg://luxe_app_user:<GENERATED_PASSWORD>@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
   ```
2. [ ] Verify `connect_args={"prepare_threshold": None}` in `database.py` for transaction pooler mode.
3. [ ] Run FastAPI application startup to trigger `init_db()` validation.
4. [ ] Verify zero schema errors or missing table exceptions.

---

## Phase 7: Safe Failure Handling & Emergency Protocols

### Day-0 Fresh Install Abort (Empty Database Failure Only)
- If an unexpected error occurs during Phase 3 execution:
  1. The transaction will automatically execute `ROLLBACK;`.
  2. If partial statements were executed outside a transaction block on a fresh empty cluster:
     ```sql
     -- ONLY PERMISSIBLE ON DAY-0 WITH ZERO USER DATA:
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

### Post-Launch Rule: Strictly Prohibit `DROP TABLE ... CASCADE`
> [!CAUTION]
> Once real users exist, **`DROP TABLE ... CASCADE` is permanently forbidden**. Schema corrections must be made via forward migrations (`ALTER TABLE`). Data recovery must use Supabase Point-in-Time Recovery (PITR) or daily automated snapshots.

