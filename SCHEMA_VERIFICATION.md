# Complete Schema Verification

## Required Columns for App to Work

After adding `start_location_text` and `pickup_address`, here's the **complete list** of columns your database needs:

### ✅ `trips` Table (15 columns)

| Column | Type | Nullable | Used In Code | Status |
|--------|------|----------|--------------|--------|
| `id` | INTEGER | NO (PK) | All queries | ✅ Core |
| `driver_name` | VARCHAR | NO | create_trip, responses | ✅ Core |
| `resort` | VARCHAR | NO | create_trip, matching | ✅ Core |
| `start_location_text` | VARCHAR | YES | create_trip (geocoding) | ⚠️ **MISSING - ADD THIS** |
| `start_lat` | FLOAT | YES | create_trip, matching | ✅ Core |
| `start_lng` | FLOAT | YES | create_trip, matching | ✅ Core |
| `current_lat` | FLOAT | YES | location updates, matching | ✅ Added by migration |
| `current_lng` | FLOAT | YES | location updates, matching | ✅ Added by migration |
| `last_location_update` | TIMESTAMP | YES | location updates | ✅ Added by migration |
| `departure_time` | VARCHAR | NO | create_trip, matching | ✅ Core |
| `available_seats` | INTEGER | NO | create_trip, booking | ✅ Core |
| `is_realtime` | BOOLEAN | NO | create_trip, filtering | ✅ Core |
| `trip_date` | DATE | YES | scheduled matching | ✅ Added by migration |
| `created_at` | TIMESTAMP | YES | timestamps | ✅ Added by migration |
| `updated_at` | TIMESTAMP | YES | timestamps | ✅ Added by migration |

### ✅ `ride_requests` Table (13 columns)

| Column | Type | Nullable | Used In Code | Status |
|--------|------|----------|--------------|--------|
| `id` | INTEGER | NO (PK) | All queries | ✅ Core |
| `passenger_name` | VARCHAR | NO | create_ride_request | ✅ Core |
| `resort` | VARCHAR | NO | create_ride_request, matching | ✅ Core |
| `pickup_lat` | FLOAT | NO | create_ride_request, matching | ✅ Core |
| `pickup_lng` | FLOAT | NO | create_ride_request, matching | ✅ Core |
| `pickup_address` | VARCHAR | YES | create_ride_request | ⚠️ **MISSING - ADD THIS** |
| `departure_time` | VARCHAR | YES | create_ride_request, matching | ✅ Added by migration |
| `status` | VARCHAR | NO | create_ride_request, filtering | ✅ Core |
| `request_date` | DATE | YES | scheduled matching | ✅ Added by migration |
| `matched_trip_id` | INTEGER | YES (FK) | match confirmation | ✅ Added by migration |
| `suggested_hub_id` | VARCHAR | YES | match confirmation | ✅ Added by migration |
| `created_at` | TIMESTAMP | YES | timestamps | ✅ Added by migration |
| `updated_at` | TIMESTAMP | YES | timestamps | ✅ Added by migration |

## After Adding Missing Columns

Once you add:
- `trips.start_location_text`
- `ride_requests.pickup_address`

**Your database will be 100% compatible with the app logic!**

## Verification

Run the verification script to check:

```bash
python3 verify_schema.py
```

Or test via the health endpoint:
```
GET /health/db
```

## Column Usage in Code

### `trips.start_location_text`
- **Used in**: `create_trip()` - for geocoding manual addresses
- **When**: User provides text address instead of GPS
- **Impact**: App will fail if missing when trying to create trips with text addresses

### `ride_requests.pickup_address`
- **Used in**: `create_ride_request()` - stored but not actively used in queries
- **When**: Passenger provides text address
- **Impact**: App will fail if missing when trying to create ride requests

Both columns are nullable, so existing rows won't break, but new inserts will fail if the columns don't exist.
