#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="skipool-483602"
REGION="us-central1"
INSTANCE_NAME="skipooldb"
CLOUD_SQL_INSTANCE="$PROJECT_ID:$REGION:$INSTANCE_NAME"
CLOUD_SQL_PROXY_PORT=5433

# Local DB connection
LOCAL_DATABASE_URL="postgresql://postgres:localdev@127.0.0.1:5432/skipooldb"

# Cloud DB connection (via proxy)
CLOUD_DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@127.0.0.1:$CLOUD_SQL_PROXY_PORT/skipooldb"

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}→ $1${NC}"
}

wait_for_postgres_docker() {
    local container_name=$1
    local max_attempts=30
    local attempt=1

    print_info "Waiting for PostgreSQL to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        # Check Docker container health status
        health_status=$(docker inspect --format='{{.State.Health.Status}}' $container_name 2>/dev/null || echo "unknown")
        if [ "$health_status" = "healthy" ]; then
            print_success "PostgreSQL is ready!"
            return 0
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done
    
    print_error "PostgreSQL failed to start within 30 seconds"
    print_info "Check logs with: docker logs $container_name"
    return 1
}

wait_for_postgres_tcp() {
    local host=$1
    local port=$2
    local max_attempts=30
    local attempt=1

    print_info "Waiting for PostgreSQL to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        # Try to connect using nc (netcat) or docker exec
        if command -v nc &> /dev/null; then
            if nc -z $host $port 2>/dev/null; then
                print_success "PostgreSQL is ready!"
                return 0
            fi
        elif command -v pg_isready &> /dev/null; then
            if pg_isready -h $host -p $port -q 2>/dev/null; then
                print_success "PostgreSQL is ready!"
                return 0
            fi
        else
            # Fallback: just wait a bit and assume it's ready
            if [ $attempt -ge 10 ]; then
                print_success "PostgreSQL should be ready"
                return 0
            fi
        fi
        echo -n "."
        sleep 1
        ((attempt++))
    done
    
    print_error "PostgreSQL failed to start within 30 seconds"
    return 1
}

start_local() {
    print_header "Starting Local Development Environment"
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
    
    # Start Docker Compose
    print_info "Starting local PostgreSQL container..."
    docker compose up -d
    
    # Wait for PostgreSQL to be ready using Docker healthcheck
    if ! wait_for_postgres_docker skipool-postgres; then
        print_error "Failed to start PostgreSQL"
        exit 1
    fi
    
    # Export DATABASE_URL for this session
    export DATABASE_URL="$LOCAL_DATABASE_URL"
    
    # Initialize database schema (creates tables if they don't exist)
    print_info "Initializing database schema..."
    python3 init_database.py
    
    # Run migrations (adds new columns to existing tables)
    print_info "Running database migrations..."
    python3 migrate_database.py --yes
    
    print_success "Local development environment ready!"
    echo ""
    echo -e "${GREEN}Database URL: $LOCAL_DATABASE_URL${NC}"
    echo -e "${GREEN}API will be available at: http://localhost:8080${NC}"
    echo ""
    
    # Free port 8080 if something is already using it (e.g. previous run)
    if lsof -i :8080 -sTCP:LISTEN -t 2>/dev/null | grep -q .; then
        print_warning "Port 8080 is in use. Freeing it..."
        lsof -i :8080 -sTCP:LISTEN -t 2>/dev/null | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
    
    # Start the application
    print_info "Starting FastAPI application..."
    DATABASE_URL="$LOCAL_DATABASE_URL" uvicorn main:app --reload --port 8080
}

