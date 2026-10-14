-- Upgrade databases created by the original 001 migration to match the
-- SQLAlchemy column names and TEXT-based JSON serialization used by the app.
-- Run only after reviewing the target project and taking a database backup.
DO $align_schema$
DECLARE
    item RECORD;
    current_type TEXT;
    old_exists BOOLEAN;
    new_exists BOOLEAN;
BEGIN
    FOR item IN
        SELECT *
        FROM (VALUES
            ('trend_signals', 'metadata', 'metadata_json', '{}'),
            ('trend_dna', 'colors', 'colors_json', '[]'),
            ('trend_dna', 'materials', 'materials_json', '[]'),
            ('trend_dna', 'textures', 'textures_json', '[]'),
            ('trend_dna', 'silhouettes', 'silhouettes_json', '[]'),
            ('trend_dna', 'patterns', 'patterns_json', '[]'),
            ('images', 'dominant_colors', 'dominant_colors_json', '[]'),
            ('collections', 'color_palette', 'color_palette_json', '[]'),
            ('collections', 'materials', 'materials_json', '[]'),
            ('collections', 'textures', 'textures_json', '[]'),
            ('collections', 'silhouettes', 'silhouettes_json', '[]'),
            ('collections', 'patterns', 'patterns_json', '[]'),
            ('collections', 'product_opportunities', 'product_opportunities_json', '[]'),
            ('prophecy', 'evidence', 'evidence_json', '[]')
        ) AS column_map(table_name, old_name, new_name, text_default)
    LOOP
        IF to_regclass(format('public.%I', item.table_name)) IS NULL THEN
            CONTINUE;
        END IF;

        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = item.table_name
              AND column_name = item.old_name
        ) INTO old_exists;
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = item.table_name
              AND column_name = item.new_name
        ) INTO new_exists;

        IF old_exists AND new_exists THEN
            RAISE EXCEPTION 'Both %.% and %.% exist; resolve the duplicate columns before continuing',
                item.table_name, item.old_name, item.table_name, item.new_name;
        ELSIF old_exists THEN
            EXECUTE format(
                'ALTER TABLE public.%I RENAME COLUMN %I TO %I',
                item.table_name, item.old_name, item.new_name
            );
            new_exists := TRUE;
        END IF;

        IF new_exists THEN
            SELECT data_type INTO current_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = item.table_name
              AND column_name = item.new_name;

            IF current_type IN ('json', 'jsonb') THEN
                EXECUTE format(
                    'ALTER TABLE public.%I ALTER COLUMN %I DROP DEFAULT',
                    item.table_name, item.new_name
                );
                EXECUTE format(
                    'ALTER TABLE public.%I ALTER COLUMN %I TYPE TEXT USING %I::text',
                    item.table_name, item.new_name, item.new_name
                );
                EXECUTE format(
                    'ALTER TABLE public.%I ALTER COLUMN %I SET DEFAULT %L',
                    item.table_name, item.new_name, item.text_default
                );
            END IF;
        END IF;
    END LOOP;
END
$align_schema$;

-- Tighten legacy foreign-key columns only when existing rows satisfy the
-- application constraints; otherwise abort instead of changing/dropping data.
DO $nonnull_constraints$
DECLARE
    item RECORD;
    has_nulls BOOLEAN;
BEGIN
    FOR item IN
        SELECT *
        FROM (VALUES
            ('trend_signals', 'trend_id'),
            ('trend_dna', 'trend_id'),
            ('collections', 'trend_id'),
            ('forecasts', 'trend_id'),
            ('prophecy', 'trend_id'),
            ('saved_trends', 'user_id'),
            ('saved_trends', 'trend_id')
        ) AS required_columns(table_name, column_name)
    LOOP
        IF to_regclass(format('public.%I', item.table_name)) IS NULL THEN
            CONTINUE;
        END IF;

        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = item.table_name
              AND column_name = item.column_name
              AND is_nullable = 'YES'
        ) THEN
            EXECUTE format(
                'SELECT EXISTS (SELECT 1 FROM public.%I WHERE %I IS NULL)',
                item.table_name, item.column_name
            ) INTO has_nulls;
            IF has_nulls THEN
                RAISE EXCEPTION 'Cannot set %.% NOT NULL while NULL rows exist; review the data first',
                    item.table_name, item.column_name;
            END IF;
            EXECUTE format(
                'ALTER TABLE public.%I ALTER COLUMN %I SET NOT NULL',
                item.table_name, item.column_name
            );
        END IF;
    END LOOP;
END
$nonnull_constraints$;
