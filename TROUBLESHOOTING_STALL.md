# Troubleshooting: App Stalls When Posting Rides

## Most Likely Causes

### 1. Geocoding Timeout ⚠️ **FIXED**

The `geolocator.geocode()` calls were hanging indefinitely. I've added:
- 10-second timeout on geocoding
- Error handling with clear error messages
- Fallback to provided coordinates

**What was fixed:**
- Added `timeout=10` to geocoding calls
- Added try/except blocks
- Added validation to ensure coordinates exist before database insert

### 2. Database Connection Issues

If the database connection is slow or timing out:

**Check:**
- Cloud SQL instance is running
- Network connectivity from Cloud Run to Cloud SQL
- Connection pool settings

**Solution:**
The connection string uses Unix socket which should be fast, but you can add connection pooling:

```python
from sqlalchemy.pool import NullPool

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=NullPool,  # Or use QueuePool with limits
    pool_pre_ping=True,  # Verify connections before using
    connect_args={"connect_timeout": 10}
)
```

### 3. Missing Required Fields

Check if all required fields are being sent:

**For trips:**
- `driver_name` ✅
- `resort` ✅
- `departure_time` ✅
- Either `current_lat`/`current_lng` OR `start_location_text` ✅

**For ride_requests:**
- `passenger_name` ✅
- `resort` ✅
- Either `lat`/`lng` OR `pickup_text` ✅

### 4. Database Transaction Issues

If the database commit is hanging:

**Check logs for:**
- Database lock errors
- Transaction timeout errors
- Connection pool exhaustion

**Solution:**
Add explicit transaction handling:

```python
try:
    db.add(new_trip)
    db.commit()
    db.refresh(new_trip)
except Exception as e:
    db.rollback()
    raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
```

## How to Debug

### 1. Check Cloud Run Logs

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=skidb-backend" \
  --limit=50 \
  --project=skipool-483602 \
  --format=json
```

Look for:
- Timeout errors
- Database connection errors
- Geocoding errors
- Stack traces

### 2. Add Logging to Endpoints

Add logging to see where it's stalling:

```python
import logging
logger = logging.getLogger(__name__)

@app.post("/trips/", response_model=schemas.Trip)
def create_trip(trip: schemas.TripCreate, db: Session = Depends(get_db)):
    logger.info(f"Creating trip for {trip.driver_name}")
    
    lat, lng = trip.current_lat, trip.current_lng
    logger.info(f"Initial coordinates: {lat}, {lng}")
    
    if trip.start_location_text:
        logger.info(f"Geocoding address: {trip.start_location_text}")
        try:
            loc = geolocator.geocode(f"{trip.start_location_text}, Utah", timeout=10)
            # ... rest of code
        except Exception as e:
            logger.error(f"Geocoding failed: {e}")
            # ... error handling
    
    logger.info("Creating database record...")
    new_trip = Trip(...)
    db.add(new_trip)
    logger.info("Committing to database...")
    db.commit()
    logger.info("Trip created successfully")
    return new_trip
```

### 3. Test with Minimal Data

Try posting with GPS coordinates (no geocoding):

```json
{
  "driver_name": "Test",
  "resort": "Alta",
  "departure_time": "Now",
  "current_lat": 40.7,
  "current_lng": -111.8,
  "is_realtime": true
}
```

If this works, the issue is geocoding. If it still stalls, it's likely database-related.

### 4. Check Database Schema

Verify all columns exist:

```sql
-- Check trips table
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'trips';

-- Check ride_requests table
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'ride_requests';
```

## Quick Fixes Applied

✅ Added 10-second timeout to geocoding
✅ Added error handling for geocoding failures
✅ Added validation to ensure coordinates exist
✅ Added clear error messages

## Next Steps

1. **Deploy the updated code** with timeout fixes
2. **Test with GPS coordinates** (bypass geocoding)
3. **Check Cloud Run logs** for errors
4. **Monitor response times** in Cloud Run metrics

If it still stalls after these fixes, the issue is likely:
- Database connection timeout
- Network issues between Cloud Run and Cloud SQL
- Database lock/transaction issues