start_cloud() {
    print_header "Starting Cloud SQL Development Environment"
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Cloud SQL Auth Proxy is installed
    if ! command -v cloud-sql-proxy &> /dev/null && ! command -v cloud_sql_proxy &> /dev/null; then
        print_error "Cloud SQL Auth Proxy is not installed."
        print_info "Install it with: gcloud components install cloud-sql-proxy"
        print_info "Or download from: https://cloud.google.com/sql/docs/mysql/sql-proxy"
        exit 1
    fi
    
    # Check Cloud SQL instance status
    print_info "Checking Cloud SQL instance status..."
    INSTANCE_STATUS=$(gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID --format="value(state)" 2>/dev/null || echo "NOT_FOUND")
    
    if [ "$INSTANCE_STATUS" = "NOT_FOUND" ]; then
        print_error "Cloud SQL instance not found: $INSTANCE_NAME"
        exit 1
    fi
    
    if [ "$INSTANCE_STATUS" != "RUNNABLE" ]; then
        print_warning "Cloud SQL instance is $INSTANCE_STATUS. Starting instance..."
        gcloud sql instances patch $INSTANCE_NAME --activation-policy=ALWAYS --project=$PROJECT_ID
        
        print_info "Waiting for instance to become RUNNABLE (this may take 1-3 minutes)..."
        max_wait=180  # 3 minutes
        elapsed=0
        while [ $elapsed -lt $max_wait ]; do
            INSTANCE_STATUS=$(gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID --format="value(state)")
            if [ "$INSTANCE_STATUS" = "RUNNABLE" ]; then
                break
            fi
            echo -n "."
            sleep 10
            ((elapsed+=10))
        done
        
        if [ "$INSTANCE_STATUS" != "RUNNABLE" ]; then
            print_error "Instance did not start within 3 minutes"
            exit 1
        fi
    fi
    
    print_success "Cloud SQL instance is RUNNABLE"
    
    # Start Cloud SQL Auth Proxy
    print_info "Starting Cloud SQL Auth Proxy on port $CLOUD_SQL_PROXY_PORT..."
    
    # Kill any existing proxy processes
    pkill -f "cloud[-_]sql[-_]proxy.*$INSTANCE_NAME" 2>/dev/null || true
    
    # Start proxy in background
    if command -v cloud-sql-proxy &> /dev/null; then
        cloud-sql-proxy --port=$CLOUD_SQL_PROXY_PORT $CLOUD_SQL_INSTANCE &
    else
        cloud_sql_proxy -instances=$CLOUD_SQL_INSTANCE=tcp:$CLOUD_SQL_PROXY_PORT &
    fi
    
    PROXY_PID=$!
    echo $PROXY_PID > .cloud_sql_proxy.pid
    
    # Wait for proxy to be ready
    sleep 3
    
    if ! ps -p $PROXY_PID > /dev/null; then
        print_error "Cloud SQL Auth Proxy failed to start"
        exit 1
    fi
    
    print_success "Cloud SQL Auth Proxy running (PID: $PROXY_PID)"
    
    # Check if we have the password in .env
    if [ -f .env ]; then
        source .env
        if [ ! -z "$DB_PASSWORD" ]; then
            CLOUD_DATABASE_URL="postgresql://postgres:$DB_PASSWORD@127.0.0.1:$CLOUD_SQL_PROXY_PORT/skipooldb"
        fi
    fi
    
    # Wait for connection to be ready
    if ! wait_for_postgres_tcp localhost $CLOUD_SQL_PROXY_PORT; then
        print_error "Failed to connect to Cloud SQL via proxy"
        kill $PROXY_PID 2>/dev/null || true
        exit 1
    fi
    
    # Export DATABASE_URL for this session
    export DATABASE_URL="$CLOUD_DATABASE_URL"
    
    # Initialize database schema (creates tables if they don't exist)
    print_info "Initializing database schema..."
    python3 init_database.py
    
    # Run migrations (adds new columns to existing tables)
    print_info "Running database migrations..."
    python3 migrate_database.py --yes
    
    print_success "Cloud SQL development environment ready!"
    echo ""
    print_warning "Using Cloud SQL: This will incur costs (~\$0.15/hour when running)"
    echo -e "${GREEN}Database URL: postgresql://postgres:****@127.0.0.1:$CLOUD_SQL_PROXY_PORT/skipooldb${NC}"
    echo -e "${GREEN}API will be available at: http://localhost:8080${NC}"
    echo ""
    
    # Free port 8080 if something is already using it
    if lsof -i :8080 -sTCP:LISTEN -t 2>/dev/null | grep -q .; then
        print_warning "Port 8080 is in use. Freeing it..."
        lsof -i :8080 -sTCP:LISTEN -t 2>/dev/null | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
    
    # Cleanup function to kill proxy on exit
    cleanup() {
        print_info "Stopping Cloud SQL Auth Proxy..."
        kill $PROXY_PID 2>/dev/null || true
        rm -f .cloud_sql_proxy.pid
    }
    trap cleanup EXIT
    
    # Start the application
    print_info "Starting FastAPI application..."
    DATABASE_URL="$CLOUD_DATABASE_URL" uvicorn main:app --reload --port 8080
}

