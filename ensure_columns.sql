-- Ensure all columns from models.py exist in trips and ride_requests.
-- PostgreSQL (Cloud SQL). Idempotent; safe to run multiple times.

-- ========== TRIPS ==========
ALTER TABLE trips ADD COLUMN IF NOT EXISTS driver_name VARCHAR;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS resort VARCHAR;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS start_location_text VARCHAR;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS start_lat DOUBLE PRECISION;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS start_lng DOUBLE PRECISION;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS current_lat DOUBLE PRECISION;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS current_lng DOUBLE PRECISION;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS last_location_update TIMESTAMP;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS departure_time VARCHAR;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS available_seats INTEGER DEFAULT 3;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS is_realtime BOOLEAN DEFAULT FALSE;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS trip_date DATE;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'utc');
ALTER TABLE trips ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

-- ========== RIDE_REQUESTS ==========
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS passenger_name VARCHAR;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS resort VARCHAR;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS pickup_lat DOUBLE PRECISION;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS pickup_lng DOUBLE PRECISION;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS pickup_address VARCHAR;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS departure_time VARCHAR;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'pending';
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS current_lat DOUBLE PRECISION;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS current_lng DOUBLE PRECISION;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS last_location_update TIMESTAMP;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS request_date DATE;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS seats_needed INTEGER DEFAULT 1;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS matched_trip_id INTEGER REFERENCES trips(id);
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS suggested_hub_id VARCHAR;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'utc');
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

-- ========== VERIFICATION ==========
-- Run this to confirm all columns exist:
/*
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('trips', 'ride_requests')
ORDER BY table_name, ordinal_position;
*/
