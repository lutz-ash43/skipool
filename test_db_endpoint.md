# Testing Database Connection

## Quick Test: Use Health Check Endpoint

I've added a `/health/db` endpoint to your FastAPI app. After deploying, you can test the database connection by calling:

```bash
curl https://skidb-backend-286587511166.us-central1.run.app/health/db
```

Or open in your browser:
```
https://skidb-backend-286587511166.us-central1.run.app/health/db
```

### Expected Response (Healthy):

```json
{
  "status": "healthy",
  "database_connected": true,
  "test_query": true,
  "tables_found": ["trips", "ride_requests"],
  "trips_count": 0,
  "ride_requests_count": 0,
  "timestamp": "2026-01-22T..."
}
```

### Expected Response (Unhealthy):

```json
{
  "status": "unhealthy",
  "database_connected": false,
  "error": "connection error message",
  "error_type": "OperationalError",
  "timestamp": "2026-01-22T..."
}
```

## Alternative: Test Script (Local)

If you want to test locally before deploying:

### Option 1: With Cloud SQL Proxy

1. Start Cloud SQL Proxy:
```bash
cloud_sql_proxy -instances=skipool-483602:us-central1:skipooldb=tcp:5432
```

2. Update database.py temporarily:
```python
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:SkiPoolTest_1@localhost:5432/skipooldb"
```

3. Run test script:
```bash
python3 test_connection.py
```

### Option 2: Direct Test (if you have psql)

```bash
psql "postgresql://postgres:SkiPoolTest_1@/skipooldb?host=/cloudsql/skipool-483602:us-central1:skipooldb"
```

## What the Health Check Tests

1. ✅ **Connection**: Can connect to database
2. ✅ **Query**: Can execute SQL queries
3. ✅ **Tables**: Verifies tables exist
4. ✅ **Data Access**: Can query trips and ride_requests tables

## Next Steps

1. **Deploy the updated code** (with health check endpoint)
2. **Call the health endpoint** to verify connection
3. **If healthy**: Proceed with testing ride posting
4. **If unhealthy**: Check the error message and troubleshoot

The health endpoint will help you quickly identify if the issue is:
- Database connection problems
- Missing tables
- Permission issues
- Network connectivity