stop_env() {
    print_header "Stopping Development Environment"
    
    # Stop local Docker containers
    if docker compose ps -q 2>/dev/null | grep -q .; then
        print_info "Stopping local PostgreSQL container..."
        docker compose down
        print_success "Local PostgreSQL stopped"
    fi
    
    # Stop Cloud SQL Auth Proxy
    if [ -f .cloud_sql_proxy.pid ]; then
        PROXY_PID=$(cat .cloud_sql_proxy.pid)
        if ps -p $PROXY_PID > /dev/null 2>&1; then
            print_info "Stopping Cloud SQL Auth Proxy..."
            kill $PROXY_PID 2>/dev/null || true
            rm -f .cloud_sql_proxy.pid
            print_success "Cloud SQL Auth Proxy stopped"
        fi
    fi
    
    # Kill any remaining proxy processes
    pkill -f "cloud[-_]sql[-_]proxy.*$INSTANCE_NAME" 2>/dev/null && print_success "Cleaned up proxy processes" || true
    
    # Ask about stopping Cloud SQL instance
    echo ""
    print_info "Stop Cloud SQL instance to save costs? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_info "Stopping Cloud SQL instance..."
        gcloud sql instances patch $INSTANCE_NAME --activation-policy=NEVER --project=$PROJECT_ID
        print_success "Cloud SQL instance stopped (will take a moment to fully stop)"
        print_info "Note: The instance will start automatically when needed"
    fi
    
    print_success "Development environment stopped"
}

run_migrations() {
    print_header "Running Database Migrations"
    
    # Check which environment is running
    if docker compose ps -q 2>/dev/null | grep -q .; then
        print_info "Detected local PostgreSQL environment"
        export DATABASE_URL="$LOCAL_DATABASE_URL"
    elif [ -f .cloud_sql_proxy.pid ]; then
        print_info "Detected Cloud SQL environment"
        if [ -f .env ]; then
            source .env
            if [ ! -z "$DB_PASSWORD" ]; then
                export DATABASE_URL="postgresql://postgres:$DB_PASSWORD@127.0.0.1:$CLOUD_SQL_PROXY_PORT/skipooldb"
            fi
        fi
    else
        print_error "No database environment is running"
        print_info "Start with: ./dev.sh local  OR  ./dev.sh cloud"
        exit 1
    fi
    
    # Initialize schema first
    print_info "Initializing database schema..."
    python3 init_database.py
    
    # Then run migrations
    print_info "Running database migrations..."
    python3 migrate_database.py --yes
    print_success "Database is up to date"
}

deploy_to_cloud_run() {
    print_header "Deploying to Cloud Run"
    
    print_warning "Security check: Verifying Cloud SQL authorized networks..."
    
    # Check if the instance has open network access
    AUTHORIZED_NETWORKS=$(gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID --format="value(settings.ipConfiguration.authorizedNetworks[].value)" 2>/dev/null || echo "")
    
    if echo "$AUTHORIZED_NETWORKS" | grep -q "0.0.0.0/0"; then
        print_warning "WARNING: Cloud SQL instance is open to the entire internet (0.0.0.0/0)"
        print_info "This is a security risk. Lock it down? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            print_info "Removing public access..."
            gcloud sql instances patch $INSTANCE_NAME \
                --clear-authorized-networks \
                --project=$PROJECT_ID
            print_success "Authorized networks cleared. Cloud SQL now only accessible via Cloud SQL Connector."
        fi
    fi
    
    print_info "Deploying to Cloud Run..."
    gcloud run deploy skidb-backend \
        --source . \
        --region=$REGION \
        --project=$PROJECT_ID \
        --allow-unauthenticated \
        --set-env-vars="INSTANCE_CONNECTION_NAME=$CLOUD_SQL_INSTANCE,DB_USER=postgres,DB_NAME=skipooldb" \
        --add-cloudsql-instances=$CLOUD_SQL_INSTANCE
    
    print_success "Deployment complete!"
    
    # Get the URL
    SERVICE_URL=$(gcloud run services describe skidb-backend --region=$REGION --project=$PROJECT_ID --format="value(status.url)")
    echo ""
    echo -e "${GREEN}Service URL: $SERVICE_URL${NC}"
}

