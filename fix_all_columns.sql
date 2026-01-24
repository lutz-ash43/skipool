-- Complete Column Fix Script
-- This ensures ALL columns from models.py exist in the database
-- Run this to fix any column mismatches

-- ============================================
-- TRIPS TABLE - Complete Column List
-- ============================================

-- id (primary key) - should already exist
-- driver_name - should already exist
-- resort - should already exist

-- start_location_text
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'start_location_text'
    ) THEN
        ALTER TABLE trips ADD COLUMN start_location_text VARCHAR;
        RAISE NOTICE 'Added start_location_text';
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
        RAISE NOTICE 'Added start_lat';
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
        RAISE NOTICE 'Added start_lng';
    END IF;
END $$;

-- current_lat
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'current_lat'
    ) THEN
        ALTER TABLE trips ADD COLUMN current_lat FLOAT;
        RAISE NOTICE 'Added current_lat';
    END IF;
END $$;

-- current_lng
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'current_lng'
    ) THEN
        ALTER TABLE trips ADD COLUMN current_lng FLOAT;
        RAISE NOTICE 'Added current_lng';
    END IF;
END $$;

-- last_location_update
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'last_location_update'
    ) THEN
        ALTER TABLE trips ADD COLUMN last_location_update TIMESTAMP;
        RAISE NOTICE 'Added last_location_update';
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
        RAISE NOTICE 'Added departure_time';
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
        RAISE NOTICE 'Added available_seats';
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
        RAISE NOTICE 'Added is_realtime';
    END IF;
END $$;

-- trip_date
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'trip_date'
    ) THEN
        ALTER TABLE trips ADD COLUMN trip_date DATE;
        RAISE NOTICE 'Added trip_date';
    END IF;
END $$;

-- created_at
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE trips ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE 'Added created_at';
    END IF;
END $$;

-- updated_at
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'trips' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE trips ADD COLUMN updated_at TIMESTAMP;
        RAISE NOTICE 'Added updated_at';
    END IF;
END $$;

-- ============================================
-- RIDE_REQUESTS TABLE - Complete Column List
-- ============================================

-- id (primary key) - should already exist
-- passenger_name - should already exist
-- resort - should already exist

-- pickup_lat
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'pickup_lat'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN pickup_lat FLOAT;
        RAISE NOTICE 'Added pickup_lat';
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
        RAISE NOTICE 'Added pickup_lng';
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
        RAISE NOTICE 'Added pickup_address';
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
        RAISE NOTICE 'Added departure_time';
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
        RAISE NOTICE 'Added status';
    END IF;
END $$;

-- request_date
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'request_date'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN request_date DATE;
        RAISE NOTICE 'Added request_date';
    END IF;
END $$;

-- matched_trip_id
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'matched_trip_id'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN matched_trip_id INTEGER;
        RAISE NOTICE 'Added matched_trip_id';
    END IF;
END $$;

-- suggested_hub_id
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'suggested_hub_id'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN suggested_hub_id VARCHAR(20);
        RAISE NOTICE 'Added suggested_hub_id';
    END IF;
END $$;

-- created_at
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'created_at'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE 'Added created_at';
    END IF;
END $$;

-- updated_at
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN updated_at TIMESTAMP;
        RAISE NOTICE 'Added updated_at';
    END IF;
END $$;

-- current_lat (for real-time passenger location tracking)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'current_lat'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN current_lat FLOAT;
        RAISE NOTICE 'Added current_lat';
    END IF;
END $$;

-- current_lng (for real-time passenger location tracking)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'current_lng'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN current_lng FLOAT;
        RAISE NOTICE 'Added current_lng';
    END IF;
END $$;

-- last_location_update (for real-time passenger location tracking)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ride_requests' AND column_name = 'last_location_update'
    ) THEN
        ALTER TABLE ride_requests ADD COLUMN last_location_update TIMESTAMP;
        RAISE NOTICE 'Added last_location_update';
    END IF;
END $$;

-- ============================================
-- VERIFICATION
-- ============================================

-- Show all columns in trips
SELECT 
    'trips' as table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'trips'
ORDER BY ordinal_position;

-- Show all columns in ride_requests
SELECT 
    'ride_requests' as table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'ride_requests'
ORDER BY ordinal_position;
