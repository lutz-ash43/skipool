# Quick Database Fix - Manual SQL

## Run This SQL in Cloud SQL Console

Copy and paste this entire SQL script into your Cloud SQL console and execute it:

```sql
-- Manual Database Fix SQL
-- Run this directly in your Cloud SQL console to add all missing columns

-- TRIPS TABLE
ALTER TABLE trips ADD COLUMN IF NOT EXISTS start_location_text VARCHAR;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS start_lat FLOAT;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS start_lng FLOAT;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS departure_time VARCHAR(100);
ALTER TABLE trips ADD COLUMN IF NOT EXISTS available_seats INTEGER DEFAULT 3;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS is_realtime BOOLEAN DEFAULT FALSE;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS current_lat FLOAT;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS current_lng FLOAT;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS last_location_update TIMESTAMP;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS trip_date DATE;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE trips ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;

-- RIDE_REQUESTS TABLE
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS pickup_lat FLOAT;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS pickup_lng FLOAT;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS pickup_address VARCHAR;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS departure_time VARCHAR(100);
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'pending';
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS current_lat FLOAT;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS current_lng FLOAT;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS last_location_update TIMESTAMP;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS request_date DATE;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS matched_trip_id INTEGER;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS suggested_hub_id VARCHAR(20);
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE ride_requests ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;
```

## How to Run

### Option 1: Cloud SQL Console (Easiest)
1. Go to [Google Cloud Console](https://console.cloud.google.com/sql)
2. Click on your database instance: `skipooldb`
3. Click "Databases" → Select `skipooldb`
4. Click "Connect using Cloud Shell" or use the SQL editor
5. Paste and run the SQL above

### Option 2: Using gcloud CLI
```bash
gcloud sql connect skipooldb --user=postgres --project=skipool-483602
```
Then paste the SQL commands.

### Option 3: Using psql (if you have Cloud SQL Proxy)
```bash
psql "postgresql://postgres:SkiPoolTest_1@/skipooldb?host=/cloudsql/skipool-483602:us-central1:skipooldb"
```
Then paste the SQL commands.

## What Gets Added

### `trips` table (12 columns):
- `start_location_text`, `start_lat`, `start_lng`
- `departure_time`, `available_seats`, `is_realtime`
- `current_lat`, `current_lng`, `last_location_update`
- `trip_date`, `created_at`, `updated_at`

### `ride_requests` table (13 columns):
- `pickup_lat`, `pickup_lng`, `pickup_address`
- `departure_time`, `status`
- `current_lat`, `current_lng`, `last_location_update`
- `request_date`, `matched_trip_id`, `suggested_hub_id`
- `created_at`, `updated_at`

## Verification

After running, verify with:

```sql
-- Check trips columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'trips' 
ORDER BY ordinal_position;

-- Check ride_requests columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'ride_requests' 
ORDER BY ordinal_position;
```

You should see all columns listed above.

## Notes

- ✅ Safe to run multiple times (uses `IF NOT EXISTS`)
- ✅ Won't delete existing data
- ✅ All new columns are nullable (except where DEFAULT is set)
- ✅ Existing rows will have NULL values for new columns