run_tests() {
    print_header "Running End-to-End Tests"
    
    # Auto-detect which environment is running
    BASE_URL="http://localhost:8080"
    
    # Check if API is reachable
    print_info "Checking API at $BASE_URL..."
    if ! curl -s -f "$BASE_URL/health" > /dev/null 2>&1; then
        print_error "API is not reachable at $BASE_URL"
        print_info "Make sure the API is running with: ./dev.sh local  OR  ./dev.sh cloud"
        exit 1
    fi
    
    print_success "API is reachable"
    
    # Run the test script
    print_info "Running test suite..."
    python3 test_flows.py --base-url "$BASE_URL"
    
    TEST_EXIT_CODE=$?
    
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        print_success "All tests passed!"
        print_info "Test report written to test_report.md"
    else
        print_error "Some tests failed"
        print_info "Check test_report.md for details"
    fi
    
    exit $TEST_EXIT_CODE
}

sim_ride() {
    print_header "Ride Now Simulation Setup"
    
    RESORT="${1:-solitude}"
    DRIVER_NAME="${2:-Sim Driver}"
    INTERVAL="${3:-10}"
    BASE_URL="http://localhost:8080"
    
    # Check if API is running
    if ! curl -s -f "$BASE_URL/health" > /dev/null 2>&1; then
        print_error "API is not reachable at $BASE_URL"
        print_info "Start the API first: ./dev.sh local"
        exit 1
    fi
    
    # Run simulation setup (hybrid: manual driver post, automated route)
    python3 sim_ride.py --mode now --resort "$RESORT" --driver-name "$DRIVER_NAME" --interval "$INTERVAL" --base-url "$BASE_URL"
}

sim_sched() {
    print_header "Scheduled Ride Simulation Setup"
    
    RESORT="${1:-solitude}"
    PERSPECTIVE="${2:-driver}"
    INTERVAL="${3:-10}"
    BASE_URL="http://localhost:8080"
    
    # Check if API is running
    if ! curl -s -f "$BASE_URL/health" > /dev/null 2>&1; then
        print_error "API is not reachable at $BASE_URL"
        print_info "Start the API first: ./dev.sh local"
        exit 1
    fi
    
    # Run simulation setup (fully automated for driver perspective)
    python3 sim_ride.py --mode scheduled --resort "$RESORT" --perspective "$PERSPECTIVE" --base-url "$BASE_URL" --interval "$INTERVAL"
}

show_usage() {
    echo "SkiPool Development Script"
    echo ""
    echo "Usage: ./dev.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  local      Start local PostgreSQL + FastAPI (daily development)"
    echo "  cloud      Start Cloud SQL + proxy + FastAPI (pre-deploy testing)"
    echo "  stop       Stop local DB and/or Cloud SQL instance"
    echo "  migrate    Run database migrations against active environment"
    echo "  test       Run end-to-end tests against running API"
    echo "  sim-ride   Hybrid Ride Now simulation [resort] [driver-name] [interval]"
    echo "  sim-sched  Hybrid Scheduled simulation [resort] [driver|passenger] [interval]"
    echo "  deploy     Deploy to Cloud Run"
    echo ""
    echo "Examples:"
    echo "  ./dev.sh local                          # Fast local development"
    echo "  ./dev.sh cloud                          # Test against production database"
    echo "  ./dev.sh test                           # Run full test suite (needs API running)"
    echo "  ./dev.sh sim-ride solitude              # Hybrid Ride Now (default 'Sim Driver')"
    echo "  ./dev.sh sim-ride solitude \"Ashley\"     # Custom driver name"
    echo "  ./dev.sh sim-ride solitude \"Ashley\" 5   # Custom name + 5s intervals"
    echo "  ./dev.sh sim-sched solitude driver      # Hybrid scheduled ride as driver"
    echo "  ./dev.sh sim-sched solitude passenger   # Scheduled ride as passenger"
    echo "  ./dev.sh deploy                         # Deploy to production"
}

# Main command router
case "${1:-}" in
    local)
        start_local
        ;;
    cloud)
        start_cloud
        ;;
    stop)
        stop_env
        ;;
    migrate)
        run_migrations
        ;;
    test)
        run_tests
        ;;
    sim-ride)
        sim_ride "${2:-solitude}" "$3" "$4"
        ;;
    sim-sched)
        sim_sched "${2:-solitude}" "${3:-driver}" "$4"
        ;;
    deploy)
        deploy_to_cloud_run
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
