#!/bin/bash
# Script to deploy the migration job using Cloud Build (no local Docker required)
# Usage: ./deploy-migration-cloudbuild.sh

set -e

PROJECT_ID="skipool-483602"
REGION="us-central1"
JOB_NAME="skipool-migration"
CLOUDSQL_INSTANCE="skipool-483602:us-central1:skipooldb"

echo "🚀 Deploying SkiPool Migration Job to Cloud Run (using Cloud Build)"
echo "===================================================================="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Job Name: ${JOB_NAME}"
echo ""

# Step 1: Submit build to Cloud Build
echo "📦 Building Docker image with Cloud Build..."
gcloud builds submit . \
  --project=$(gcloud config get-value project) \
  --substitutions=_TAG=gcr.io/$(gcloud config get-value project)/skipool-migration:latest \
  --config <(echo "
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', '\${_TAG}', '-f', 'Dockerfile.migration', '.']
images:
- '\${_TAG}'
")

# Step 2: Deploy as Cloud Run Job
echo ""
echo "🚀 Deploying Cloud Run Job..."
gcloud run jobs deploy ${JOB_NAME} \
  --image=gcr.io/${PROJECT_ID}/skipool-migration:latest \
  --region=${REGION} \
  --set-cloudsql-instances=${CLOUDSQL_INSTANCE} \
  --max-retries=1 \
  --task-timeout=600 \
  --memory=1Gi \
  --cpu=2 \
  --project=${PROJECT_ID}

echo ""
echo "✅ Migration job deployed successfully!"
echo ""
echo "To run the migration, execute:"
echo "  gcloud run jobs execute ${JOB_NAME} --region=${REGION} --project=${PROJECT_ID}"
echo ""
echo "To view logs:"
echo "  gcloud run jobs executions list --job=${JOB_NAME} --region=${REGION} --project=${PROJECT_ID}"
