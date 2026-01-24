# Migration Timeout Fix

## Changes Made

### 1. Increased Cloud Run Job Timeout
- **Before**: 300 seconds (5 minutes)
- **After**: 600 seconds (10 minutes)
- **Location**: `deploy-migration-cloudbuild.sh`

### 2. Increased Resources
- **Memory**: 512Mi → 1Gi
- **CPU**: 1 → 2
- This helps with database connection and query performance

### 3. Added Database Connection Timeouts
- **Connection timeout**: 30 seconds
- **Statement timeout**: 60 seconds
- **Location**: `database.py`

### 4. Optimized Column Existence Check
- **Before**: Used SQLAlchemy inspector (slower)
- **After**: Direct SQL query (faster)
- **Location**: `migrate_database.py`

## Redeploy the Migration Job

After these changes, redeploy the job:

```bash
./deploy-migration-cloudbuild.sh
```

Then execute:

```bash
gcloud run jobs execute skipool-migration --region=us-central1 --project=skipool-483602
```

## If It Still Times Out

### Option 1: Run Migration in Smaller Batches

Split the migration into two separate jobs:
1. Migrate `trips` table
2. Migrate `ride_requests` table

### Option 2: Use SQL Script Directly

Instead of Cloud Run job, run the SQL script directly:

```bash
# Connect to database
gcloud sql connect skipooldb --user=postgres --project=skipool-483602

# Then run:
\i migration.sql
```

Or use Cloud SQL Admin API:

```bash
gcloud sql databases execute-sql skipooldb \
  --sql-file=migration.sql \
  --project=skipool-483602
```

### Option 3: Manual Column Addition

Add columns one at a time via Cloud SQL console or psql.

## Monitoring

Watch the logs in real-time:

```bash
gcloud run jobs executions tail \
  --job=skipool-migration \
  --region=us-central1 \
  --project=skipool-483602
```

## Expected Duration

With optimizations:
- **Small database** (< 1000 rows): 10-30 seconds
- **Medium database** (1000-10000 rows): 30-60 seconds
- **Large database** (> 10000 rows): 1-3 minutes

If it takes longer than 5 minutes, there may be:
- Network connectivity issues
- Database lock contention
- Very large tables
