# LUXE.TECH — Phase 12 Security and Database Permissions Design

**Document Location:** `supabase/proposals/PHASE_12_SECURITY_AND_PERMISSIONS_DESIGN.md`  
**Status:** DRAFT PROPOSAL (Offline Review Only — Not Deployed)  
**Target:** Dedicated LUXE.TECH Supabase Project & FastAPI Backend Runtime

---

## 1. Runtime Database Permissions & Least-Privilege Role Design

### 1.1 The Risk of Administrative Database Connections
In many initial setups, the backend is configured using the default `postgres` superuser connection string. This presents significant security risks:
- Bypasses all Row Level Security (RLS) policies unconditionally.
- Possesses DDL capabilities (`DROP TABLE`, `ALTER TABLE`, `TRUNCATE`).
- Exposes administrative control of the entire PostgreSQL cluster if credentials leak.

### 1.2 Proposed Least-Privilege Runtime Role (`luxe_app_user`)
For production runtime operation, the FastAPI backend must connect via a dedicated least-privilege role that lacks superuser privileges and DDL authority.

```sql
-- DDL to be reviewed and executed during deployment (NOT executed now):
CREATE ROLE luxe_app_user WITH LOGIN PASSWORD '<secure_runtime_password>';

-- Grant schema access
GRANT USAGE ON SCHEMA public TO luxe_app_user;

-- Grant standard DML on application tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO luxe_app_user;

-- Grant sequence usage for auto-incrementing IDs (if any)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO luxe_app_user;

-- Ensure future tables retain these permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO luxe_app_user;
```

### 1.3 RLS Interaction with the Runtime Role
Under PostgreSQL, enabling Row Level Security on a table causes all queries from non-superusers without `BYPASSRLS` to be filtered by active RLS policies.
- **Do NOT grant `BYPASSRLS` to `luxe_app_user` automatically.** Granting `BYPASSRLS` completely disables database-level tenant isolation.
- Instead, define an explicit application service policy:
  ```sql
  -- Example application service policy for backend DML:
  CREATE POLICY app_runtime_all ON public.<table>
      FOR ALL
      TO luxe_app_user
      USING (true)
      WITH CHECK (true);
  ```
  This ensures that only queries originating from the authenticated backend connection are permitted, while direct PostgREST calls by `anon` or `authenticated` remain blocked.

---

## 2. Application Layer Authorization Architecture (FastAPI)

FastAPI enforces all domain authorization, ownership, and role-based access before database transactions occur.

### 2.1 Server-Side User Role Assignment
- **Public Registration:** Handled via `POST /api/auth/register`. The request schema `AuthRegisterRequest` accepts only `email`, `password`, and `name`. The `role` attribute is not part of the schema and is hardcoded server-side to `"user"`.
- **Administrative Roles:** Privileged roles (`lead_analyst`, `admin`) cannot be self-selected or escalated via client request bodies or headers. They can only be assigned directly in the database or via administrative provisioning scripts.

### 2.2 JWT Token Generation and Verification
- Tokens are minted using HS256 signed with `settings.SECRET_KEY`.
- The token payload embeds `sub` (user UUID) and `role` extracted from the database row:
  ```python
  token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
  ```
- Any client tampering with the payload invalidates the HMAC signature.

### 2.3 Route-Level Authorization Enforcement
1. **Public Discovery Routes (Read-Only):**
   - `GET /api/trends`, `GET /api/trends/{slug}`, `GET /api/products`, `GET /api/retail`, `GET /api/dashboard`.
   - Publicly readable to allow catalog browsing without authentication.
2. **Authenticated Personal Operations:**
   - `POST /api/trends/{trend_id}/save`, `GET /api/trends/saved`, `POST /api/images/analyze` (personal uploads).
   - Require `get_current_user`. Scoped strictly to `current_user["id"]`.
3. **Privileged Catalog Mutations:**
   - `POST /api/trends`, `POST /api/collections/generate`, `POST /api/products/generate`, `POST /api/forecast/{trend_id}`, `POST /api/prophecy/{trend_id}`.
   - Enforce `get_privileged_user` dependency:
     ```python
     PRIVILEGED_ROLES = frozenset({"admin", "lead_analyst"})
     if current_user.get("role") not in PRIVILEGED_ROLES:
         raise HTTPException(status_code=403, detail="Forbidden: Administrative or lead analyst privileges required...")
     ```

---

## 3. Disconnect Between Application JWT and Supabase Auth Identity

