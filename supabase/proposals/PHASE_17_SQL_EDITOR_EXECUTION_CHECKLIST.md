# LUXE.TECH — Phase 17: Supabase SQL Editor Execution Checklist

**Document Location:** `supabase/proposals/PHASE_17_SQL_EDITOR_EXECUTION_CHECKLIST.md`  
**Status:** BINDING EXECUTION GATEWAY (Requires Human Operator Sign-Off)  
**Target Environment:** Dedicated LUXE.TECH Supabase Project  
**Author:** LUXE.TECH Senior Backend & Database Security Engineering  
**Date:** October 10, 2026  

---

## Pre-Execution Governance & Mandatory Gate

> [!CAUTION]
> **STRICT SAFETY RULE:**
> Do NOT execute the initial DDL script until every check in **Phase 1** has been verified and confirmed in the Supabase Dashboard.

---

## Phase 1: Comprehensive Multi-Catalog Baseline Verification

Do **not** rely solely on a table count. Run the following comprehensive baseline inspection query in the Supabase SQL Editor before applying any DDL:

```sql
-- Comprehensive Pre-Execution Baseline Audit Query
SELECT 
    'tables' AS object_type, 
    count(*) AS count 
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
UNION ALL
SELECT 
    'views' AS object_type, 
    count(*) AS count 
FROM information_schema.views 
WHERE table_schema = 'public'
UNION ALL
SELECT 
    'materialized_views' AS object_type, 
    count(*) AS count 
FROM pg_matviews 
WHERE schemaname = 'public'
UNION ALL
SELECT 
    'routines_or_functions' AS object_type, 
    count(*) AS count 
FROM information_schema.routines 
WHERE routine_schema = 'public'
UNION ALL
SELECT 
    'policies_in_public' AS object_type, 
    count(*) AS count 
FROM pg_policies 
WHERE schemaname = 'public'
UNION ALL
SELECT 
    'extensions_installed' AS object_type, 
    count(*) AS count 
FROM pg_extension;
```

### Baseline Sign-Off Table:

| Catalog Check | Verification Query / Procedure | Pass Criteria | Status |
|:---:|---|---|:---:|
| **1.1 Dedicated Project Ref** | Browser URL: `https://supabase.com/dashboard/project/<PROJECT_REF>`. | Matches 20-char project ref in `.env`. | `[PENDING]` |
| **1.2 Base Tables** | `information_schema.tables WHERE table_schema = 'public'` | Exactly `0` application tables. | `[PENDING]` |
| **1.3 Views** | `information_schema.views WHERE table_schema = 'public'` | `0` custom application views. | `[PENDING]` |
| **1.4 Materialized Views** | `pg_matviews WHERE schemaname = 'public'` | `0` materialized views. | `[PENDING]` |
| **1.5 Custom Functions** | `information_schema.routines WHERE routine_schema = 'public'` | `0` custom application routines. | `[PENDING]` |
| **1.6 Policies on Public** | `pg_policies WHERE schemaname = 'public'` | `0` existing policies. | `[PENDING]` |
| **1.7 Backup / PITR** | **Settings** $\rightarrow$ **Database** $\rightarrow$ **Backups**. | Automated backups or PITR active. | `[PENDING]` |

---

## Phase 2: Local Script Preparation & Verification

| Step | Check Item | Required Action / Verification | Status |
|:---:|---|---|:---:|
| **2.1** | **Script Location** | Locate [`supabase/proposals/luxe_phase16_canonical_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_canonical_first_install.sql). | `[CONFIRMED]` |
| **2.2** | **Password Substitution** | On line 31, replace `'REPLACE_WITH_STRONG_PASSWORD'` with a cryptographically secure, high-entropy password for `luxe_app_user`. | `[PENDING OPERATOR]` |
| **2.3** | **Transaction Enclosure** | Verify the script opens with `BEGIN;` (line 20) and ends with `COMMIT;` (line 319). | `[CONFIRMED]` |
| **2.4** | **Narrow Scoping Verified** | Verify lines 256–283 explicitly name the 11 LUXE.TECH tables (no wildcard `ALL TABLES`). | `[CONFIRMED]` |
| **2.5** | **Zero Destructive DDL** | Verify zero `DROP TABLE`, `TRUNCATE`, `DROP SCHEMA`, or `CASCADE` statements. | `[CONFIRMED]` |
| **2.6** | **Storage Decoupling** | Verify storage bucket provisioning is **not** present in the script. | `[CONFIRMED]` |

---

## Phase 3: Execution in Supabase SQL Editor

1. [ ] Log in to **Supabase Dashboard** and open the dedicated LUXE.TECH project.
2. [ ] Click **SQL Editor** $\rightarrow$ **New Query**. Name the tab `001_luxe_canonical_first_install`.
3. [ ] Copy the entire text of [`luxe_phase16_canonical_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_canonical_first_install.sql).
4. [ ] Paste into the SQL Editor.
5. [ ] Replace `'REPLACE_WITH_STRONG_PASSWORD'` with the generated runtime password.
6. [ ] Click **Run** (or press `Ctrl+Enter`).
7. [ ] Confirm the output displays: **`Success. No rows returned`** (or transaction committed).

---

## Phase 4: Immediate Post-Execution Verification Queries

Open a new query tab in SQL Editor and execute each query:

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

### Check 4.6: Verify PostgREST Fail-Closed Status on LUXE.TECH Tables
```sql
SELECT table_name, privilege_type, grantee
FROM information_schema.table_privileges
WHERE table_schema = 'public' 
  AND table_name IN ('users', 'trends', 'saved_trends', 'collections', 'products')
  AND grantee IN ('anon', 'authenticated');
```
- [ ] **Expected Output:** `0 rows` (All direct privileges revoked from public roles).

---

## Phase 5: Storage Bucket Provisioning (Decoupled Step)

1. [ ] Review [`supabase/proposals/luxe_phase16_storage_setup_proposal.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql).
2. [ ] In SQL Editor, execute the storage script OR configure in **Storage** $\rightarrow$ **New Bucket**:
   - `trend-images`: Public, 10 MB limit, image MIME whitelist (`image/jpeg`, `image/png`, `image/webp`).
   - `collections`: Public, 10 MB limit, image MIME whitelist.
   - `user-uploads`: Strictly Private, 10 MB limit, image MIME whitelist.
3. [ ] Verify buckets appear in Storage dashboard with correct public/private toggles.

---

## Phase 6: Application Runtime Configuration

1. [ ] Update `DATABASE_URL` in backend `.env` to connect via `luxe_app_user`:
   ```env
   DATABASE_URL="postgresql+psycopg://luxe_app_user:<GENERATED_PASSWORD>@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
   ```
2. [ ] Verify `connect_args={"prepare_threshold": None}` in `database.py` for transaction pooler mode.
3. [ ] Start FastAPI backend and verify that `init_db()` passes with zero missing tables or columns.

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

