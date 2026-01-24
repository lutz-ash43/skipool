#!/bin/bash
# Script to deploy the migration job to Cloud Run
# Usage: ./deploy-migration-job.sh

set -e

PROJECT_ID="skipool-483602"
REGION="us-central1"
JOB_NAME="skipool-migration"
IMAGE_NAME="gcr.io/${PROJECT_ID}/skipool-migration:latest"
CLOUDSQL_INSTANCE="skipool-483602:us-central1:skipooldb"

echo "🚀 Deploying SkiPool Migration Job to Cloud Run"
echo "================================================"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Job Name: ${JOB_NAME}"
echo ""

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t ${IMAGE_NAME} -f Dockerfile.migration .

# Push the image to Google Container Registry
echo "📤 Pushing image to GCR..."
docker push ${IMAGE_NAME}

# Deploy as Cloud Run Job
echo "🚀 Deploying Cloud Run Job..."
gcloud run jobs deploy ${JOB_NAME} \
  --image=${IMAGE_NAME} \
  --region=${REGION} \
  --set-cloudsql-instances=${CLOUDSQL_INSTANCE} \
  --max-retries=1 \
  --task-timeout=300 \
  --memory=512Mi \
  --cpu=1 \
  --project=${PROJECT_ID}

echo ""
echo "✅ Migration job deployed successfully!"
echo ""
echo "To run the migration, execute:"
echo "  gcloud run jobs execute ${JOB_NAME} --region=${REGION} --project=${PROJECT_ID}"
echo ""
echo "To view logs:"
echo "  gcloud run jobs executions list --job=${JOB_NAME} --region=${REGION} --project=${PROJECT_ID}"
