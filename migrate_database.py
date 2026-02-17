"""
Database Migration Script for SkiPool

This script adds new columns to existing tables in your GCP database.

IMPORTANT:
- The database must be running and accessible
- If running locally, ensure Cloud SQL Proxy is running (or set DATABASE_URL in .env)
- Backup your database before running this script
- This script is idempotent (safe to run multiple times)

Usage:
    python migrate_database.py              # Interactive mode
    python migrate_database.py --yes        # Non-interactive (for Cloud Run)
"""

from sqlalchemy import text, inspect
from database import engine, get_connection_string, IS_CLOUD_RUN
import sys
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def column_exists(connection, table_name, column_name):
    """Check if a column exists in a table - optimized query"""
    # Use direct SQL query instead of inspector for faster execution
    result = connection.execute(text("""
        SELECT COUNT(*) 
        FROM information_schema.columns 
        WHERE table_name = :table_name 
        AND column_name = :column_name
    """), {"table_name": table_name, "column_name": column_name})
    return result.scalar() > 0

def run_migration():
    """Execute database migration"""
    import time
    start_time = time.time()
    print("🚀 Starting database migration...")
    
    if IS_CLOUD_RUN:
        print(f"📡 Cloud Run environment - connecting via Cloud SQL Connector")
    else:
        connection_string = get_connection_string()
        if connection_string:
            # Hide password for security
            safe_connection = connection_string.split('@')[-1] if '@' in connection_string else "local database"
            print(f"📡 Connecting to database: {safe_connection}")
        else:
            print(f"📡 Connecting to database via environment configuration")
    
    try:
        # Set connection timeout
        print("⏱️  Setting connection timeout to 30 seconds...")
        with engine.connect() as connection:
            # Start a transaction
            trans = connection.begin()
            
            try:
                print("\n📋 Checking existing columns...")
                check_start = time.time()
                
                # ===== TRIPS TABLE MIGRATIONS =====
                print("\n🔄 Migrating 'trips' table...")
                
                # Check for ALL model columns (not just new ones)
                # Core columns that might be missing
                if not column_exists(connection, 'trips', 'start_location_text'):
                    print("  ➕ Adding 'start_location_text' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN start_location_text VARCHAR"))
                else:
                    print("  ✓ 'start_location_text' already exists")
                
                if not column_exists(connection, 'trips', 'start_lat'):
                    print("  ➕ Adding 'start_lat' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN start_lat FLOAT"))
                else:
                    print("  ✓ 'start_lat' already exists")
                
                if not column_exists(connection, 'trips', 'start_lng'):
                    print("  ➕ Adding 'start_lng' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN start_lng FLOAT"))
                else:
                    print("  ✓ 'start_lng' already exists")
                
                if not column_exists(connection, 'trips', 'departure_time'):
                    print("  ➕ Adding 'departure_time' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN departure_time VARCHAR(100)"))
                else:
                    print("  ✓ 'departure_time' already exists")
                
                if not column_exists(connection, 'trips', 'available_seats'):
                    print("  ➕ Adding 'available_seats' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN available_seats INTEGER DEFAULT 3"))
                else:
                    print("  ✓ 'available_seats' already exists")
                
                if not column_exists(connection, 'trips', 'is_realtime'):
                    print("  ➕ Adding 'is_realtime' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN is_realtime BOOLEAN DEFAULT FALSE"))
                else:
                    print("  ✓ 'is_realtime' already exists")
                
                # New columns from migration
                if not column_exists(connection, 'trips', 'current_lat'):
                    print("  ➕ Adding 'current_lat' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN current_lat FLOAT"))
                else:
                    print("  ✓ 'current_lat' already exists")
                
                if not column_exists(connection, 'trips', 'current_lng'):
                    print("  ➕ Adding 'current_lng' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN current_lng FLOAT"))
                else:
                    print("  ✓ 'current_lng' already exists")
                
                if not column_exists(connection, 'trips', 'last_location_update'):
                    print("  ➕ Adding 'last_location_update' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN last_location_update TIMESTAMP"))
                else:
                    print("  ✓ 'last_location_update' already exists")
                
                if not column_exists(connection, 'trips', 'trip_date'):
                    print("  ➕ Adding 'trip_date' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN trip_date DATE"))
                else:
                    print("  ✓ 'trip_date' already exists")
                
                if not column_exists(connection, 'trips', 'driver_en_route_at'):
                    print("  ➕ Adding 'driver_en_route_at' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN driver_en_route_at TIMESTAMP"))
                else:
                    print("  ✓ 'driver_en_route_at' already exists")
                
                # Ride lifecycle fields
                if not column_exists(connection, 'trips', 'status'):
                    print("  ➕ Adding 'status' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN status VARCHAR(50) DEFAULT 'pending'"))
                else:
                    print("  ✓ 'status' already exists")
                
                if not column_exists(connection, 'trips', 'picked_up_at'):
                    print("  ➕ Adding 'picked_up_at' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN picked_up_at TIMESTAMP"))
                else:
                    print("  ✓ 'picked_up_at' already exists")
                
                if not column_exists(connection, 'trips', 'completed_at'):
                    print("  ➕ Adding 'completed_at' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN completed_at TIMESTAMP"))
                else:
                    print("  ✓ 'completed_at' already exists")
                
                if not column_exists(connection, 'trips', 'push_token'):
                    print("  ➕ Adding 'push_token' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN push_token VARCHAR"))
                else:
                    print("  ✓ 'push_token' already exists")
                
                if not column_exists(connection, 'trips', 'created_at'):
                    print("  ➕ Adding 'created_at' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                else:
                    print("  ✓ 'created_at' already exists")
                
                if not column_exists(connection, 'trips', 'updated_at'):
                    print("  ➕ Adding 'updated_at' column...")
                    connection.execute(text("ALTER TABLE trips ADD COLUMN updated_at TIMESTAMP"))
                else:
                    print("  ✓ 'updated_at' already exists")
                
                # ===== RIDE_REQUESTS TABLE MIGRATIONS =====
                print("\n🔄 Migrating 'ride_requests' table...")
                
                # Check for ALL model columns (not just new ones)
                # Core columns that might be missing
                if not column_exists(connection, 'ride_requests', 'pickup_lat'):
                    print("  ➕ Adding 'pickup_lat' column...")
                    connection.execute(text("ALTER TABLE ride_requests ADD COLUMN pickup_lat FLOAT"))
                else:
                    print("  ✓ 'pickup_lat' already exists")
                
                if not column_exists(connection, 'ride_requests', 'pickup_lng'):
                    print("  ➕ Adding 'pickup_lng' column...")
                    connection.execute(text("ALTER TABLE ride_requests ADD COLUMN pickup_lng FLOAT"))
                else:
                    print("  ✓ 'pickup_lng' already exists")
                
                if not column_exists(connection, 'ride_requests', 'pickup_address'):
                    print("  ➕ Adding 'pickup_address' column...")
                    connection.execute(text("ALTER TABLE ride_requests ADD COLUMN pickup_address VARCHAR"))
                else:
                    print("  ✓ 'pickup_address' already exists")
                
                if not column_exists(connection, 'ride_requests', 'departure_time'):
                    print("  ➕ Adding 'departure_time' column...")
                    connection.execute(text("ALTER TABLE ride_requests ADD COLUMN departure_time VARCHAR(100)"))
                else:
                    print("  ✓ 'departure_time' already exists")
                
                if not column_exists(connection, 'ride_requests', 'status'):
                    print("  ➕ Adding 'status' column...")
                    connection.execute(text("ALTER TABLE ride_requests ADD COLUMN status VARCHAR(50) DEFAULT 'pending'"))
                else:
                    print("  ✓ 'status' already exists")
                
                if not column_exists(connection, 'ride_requests', 'request_date'):
                    print("  ➕ Adding 'request_date' column...")
                    connection.execute(text("ALTER TABLE ride_requests ADD COLUMN request_date DATE"))
                else:
                    print("  ✓ 'request_date' already exists")
                
                if not column_exists(connection, 'ride_requests', 'matched_trip_id'):
                    print("  ➕ Adding 'matched_trip_id' column...")
                    connection.execute(text("ALTER TABLE ride_requests ADD COLUMN matched_trip_id INTEGER"))
                else:
                    print("  ✓ 'matched_trip_id' already exists")
                
                if not column_exists(connection, 'ride_requests', 'suggested_hub_id'):
                    print("  ➕ Adding 'suggested_hub_id' column...")
                    connection.execute(text("ALTER TABLE ride_requests ADD COLUMN suggested_hub_id VARCHAR(10)"))
                else:
                    print("  ✓ 'suggested_hub_id' already exists")
                
                # Ride lifecycle fields
                if not column_exists(connection, 'ride_requests', 'picked_up_at'):
                    print("  ➕ Adding 'picked_up_at' column...")
                    connection.execute(text("ALTER TABLE ride_requests ADD COLUMN picked_up_at TIMESTAMP"))
                else:
                    print("  ✓ 'picked_up_at' already exists")
                
                if not column_exists(connection, 'ride_requests', 'completed_at'):
                    print("  ➕ Adding 'completed_at' column...")
                    connection.execute(text("ALTER TABLE ride_requests ADD COLUMN completed_at TIMESTAMP"))
                else:
                    print("  ✓ 'completed_at' already exists")
                
                if not column_exists(connection, 'ride_requests', 'push_token'):
                    print("  ➕ Adding 'push_token' column...")
                    connection.execute(text("ALTER TABLE ride_requests ADD COLUMN push_token VARCHAR"))
                else:
                    print("  ✓ 'push_token' already exists")
                
                if not column_exists(connection, 'ride_requests', 'created_at'):
                    print("  ➕ Adding 'created_at' column...")
                    connection.execute(text("ALTER TABLE ride_requests ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                else:
                    print("  ✓ 'created_at' already exists")
                
                if not column_exists(connection, 'ride_requests', 'updated_at'):
                    print("  ➕ Adding 'updated_at' column...")
                    connection.execute(text("ALTER TABLE ride_requests ADD COLUMN updated_at TIMESTAMP"))
                else:
                    print("  ✓ 'updated_at' already exists")
                
                # Real-time location tracking for passengers (Ride Now mode)
                if not column_exists(connection, 'ride_requests', 'current_lat'):
                    print("  ➕ Adding 'current_lat' column...")
                    connection.execute(text("ALTER TABLE ride_requests ADD COLUMN current_lat FLOAT"))
                else:
                    print("  ✓ 'current_lat' already exists")
                
                if not column_exists(connection, 'ride_requests', 'current_lng'):
                    print("  ➕ Adding 'current_lng' column...")
                    connection.execute(text("ALTER TABLE ride_requests ADD COLUMN current_lng FLOAT"))
                else:
                    print("  ✓ 'current_lng' already exists")
                
                if not column_exists(connection, 'ride_requests', 'last_location_update'):
                    print("  ➕ Adding 'last_location_update' column...")
                    connection.execute(text("ALTER TABLE ride_requests ADD COLUMN last_location_update TIMESTAMP"))
                else:
                    print("  ✓ 'last_location_update' already exists")
                
                # Add foreign key constraint if matched_trip_id exists but constraint doesn't
                print("\n🔗 Checking foreign key constraints...")
                try:
                    # Check if FK constraint exists (PostgreSQL specific)
                    result = connection.execute(text("""
                        SELECT COUNT(*) FROM information_schema.table_constraints 
                        WHERE constraint_name = 'ride_requests_matched_trip_id_fkey'
                        AND table_name = 'ride_requests'
                    """))
                    fk_exists = result.scalar() > 0
                    
                    if not fk_exists and column_exists(connection, 'ride_requests', 'matched_trip_id'):
                        print("  ➕ Adding foreign key constraint...")
                        connection.execute(text("""
                            ALTER TABLE ride_requests 
                            ADD CONSTRAINT ride_requests_matched_trip_id_fkey 
                            FOREIGN KEY (matched_trip_id) REFERENCES trips(id)
                        """))
                    else:
                        print("  ✓ Foreign key constraint already exists or column missing")
                except Exception as e:
                    print(f"  ⚠️  Could not add foreign key (may already exist): {e}")
                
                # Commit the transaction
                trans.commit()
                elapsed = time.time() - start_time
                print("\n✅ Migration completed successfully!")
                print(f"⏱️  Total time: {elapsed:.2f} seconds")
                print("\n📊 Summary:")
                print("   - All new columns have been added")
                print("   - Existing data is preserved")
                print("   - New columns are nullable (existing rows have NULL values)")
                
            except Exception as e:
                trans.rollback()
                print(f"\n❌ Migration failed: {e}")
                print("   Transaction rolled back - no changes made")
                sys.exit(1)
                
    except Exception as e:
        print(f"\n❌ Connection error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Ensure the database is running")
        print("   2. If running locally, ensure Cloud SQL Proxy is running")
        print("   3. Check your connection string in database.py")
        print("   4. Verify network access to GCP Cloud SQL")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='SkiPool Database Migration')
    parser.add_argument('--yes', action='store_true', 
                       help='Skip confirmation prompt (for automated runs)')
    args = parser.parse_args()
    
    print("=" * 60)
    print("SkiPool Database Migration")
    print("=" * 60)
    print("\n⚠️  IMPORTANT: Backup your database before running this!")
    print("   This script will add new columns to existing tables.")
    print("   Existing data will be preserved.\n")
    
    if not args.yes:
        response = input("Continue with migration? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Migration cancelled.")
            sys.exit(0)
    else:
        print("Running in non-interactive mode (--yes flag provided)\n")
    
    run_migration()
