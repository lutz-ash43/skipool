-- Ensure all columns from models.py exist. Target: BigQuery.
-- Replace `project.dataset` with your project and dataset (e.g. myproject.skipooldb).
-- Uses ADD COLUMN IF NOT EXISTS where supported; otherwise ignore "already exists" errors.

-- ========== TRIPS ==========
ALTER TABLE `project.dataset.trips` ADD COLUMN IF NOT EXISTS driver_name STRING;
ALTER TABLE `project.dataset.trips` ADD COLUMN IF NOT EXISTS resort STRING;
ALTER TABLE `project.dataset.trips` ADD COLUMN IF NOT EXISTS start_location_text STRING;
ALTER TABLE `project.dataset.trips` ADD COLUMN IF NOT EXISTS start_lat FLOAT64;
ALTER TABLE `project.dataset.trips` ADD COLUMN IF NOT EXISTS start_lng FLOAT64;
ALTER TABLE `project.dataset.trips` ADD COLUMN IF NOT EXISTS current_lat FLOAT64;
ALTER TABLE `project.dataset.trips` ADD COLUMN IF NOT EXISTS current_lng FLOAT64;
ALTER TABLE `project.dataset.trips` ADD COLUMN IF NOT EXISTS last_location_update TIMESTAMP;
ALTER TABLE `project.dataset.trips` ADD COLUMN IF NOT EXISTS departure_time STRING;
ALTER TABLE `project.dataset.trips` ADD COLUMN IF NOT EXISTS available_seats INT64;
ALTER TABLE `project.dataset.trips` ADD COLUMN IF NOT EXISTS is_realtime BOOL;
ALTER TABLE `project.dataset.trips` ADD COLUMN IF NOT EXISTS trip_date DATE;
ALTER TABLE `project.dataset.trips` ADD COLUMN IF NOT EXISTS created_at TIMESTAMP;
ALTER TABLE `project.dataset.trips` ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

-- ========== RIDE_REQUESTS ==========
ALTER TABLE `project.dataset.ride_requests` ADD COLUMN IF NOT EXISTS passenger_name STRING;
ALTER TABLE `project.dataset.ride_requests` ADD COLUMN IF NOT EXISTS resort STRING;
ALTER TABLE `project.dataset.ride_requests` ADD COLUMN IF NOT EXISTS pickup_lat FLOAT64;
ALTER TABLE `project.dataset.ride_requests` ADD COLUMN IF NOT EXISTS pickup_lng FLOAT64;
ALTER TABLE `project.dataset.ride_requests` ADD COLUMN IF NOT EXISTS pickup_address STRING;
ALTER TABLE `project.dataset.ride_requests` ADD COLUMN IF NOT EXISTS departure_time STRING;
ALTER TABLE `project.dataset.ride_requests` ADD COLUMN IF NOT EXISTS status STRING;
ALTER TABLE `project.dataset.ride_requests` ADD COLUMN IF NOT EXISTS current_lat FLOAT64;
ALTER TABLE `project.dataset.ride_requests` ADD COLUMN IF NOT EXISTS current_lng FLOAT64;
ALTER TABLE `project.dataset.ride_requests` ADD COLUMN IF NOT EXISTS last_location_update TIMESTAMP;
ALTER TABLE `project.dataset.ride_requests` ADD COLUMN IF NOT EXISTS request_date DATE;
ALTER TABLE `project.dataset.ride_requests` ADD COLUMN IF NOT EXISTS seats_needed INT64;
ALTER TABLE `project.dataset.ride_requests` ADD COLUMN IF NOT EXISTS matched_trip_id INT64;
ALTER TABLE `project.dataset.ride_requests` ADD COLUMN IF NOT EXISTS suggested_hub_id STRING;
ALTER TABLE `project.dataset.ride_requests` ADD COLUMN IF NOT EXISTS created_at TIMESTAMP;
ALTER TABLE `project.dataset.ride_requests` ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

-- ========== VERIFICATION ==========
-- SELECT table_name, column_name, data_type
-- FROM `project.dataset.INFORMATION_SCHEMA.COLUMNS`
-- WHERE table_name IN ('trips', 'ride_requests')
-- ORDER BY table_name, ordinal_position;
