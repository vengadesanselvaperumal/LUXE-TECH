# LUXE.TECH — Phase 16: Supabase Database Setup Runbook

**Document Location:** `supabase/proposals/PHASE_16_SUPABASE_SETUP_RUNBOOK.md`  
**Status:** OPERATIONAL EXECUTION GUIDE (Requires Explicit User Sign-Off Before Running)  
**Target Environment:** Dedicated LUXE.TECH Supabase Project  
**Author:** LUXE.TECH Senior Backend & Database Security Engineering  
**Date:** October 10, 2026  

---

## 1. Scope & Pre-Execution Governance

This runbook provides the exact, human-reviewed procedure for applying the initial LUXE.TECH application schema in the **Supabase SQL Editor**.

> [!CAUTION]
> **SAFETY PREREQUISITES:**
> 1. Do NOT execute this script against any shared, legacy, or unverified Supabase project.
> 2. Ensure the active project reference in the Supabase Dashboard URL matches character-for-character the dedicated LUXE.TECH project.
> 3. Verify that zero application tables currently exist in the `public` schema before proceeding.

---

## 2. Pre-Execution Checklist in Supabase Management Console

Before opening the SQL Editor, perform these three verifications:

### Check 2.1: Confirm Dedicated Project Identity
- In your browser, navigate to your Supabase Dashboard: `https://supabase.com/dashboard/project/<PROJECT_REF>`.
- Confirm that `<PROJECT_REF>` matches the 20-character identifier configured in your local `.env`.
- Ensure no other active applications share this Supabase project.

### Check 2.2: Confirm Clean Baseline
- In the left sidebar, click **SQL Editor**.
- Run this query:
  ```sql
  SELECT table_name, table_type
  FROM information_schema.tables
  WHERE table_schema = 'public';
  ```
- **Expected Result:** `0 rows` (or only Supabase default system views). If any tables from an existing application exist, **HALT IMMEDIATELY**.

### Check 2.3: Verify Backup Status
- In the left sidebar, navigate to **Settings** $\rightarrow$ **Database** $\rightarrow$ **Backups**.
- Verify that daily automated backups or Point-in-Time Recovery (PITR) are enabled and operational.

---

## 3. Preparation of the SQL Script

The canonical first-install script is located at:  
[`supabase/proposals/luxe_phase16_canonical_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_canonical_first_install.sql)

### Critical Edits to Perform in the Script Before Execution:
1. **Password Substitution:**
   Locate line 31 in `luxe_phase16_canonical_first_install.sql`:
   ```sql
   PASSWORD 'REPLACE_WITH_STRONG_PASSWORD'
   ```
   Replace `'REPLACE_WITH_STRONG_PASSWORD'` with a cryptographically secure, high-entropy password generated for `luxe_app_user`. Store this password securely in your password manager.
2. **Transaction Integrity:**
   Ensure the script begins with `BEGIN;` and concludes with `COMMIT;`. This guarantees that if any statement encounters an error, the entire batch rolls back atomically.
3. **Zero Destructive Commands:**
   Verify that the script contains zero `DROP TABLE`, `TRUNCATE`, or `CASCADE` commands.

---

## 4. Execution Procedure in Supabase SQL Editor

1. Open **Supabase Dashboard** $\rightarrow$ **SQL Editor**.
2. Click **New Query**. Name the tab `001_luxe_canonical_first_install`.
3. Copy the entire contents of [`luxe_phase16_canonical_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_canonical_first_install.sql).
4. Paste into the SQL Editor.
5. Update the password placeholder for `luxe_app_user`.
6. Click **Run** (or press `Ctrl+Enter` / `Cmd+Enter`).
7. Confirm the result banner shows **`Success. No rows returned`** (or transaction committed).

---

## 5. Post-Execution Verification Queries (Copy & Paste)

Immediately after running the script, open a new SQL Editor tab and run each verification query below:

