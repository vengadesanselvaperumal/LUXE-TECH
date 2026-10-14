-- ============================================================================
-- LUXE.TECH — Phase 16 Supabase Storage Setup (SEPARATE PROPOSAL)
-- Location: supabase/proposals/luxe_phase16_storage_setup_proposal.sql
-- Status: PROPOSAL ONLY (Offline Review — Kept Separate From Table DDL)
--
-- TARGET: Dedicated LUXE.TECH Supabase Project (Storage Configuration)
--
-- NOTE:
-- This script is completely decoupled from the core application schema DDL.
-- It provisions the three required storage buckets with strict 10 MB caps,
-- image-only MIME whitelists, and appropriate public/private visibility.
-- ============================================================================

BEGIN;

-- 1. PROVISION STORAGE BUCKETS
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

-- 2. STORAGE OBJECT ACCESS POLICIES
-- Public CDN Read for 'trend-images' and 'collections'
CREATE POLICY "Public Read Trend Images" ON storage.objects
    FOR SELECT
    USING (bucket_id = 'trend-images');

CREATE POLICY "Public Read Collections" ON storage.objects
    FOR SELECT
    USING (bucket_id = 'collections');

-- Note on 'user-uploads':
-- Zero public policies are defined for 'user-uploads'.
-- Objects in 'user-uploads' can only be accessed via temporary signed URLs
-- generated server-side by FastAPI via the Supabase Storage Service Key.

COMMIT;

