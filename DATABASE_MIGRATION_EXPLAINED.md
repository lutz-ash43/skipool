# Database Migration Explained

## How Database Migrations Work

### Current Situation

Your code uses `Base.metadata.create_all(bind=engine)` in `main.py` (line 13). This SQLAlchemy method:
- ✅ **Creates tables** if they don't exist
- ❌ **Does NOT modify** existing tables
- ❌ **Does NOT add columns** to existing tables

So if your `trips` and `ride_requests` tables already exist in GCP, the new fields we added to the models won't automatically appear in the database.

---

## What a Migration Does

A migration script:
1. **Connects to your GCP database** (yes, it needs to be running and accessible)
2. **Executes SQL ALTER TABLE commands** to add new columns
3. **Preserves existing data** (new columns are nullable, so existing rows get NULL values)
4. **Updates the schema** to match your Python models

---

## Does the Database Need to Be Running?

**YES** - The database instance must be:
- ✅ Running and accessible
- ✅ Reachable from where you run the migration (your local machine or Cloud Run)
- ✅ You must have proper credentials/network access

Your connection string uses Cloud SQL socket connection:
```
postgresql://postgres:SkiPoolTest_1@/skipooldb?host=/cloudsql/skipool-483602:us-central1:skipooldb
```

This means:
- If running locally: You need Cloud SQL Proxy running
- If running on Cloud Run: It should work automatically (Cloud Run has access to Cloud SQL)

---

## Migration Options

### Option 1: Manual SQL Migration (Simplest)

Run SQL commands directly to add the new columns. This is what I'll create for you.

**Pros:**
- Simple, straightforward
- No additional dependencies
- Full control

**Cons:**
- Manual process
- No version tracking
- Need to remember what was added

### Option 2: Alembic (Production-Ready)

Use Alembic for version-controlled migrations.

**Pros:**
- Version tracking
- Can rollback changes
- Industry standard
- Tracks migration history

**Cons:**
- More setup
- Additional dependency
- Learning curve

---

## What Fields Need to Be Added

### `trips` table:
- `current_lat` (FLOAT, nullable)
- `current_lng` (FLOAT, nullable)
- `last_location_update` (TIMESTAMP, nullable)
- `trip_date` (DATE, nullable)
- `created_at` (TIMESTAMP, default now)
- `updated_at` (TIMESTAMP, nullable)

### `ride_requests` table:
- `departure_time` (VARCHAR, nullable) - **IMPORTANT: This was missing!**
- `request_date` (DATE, nullable)
- `matched_trip_id` (INTEGER, nullable, FK to trips.id)
- `suggested_hub_id` (VARCHAR, nullable)
- `created_at` (TIMESTAMP, default now)
- `updated_at` (TIMESTAMP, nullable)

---

## Safety Notes

1. **Backup First**: Always backup your database before migrations
2. **Test on Dev**: Test migrations on a development database first
3. **Nullable Fields**: All new fields are nullable, so existing data won't break
4. **No Data Loss**: This migration only ADDS columns, doesn't delete anything

---

## Next Steps

I'll create a migration script that you can run. It will:
1. Check if columns already exist (safe to run multiple times)
2. Add missing columns
3. Set up foreign key constraints
4. Add default values where needed
