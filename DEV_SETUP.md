# SkiPool Development Setup

This guide will help you set up your local development environment for SkiPool.

## Quick Start (Recommended for Daily Development)

1. **Make sure Docker Desktop is running**
   
2. **Start local development**:
   ```bash
   ./dev.sh local
   ```
   
   This will:
   - ✓ Start PostgreSQL in Docker (5 seconds)
   - ✓ Run database migrations automatically
   - ✓ Start FastAPI with hot reload on `http://localhost:8080`

3. **Code and test** - Changes auto-reload!

4. **When done**:
   ```bash
   ./dev.sh stop
   ```

## Why Local Development?

Your Cloud SQL instance (`db-custom-2-8192`) costs ~$0.15/hour when running and takes 1-3 minutes to start from stopped. Local PostgreSQL:

- ✓ **Fast**: Starts in ~5 seconds
- ✓ **Free**: No GCP charges
- ✓ **Offline**: Works without internet
- ✓ **Low latency**: Sub-millisecond queries

## Cloud SQL Testing (Pre-Deployment)

When you need to test against the production database:

1. **Create `.env` file** (first time only):
   ```bash
   cp .env.example .env
   ```
   
2. **Add your Cloud SQL password** in `.env`:
   ```
   DB_PASSWORD=your_cloud_sql_password
   ```

3. **Start cloud mode**:
   ```bash
   ./dev.sh cloud
   ```
   
   This will:
   - Start the Cloud SQL instance (if stopped)
   - Wait for it to become ready (~1-3 minutes)
   - Start Cloud SQL Auth Proxy
   - Run migrations
   - Start FastAPI

⚠️ **Note**: Cloud SQL incurs costs (~$0.15/hour) while running.

## Available Commands

```bash
./dev.sh local      # Start local PostgreSQL + FastAPI (recommended)
./dev.sh cloud      # Start Cloud SQL + proxy + FastAPI (testing)
./dev.sh stop       # Stop everything (asks about stopping Cloud SQL)
./dev.sh migrate    # Run migrations against active database
./dev.sh deploy     # Deploy to Cloud Run
```

## Database Information

### Local Development
- **Host**: localhost
- **Port**: 5432
- **Database**: skipooldb
- **User**: postgres
- **Password**: localdev
- **Connection**: `postgresql://postgres:localdev@127.0.0.1:5432/skipooldb`

### Cloud SQL (via Proxy)
- **Host**: localhost (via proxy)
- **Port**: 5433
- **Database**: skipooldb
- **User**: postgres
- **Password**: (from your `.env` file)
- **Instance**: `skipool-483602:us-central1:skipooldb`

## Workflow Examples

### Daily Development
```bash
./dev.sh local
# Code, test, repeat...
./dev.sh stop
```

### Pre-Deployment Testing
```bash
./dev.sh cloud
# Test against production database
./dev.sh deploy
./dev.sh stop
```

### Database Migrations
```bash
# Start either local or cloud environment first
./dev.sh local

# In another terminal, run migrations
./dev.sh migrate
```

## Troubleshooting

### "Docker is not running"
- Start Docker Desktop and try again

### "Cloud SQL Auth Proxy is not installed"
```bash
gcloud components install cloud-sql-proxy
# or download from: https://cloud.google.com/sql/docs/mysql/sql-proxy
```

### "Database connection failed"
- **Local mode**: Make sure Docker is running
- **Cloud mode**: Check that `.env` has the correct `DB_PASSWORD`

### Port already in use
```bash
# Kill any processes using port 5432 (local) or 5433 (cloud)
lsof -ti:5432 | xargs kill -9
lsof -ti:5433 | xargs kill -9
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     LOCAL DEVELOPMENT                       │
│  FastAPI (8080) → PostgreSQL Docker (5432)                  │
│  Fast, Free, Offline                                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   CLOUD SQL TESTING                         │
│  FastAPI (8080) → Auth Proxy (5433) → Cloud SQL            │
│  Production-like, Costs Money                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      PRODUCTION                             │
│  Cloud Run → Cloud SQL Connector → Cloud SQL                │
│  Deployed with ./dev.sh deploy                              │
└─────────────────────────────────────────────────────────────┘
```

## Security Note

The dev.sh deploy command will check if your Cloud SQL instance has `authorizedNetworks: 0.0.0.0/0` (open to the entire internet) and offer to fix it. Cloud SQL should only be accessible via:
- Cloud SQL Auth Proxy (local development)
- Cloud SQL Python Connector (Cloud Run production)

No public IP access needed!
