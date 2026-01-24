# Migration Deployment Options

You have two options for deploying the migration job, depending on whether you have Docker running locally.

## Option 1: Cloud Build (No Local Docker Required) ✅ RECOMMENDED

This uses Google Cloud Build to build the image, so you don't need Docker Desktop running locally.

```bash
./deploy-migration-cloudbuild.sh
```

**What it does:**
1. Uses `gcloud builds submit` to build the Docker image in the cloud
2. Deploys the Cloud Run job
3. No local Docker required!

## Option 2: Local Docker Build

This requires Docker Desktop to be running on your machine.

```bash
# First, start Docker Desktop, then:
./deploy-migration-job.sh
```

**What it does:**
1. Builds Docker image locally
2. Pushes to Google Container Registry
3. Deploys the Cloud Run job

## Option 3: Manual gcloud Commands

If you prefer to run commands manually:

```bash
# Build and push image using Cloud Build
gcloud builds submit \
  --tag gcr.io/skipool-483602/skipool-migration:latest \
  --dockerfile=Dockerfile.migration \
  --project=skipool-483602

# Deploy the job
gcloud run jobs deploy skipool-migration \
  --image=gcr.io/skipool-483602/skipool-migration:latest \
  --region=us-central1 \
  --set-cloudsql-instances=skipool-483602:us-central1:skipooldb \
  --max-retries=1 \
  --task-timeout=300 \
  --memory=512Mi \
  --cpu=1 \
  --project=skipool-483602

# Execute the migration
gcloud run jobs execute skipool-migration \
  --region=us-central1 \
  --project=skipool-483602
```

## Why the Error Occurred

The original `deploy-migration-job.sh` script uses:
- `docker build` - requires local Docker daemon
- `docker push` - requires local Docker daemon

But you're using `gcloud run deploy --source .` which uses Cloud Build instead. The new `deploy-migration-cloudbuild.sh` script matches your workflow by using Cloud Build.

## Recommendation

Since you're already using Cloud Build for your main app deployment, use **Option 1** (`deploy-migration-cloudbuild.sh`) - it's consistent with your existing workflow and doesn't require Docker Desktop.
