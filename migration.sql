-- SkiPool Database Migration SQL Script
-- Run this in your GCP Cloud SQL console or via psql
-- 
-- IMPORTANT: 
-- - Backup your database first!
-- - This script is idempotent (safe to run multiple times)
-- - All new columns are nullable, so existing data is preserved

-- ============================================
-- TRIPS TABLE MIGRATIONS - COMPLETE COLUMN LIST
-- ============================================

-- Core columns that might be missing from original table creation

-- start_location_text
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'start_location_text'
    ) THEN
        ALTER TABLE trips ADD COLUMN start_location_text VARCHAR;
    END IF;
END $$;

-- start_lat
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'start_lat'
    ) THEN
        ALTER TABLE trips ADD COLUMN start_lat FLOAT;
    END IF;
END $$;

-- start_lng
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'start_lng'
    ) THEN
        ALTER TABLE trips ADD COLUMN start_lng FLOAT;
    END IF;
END $$;

-- departure_time
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'departure_time'
    ) THEN
        ALTER TABLE trips ADD COLUMN departure_time VARCHAR(100);
    END IF;
END $$;

-- available_seats
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'available_seats'
    ) THEN
        ALTER TABLE trips ADD COLUMN available_seats INTEGER DEFAULT 3;
    END IF;
END $$;

-- is_realtime
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'is_realtime'
    ) THEN
        ALTER TABLE trips ADD COLUMN is_realtime BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- New columns from migration

-- current_lat column (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'current_lat'
    ) THEN
        ALTER TABLE trips ADD COLUMN current_lat FLOAT;
    END IF;
END $$;

-- Add current_lng column (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'current_lng'
    ) THEN
        ALTER TABLE trips ADD COLUMN current_lng FLOAT;
    END IF;
END $$;

-- Add last_location_update column (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'last_location_update'
    ) THEN
        ALTER TABLE trips ADD COLUMN last_location_update TIMESTAMP;
    END IF;
END $$;

-- Add trip_date column (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'trip_date'
    ) THEN
        ALTER TABLE trips ADD COLUMN trip_date DATE;
    END IF;
END $$;

-- Add created_at column (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE trips ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

-- Add updated_at column (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE trips ADD COLUMN updated_at TIMESTAMP;
    END IF;
END $$;

-- ============================================
-- RIDE_REQUESTS TABLE MIGRATIONS - COMPLETE COLUMN LIST
-- ============================================

-- Core columns that might be missing from original table creation

-- pickup_lat
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'pickup_lat'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN pickup_lat FLOAT;
    END IF;
END $$;

-- pickup_lng
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'pickup_lng'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN pickup_lng FLOAT;
    END IF;
END $$;

-- pickup_address
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'pickup_address'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN pickup_address VARCHAR;
    END IF;
END $$;

-- departure_time
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'departure_time'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN departure_time VARCHAR(100);
    END IF;
END $$;

-- status
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'status'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN status VARCHAR(50) DEFAULT 'pending';
    END IF;
END $$;

-- Add request_date column (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'request_date'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN request_date DATE;
    END IF;
END $$;

-- Add matched_trip_id column (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'matched_trip_id'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN matched_trip_id INTEGER;
    END IF;
END $$;

-- Add suggested_hub_id column (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'suggested_hub_id'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN suggested_hub_id VARCHAR(10);
    END IF;
END $$;

-- Add created_at column (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

-- Add updated_at column (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN updated_at TIMESTAMP;
    END IF;
END $$;

-- ============================================
-- FOREIGN KEY CONSTRAINT
-- ============================================

-- Add foreign key constraint (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'ride_requests_matched_trip_id_fkey'
        AND table_name = 'ride_requests'
    ) THEN
        ALTER TABLE ride_requests 
        ADD CONSTRAINT ride_requests_matched_trip_id_fkey 
        FOREIGN KEY (matched_trip_id) REFERENCES trips(id);
    END IF;
END $$;

-- ============================================
-- VERIFICATION
-- ============================================

-- Verify all columns were added
SELECT 
    'trips' as table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'trips'
ORDER BY ordinal_position;

SELECT 
    'ride_requests' as table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'ride_requests'
ORDER BY ordinal_position;