### Query 5.1: Verify All 11 Application Tables Exist
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;
```
**Expected Output (Exactly 11 tables):**
- `collections`
- `forecasts`
- `images`
- `products`
- `prophecy`
- `retail_signals`
- `saved_trends`
- `trend_dna`
- `trend_signals`
- `trends`
- `users`

---

### Query 5.2: Verify Row Level Security Is Enabled on All Tables
```sql
SELECT relname AS table_name, relrowsecurity AS rls_enabled
FROM pg_class
WHERE relnamespace = 'public'::regnamespace AND relkind = 'r'
ORDER BY relname;
```
**Expected Output:** All 11 tables must report `rls_enabled = true`.

---

### Query 5.3: Verify Runtime RLS Policies for `luxe_app_user`
```sql
SELECT tablename, policyname, roles, cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename;
```
**Expected Output:** Exactly 11 policies named `app_runtime_all`, targeting `{luxe_app_user}` with command `ALL`.

---

### Query 5.4: Verify Explicit Indexes (12 Indexes)
```sql
SELECT tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public' AND indexname LIKE 'ix_%'
ORDER BY tablename, indexname;
```
**Expected Output (Exactly 12 indexes):**
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

---

### Query 5.5: Verify Least-Privilege Role Attributes for `luxe_app_user`
```sql
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls
FROM pg_roles
WHERE rolname = 'luxe_app_user';
```
**Expected Output:**
- `rolname`: `luxe_app_user`
- `rolsuper`: `false`
- `rolcreaterole`: `false`
- `rolcreatedb`: `false`
- `rolbypassrls`: `false`

---

### Query 5.6: Verify PostgREST Fail-Closed Status
```sql
SELECT table_name, privilege_type, grantee
FROM information_schema.table_privileges
WHERE table_schema = 'public' AND grantee IN ('anon', 'authenticated');
```
**Expected Output:** `0 rows` (All privileges revoked from `anon` and `authenticated`).

---

## 6. Decoupled Step: Storage Bucket Provisioning

Storage bucket provisioning is kept strictly separate from the core table DDL.

1. Review [`supabase/proposals/luxe_phase16_storage_setup_proposal.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase16_storage_setup_proposal.sql).
2. It provisions:
   - `trend-images`: Public CDN read, 10 MB limit, image MIME whitelist.
   - `collections`: Public CDN read, 10 MB limit, image MIME whitelist.
   - `user-uploads`: Strictly private, 10 MB limit, image MIME whitelist, signed URL access only.
3. Execute the storage SQL script in the SQL Editor, OR create the three buckets directly via **Supabase Dashboard** $\rightarrow$ **Storage** $\rightarrow$ **New Bucket** with matching parameters.

---

## 7. Application Configuration Update (FastAPI `.env`)

Once the database schema is verified:
1. Update `DATABASE_URL` in `.env` to connect via the newly provisioned least-privilege role `luxe_app_user`:
   ```env
   DATABASE_URL="postgresql+psycopg://luxe_app_user:<GENERATED_PASSWORD>@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
   ```
2. Note on Transaction Pooler: In `backend/app/database.py`, ensure psycopg connects with `prepare_threshold=None` if prepared statements are disabled on the pooler.

---

## 8. Abort & Emergency Recovery Protocol

### Day-0 Fresh Install Abort (Empty Database Only)
If the script encounters a syntax or permission error during initial execution:
1. Because the script is enclosed in `BEGIN; ... COMMIT;`, PostgreSQL will automatically execute `ROLLBACK;`.
2. If partial statements were executed outside a transaction, you may drop the newly created empty tables:
   ```sql
   -- ONLY PERMISSIBLE ON DAY-0 WITH ZERO REAL USER DATA:
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
Once real users and operational data exist in production, **destructive DDL (`DROP TABLE`, `TRUNCATE`, `CASCADE`) is permanently prohibited**. Any schema fixes must be applied via forward migrations (`ALTER TABLE`). Data recovery must use Supabase Point-in-Time Recovery (PITR) or daily automated snapshot restores.

