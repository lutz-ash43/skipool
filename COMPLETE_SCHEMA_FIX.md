# Complete Schema Fix Guide

## Problem

The database tables were created with an incomplete schema. The migration script was only adding NEW columns, but some CORE columns from the original models were also missing.

## Solution

I've created a **complete fix** that adds ALL columns from `models.py`, not just the new ones.

## Quick Fix (Run This Now)

### Option 1: Run Complete SQL Script (Recommended)

Run `fix_all_columns.sql` in your Cloud SQL console:

```sql
-- This script checks and adds ALL columns from models.py
-- Safe to run multiple times (idempotent)
```

**How to run:**
1. Go to Cloud SQL Console
2. Open your database
3. Copy and paste the contents of `fix_all_columns.sql`
4. Execute

### Option 2: Run Updated Migration Script

The migration script has been updated to check for ALL columns. Redeploy and run:

```bash
./deploy-migration-cloudbuild.sh
gcloud run jobs execute skipool-migration --region=us-central1 --project=skipool-483602
```

## Complete Column List

### `trips` Table - ALL Required Columns:

1. ✅ `id` (INTEGER, PK) - Should exist
2. ✅ `driver_name` (VARCHAR) - Should exist
3. ✅ `resort` (VARCHAR) - Should exist
4. ⚠️ `start_location_text` (VARCHAR) - **MISSING**
5. ⚠️ `start_lat` (FLOAT) - **MISSING** (causing your error!)
6. ⚠️ `start_lng` (FLOAT) - **MISSING**
7. ⚠️ `departure_time` (VARCHAR) - **MISSING**
8. ⚠️ `available_seats` (INTEGER) - **MISSING**
9. ⚠️ `is_realtime` (BOOLEAN) - **MISSING**
10. ✅ `current_lat` (FLOAT) - Added by migration
11. ✅ `current_lng` (FLOAT) - Added by migration
12. ✅ `last_location_update` (TIMESTAMP) - Added by migration
13. ✅ `trip_date` (DATE) - Added by migration
14. ✅ `created_at` (TIMESTAMP) - Added by migration
15. ✅ `updated_at` (TIMESTAMP) - Added by migration

### `ride_requests` Table - ALL Required Columns:

1. ✅ `id` (INTEGER, PK) - Should exist
2. ✅ `passenger_name` (VARCHAR) - Should exist
3. ✅ `resort` (VARCHAR) - Should exist
4. ⚠️ `pickup_lat` (FLOAT) - **MISSING**
5. ⚠️ `pickup_lng` (FLOAT) - **MISSING**
6. ⚠️ `pickup_address` (VARCHAR) - **MISSING**
7. ⚠️ `departure_time` (VARCHAR) - **MISSING**
8. ⚠️ `status` (VARCHAR) - **MISSING**
9. ✅ `request_date` (DATE) - Added by migration
10. ✅ `matched_trip_id` (INTEGER) - Added by migration
11. ✅ `suggested_hub_id` (VARCHAR) - Added by migration
12. ✅ `created_at` (TIMESTAMP) - Added by migration
13. ✅ `updated_at` (TIMESTAMP) - Added by migration

## What Was Wrong

The original migration script assumed core columns already existed, but it looks like your tables were created with only:
- `id`, `driver_name`, `resort` (for trips)
- `id`, `passenger_name`, `resort` (for ride_requests)

All other columns need to be added!

## After Running the Fix

1. ✅ All columns from `models.py` will exist
2. ✅ Database will match app logic 100%
3. ✅ No more "column does not exist" errors
4. ✅ App will work correctly

## Verification

After running the fix, verify with:

```bash
python3 verify_schema.py
```

Or test the health endpoint:
```
GET /health/db
```

Both should work without errors!