### 3.1 The Architectural Distinction
- **Supabase Auth:** Employs the `auth.users` table in the `auth` schema. When users log in via Supabase Auth, tokens contain claims that PostgREST understands, allowing PostgreSQL functions like `auth.uid()` and `auth.role()` to evaluate user identity in SQL RLS policies.
- **LUXE.TECH Application Auth:** Employs `public.users` and issues custom application JWTs signed with the backend's `SECRET_KEY`.

### 3.2 Consequences for Database Security
1. `auth.uid()` evaluates to `NULL` for LUXE.TECH application connections.
2. If RLS policies are written expecting `auth.uid() = user_id`, queries using custom JWTs will return zero rows.
3. Therefore, Row Level Security in Supabase must NOT rely on `auth.uid()` unless users are migrated to Supabase Auth.
4. Instead, RLS on application tables acts as a **fail-closed perimeter** that prevents unauthorized PostgREST API access, while the FastAPI backend enforces tenant isolation in Python/SQLAlchemy queries.

---

## 4. PostgREST API Protection & Public Catalog Exposure

### 4.1 Threat Model
Supabase automatically generates a RESTful API (PostgREST) over the `public` schema. If tables have permissive grants and RLS is not enabled, anonymous external clients can query PostgREST (`https://<project-ref>.supabase.co/rest/v1/users`) and scrape user accounts, email addresses, or unreleased trend data.

### 4.2 Fail-Closed Defense
1. **RLS Enabled with Zero Policies:**
   - By enabling RLS on all 11 tables without defining `anon` or `authenticated` policies, PostgREST queries from external users return `HTTP 200 []` (empty array) or `HTTP 401/403`.
2. **Revocation of Anonymous API Grants:**
   - During deployment hardening, explicitly revoke direct PostgREST access to sensitive tables:
     ```sql
     REVOKE ALL ON public.users FROM anon, authenticated;
     REVOKE ALL ON public.saved_trends FROM anon, authenticated;
     ```
3. **Application Gateway Pattern:**
   - All client traffic (frontend web app) communicates strictly with the FastAPI backend (`https://api.luxe.tech/api/...`). The backend queries the database and shapes the returned data. The Supabase PostgREST endpoint is not used for client data retrieval.

---

## 5. Storage Architecture: Public vs. Private Buckets

### 5.1 Bucket Separation Matrix

| Bucket Name | Visibility | Allowed Content | Access Mechanism | Expiration / Restrictions |
|---|---|---|---|---|
| `trend-images` | **Public** | Curated catalog imagery, trend banners | Direct CDN URL (`/storage/v1/object/public/trend-images/...`) | Public read; write restricted to privileged users |
| `collections` | **Public** | Capsule lookbooks, swatch boards | Direct CDN URL (`/storage/v1/object/public/collections/...`) | Public read; write restricted to privileged users |
| `user-uploads` | **Private** | Personal sketches, inspiration uploads | Signed URL (`/storage/v1/object/sign/user-uploads/...`) | 3600 seconds (1 hour); write restricted to authenticated users |

### 5.2 Upload Validation & Anti-DoS Controls
In [`validation.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/utils/validation.py):
- **Bounded Chunked Reads:** Reads incoming file streams in 64 KB chunks up to a strict maximum of 10 MB (`MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024`). Rejects oversized payloads immediately with `HTTP 413 Content Too Large`.
- **MIME & Extension Whitelist:** Only `.jpg`, `.jpeg`, `.png`, and `.webp` extensions and corresponding MIME types are accepted.
- **Image Signature & Pixel Decoding:** Pillow decodes images in memory to verify dimensions (minimum 10x10 px) and strips malicious non-image code.
- **Path Sanitization:** Filenames are sanitized via regex `[^a-zA-Z0-9._-]` to prevent directory traversal attacks.

### 5.3 Storage Path Namespacing
To prevent path-enumeration and cross-user data leakage:
- Private user uploads are namespaced by user ID:
  `storage_path = f"{current_user['id']}/{uuid.uuid4()}_{safe_filename}"`
- Catalog uploads are namespaced by trend ID:
  `storage_path = f"trends/{trend_id}/{uuid.uuid4()}_{safe_filename}"`

### 5.4 Verification of Signed URL Implementation
The implementation in [`supabase_service.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/services/supabase_service.py):
- Calls Supabase Storage sign API: `POST /storage/v1/object/sign/{bucket}/{path}` with `{"expiresIn": 3600}` using the service role key.
- Rejects any attempt to call `get_public_url()` on private buckets (`user-uploads`) by raising `ValueError`.
- Verified passing in test suite (`test_private_bucket_upload_returns_temporary_signed_url` and `test_private_bucket_cannot_be_given_a_public_url`).

