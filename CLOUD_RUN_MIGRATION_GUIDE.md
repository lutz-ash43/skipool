# Cloud Run Migration Job Guide

This guide explains how to deploy and run the database migration as a Cloud Run job.

## Overview

The migration is packaged as a Cloud Run Job that:
- Connects to your Cloud SQL database using the Unix socket (automatic on Cloud Run)
- Adds new columns to existing tables
- Is idempotent (safe to run multiple times)
- Preserves all existing data

## Prerequisites

1. **Google Cloud SDK (gcloud)** installed and configured
2. **Docker** installed (for building the image)
3. **Permissions** to:
   - Build and push images to Google Container Registry
   - Deploy Cloud Run jobs
   - Access Cloud SQL instance

## Quick Start

### Option 1: Using the Deployment Script (Easiest)

```bash
# Make script executable
chmod +x deploy-migration-job.sh

# Deploy the job
./deploy-migration-job.sh

# Run the migration
gcloud run jobs execute skipool-migration --region=us-central1 --project=skipool-483602
```

### Option 2: Manual Deployment

#### Step 1: Build and Push Docker Image

```bash
# Set variables
PROJECT_ID="skipool-483602"
IMAGE_NAME="gcr.io/${PROJECT_ID}/skipool-migration:latest"

# Build the image
docker build -t ${IMAGE_NAME} -f Dockerfile.migration .

# Push to Google Container Registry
docker push ${IMAGE_NAME}
```

#### Step 2: Deploy Cloud Run Job

```bash
gcloud run jobs deploy skipool-migration \
  --image=gcr.io/skipool-483602/skipool-migration:latest \
  --region=us-central1 \
  --set-cloudsql-instances=skipool-483602:us-central1:skipooldb \
  --max-retries=1 \
  --task-timeout=300 \
  --memory=512Mi \
  --cpu=1 \
  --project=skipool-483602
```

#### Step 3: Execute the Migration

```bash
gcloud run jobs execute skipool-migration \
  --region=us-central1 \
  --project=skipool-483602
```

## Option 3: Using Cloud Build (CI/CD)

If you want to automate the deployment:

```bash
gcloud builds submit --config=cloudbuild-migration.yaml
```

This will:
1. Build the Docker image
2. Push it to GCR
3. Deploy the Cloud Run job

**Note:** You'll need to update the service account in `cloudbuild-migration.yaml` first.

## Monitoring the Migration

### View Job Execution Status

```bash
gcloud run jobs executions list \
  --job=skipool-migration \
  --region=us-central1 \
  --project=skipool-483602
```

### View Logs

```bash
# Get the latest execution name
EXECUTION=$(gcloud run jobs executions list \
  --job=skipool-migration \
  --region=us-central1 \
  --project=skipool-483602 \
  --limit=1 \
  --format="value(name)")

# View logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=skipool-migration" \
  --limit=50 \
  --project=skipool-483602
```

Or view in the Cloud Console:
- Go to Cloud Run → Jobs → skipool-migration → Executions → View Logs

## What Gets Migrated

### `trips` Table
- `current_lat` (FLOAT, nullable)
- `current_lng` (FLOAT, nullable)
- `last_location_update` (TIMESTAMP, nullable)
- `trip_date` (DATE, nullable)
- `created_at` (TIMESTAMP, default now)
- `updated_at` (TIMESTAMP, nullable)

### `ride_requests` Table
- `departure_time` (VARCHAR, nullable) - **This was missing!**
- `request_date` (DATE, nullable)
- `matched_trip_id` (INTEGER, nullable, FK)
- `suggested_hub_id` (VARCHAR, nullable)
- `created_at` (TIMESTAMP, default now)
- `updated_at` (TIMESTAMP, nullable)

## Safety Features

1. **Idempotent**: Safe to run multiple times - checks if columns exist before adding
2. **Non-destructive**: Only adds columns, never deletes data
3. **Nullable fields**: All new columns are nullable, so existing rows get NULL values
4. **Transaction-based**: Uses database transactions - if something fails, all changes are rolled back

## Troubleshooting

### Error: Permission Denied

Ensure your service account has:
- `cloudsql.client` role on the Cloud SQL instance
- `run.jobs.create` and `run.jobs.execute` permissions

### Error: Cannot Connect to Database

- Verify Cloud SQL instance is running
- Check that `--set-cloudsql-instances` matches your instance connection name
- Ensure the connection name format is correct: `PROJECT_ID:REGION:INSTANCE_NAME`

### Error: Image Not Found

- Ensure Docker image was pushed successfully
- Check that you're using the correct project ID
- Verify image exists: `gcloud container images list --repository=gcr.io/skipool-483602`

### View Detailed Error Messages

```bash
# Get execution details
gcloud run jobs executions describe EXECUTION_NAME \
  --region=us-central1 \
  --project=skipool-483602
```

## Cleanup

After successful migration, you can optionally delete the job:

```bash
gcloud run jobs delete skipool-migration \
  --region=us-central1 \
  --project=skipool-483602
```

Or keep it for future migrations (it's idempotent, so safe to keep).

## Verification

After migration, verify the columns were added:

```bash
# Connect to your database and run:
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'trips' 
ORDER BY ordinal_position;

SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'ride_requests' 
ORDER BY ordinal_position;
```

## Next Steps

After successful migration:
1. ✅ Test your API endpoints
2. ✅ Verify mobile app can connect
3. ✅ Test creating trips and ride requests
4. ✅ Test scheduled ride matching

---

**Need Help?** Check the logs or verify your Cloud SQL instance is accessible from Cloud Run.
