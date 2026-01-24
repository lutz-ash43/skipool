-- Manual Database Fix SQL
-- Run this directly in your Cloud SQL console to add all missing columns
-- Safe to run multiple times (uses IF NOT EXISTS)

-- ============================================
-- TRIPS TABLE - Add All Missing Columns
-- ============================================

-- Core columns
ALTER TABLE trips ADD COLUMN IF NOT EXISTS start_location_text VARCHAR;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS start_lat FLOAT;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS start_lng FLOAT;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS departure_time VARCHAR(100);
ALTER TABLE trips ADD COLUMN IF NOT EXISTS available_seats INTEGER DEFAULT 3;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS is_realtime BOOLEAN DEFAULT FALSE;

-- Real-time location tracking
ALTER TABLE trips ADD COLUMN IF NOT EXISTS current_lat FLOAT;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS current_lng FLOAT;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS last_location_update TIMESTAMP;

-- Scheduled rides
ALTER TABLE trips ADD COLUMN IF NOT EXISTS trip_date DATE;

-- Timestamps
ALTER TABLE trips ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

-- ============================================
-- RIDE_REQUESTS TABLE - Add All Missing Columns
-- ============================================

-- Core columns
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS pickup_lat FLOAT;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS pickup_lng FLOAT;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS pickup_address VARCHAR;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS departure_time VARCHAR(100);
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'pending';

-- Real-time location tracking
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS current_lat FLOAT;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS current_lng FLOAT;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS last_location_update TIMESTAMP;

-- Scheduled rides
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS request_date DATE;

-- Matching relationships
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS matched_trip_id INTEGER;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS suggested_hub_id VARCHAR(20);

-- Timestamps
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

-- ============================================
-- FOREIGN KEY CONSTRAINT (if not exists)
-- ============================================

-- Check and add foreign key constraint
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
-- VERIFICATION - Check All Columns Exist
-- ============================================

-- Verify trips table columns
SELECT 
    'trips' as table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'trips'
ORDER BY ordinal_position;

-- Verify ride_requests table columns
SELECT 
    'ride_requests' as table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'ride_requests'
ORDER BY ordinal_position;
