"""
Test Database Connection Script

This script tests the connection to your GCP Cloud SQL database
and verifies basic connectivity before running migrations.

Usage:
    python test_connection.py
"""

from sqlalchemy import text, inspect
from database import engine, get_connection_string, IS_CLOUD_RUN
import sys

def test_connection():
    """Test database connection and basic operations"""
    print("=" * 60)
    print("SkiPool Database Connection Test")
    print("=" * 60)
    
    if IS_CLOUD_RUN:
        print(f"\n📡 Cloud Run environment - connecting via Cloud SQL Connector\n")
    else:
        connection_string = get_connection_string()
        if connection_string and '@' in connection_string:
            print(f"\n📡 Connection String: {connection_string.split('@')[-1]}")
            print("   (Full connection string hidden for security)\n")
        else:
            print(f"\n📡 Connecting via environment configuration\n")
    
    try:
        print("🔄 Attempting to connect...")
        with engine.connect() as connection:
            print("✅ Connection successful!\n")
            
            # Test 1: Check PostgreSQL version
            print("📊 Test 1: Checking PostgreSQL version...")
            try:
                result = connection.execute(text("SELECT version()"))
                version = result.scalar()
                print(f"   ✅ PostgreSQL Version: {version.split(',')[0]}\n")
            except Exception as e:
                print(f"   ⚠️  Could not get version: {e}\n")
            
            # Test 2: Check if tables exist
            print("📊 Test 2: Checking existing tables...")
            try:
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                print(f"   ✅ Found {len(tables)} table(s):")
                for table in tables:
                    print(f"      - {table}")
                
                # Check if our target tables exist
                required_tables = ['trips', 'ride_requests']
                missing_tables = [t for t in required_tables if t not in tables]
                
                if missing_tables:
                    print(f"\n   ⚠️  Missing tables: {', '.join(missing_tables)}")
                    print("      These will be created by Base.metadata.create_all()")
                else:
                    print("\n   ✅ All required tables exist")
                print()
            except Exception as e:
                print(f"   ❌ Error checking tables: {e}\n")
            
            # Test 3: Check current schema of trips table
            print("📊 Test 3: Checking 'trips' table schema...")
            try:
                if 'trips' in tables:
                    columns = inspector.get_columns('trips')
                    print(f"   ✅ 'trips' table has {len(columns)} columns:")
                    for col in columns:
                        nullable = "NULL" if col['nullable'] else "NOT NULL"
                        print(f"      - {col['name']}: {col['type']} ({nullable})")
                    
                    # Check for new columns we need to add
                    existing_cols = [col['name'] for col in columns]
                    needed_cols = ['current_lat', 'current_lng', 'last_location_update', 
                                  'trip_date', 'created_at', 'updated_at']
                    missing_cols = [col for col in needed_cols if col not in existing_cols]
                    
                    if missing_cols:
                        print(f"\n   📝 Missing columns that need to be added: {', '.join(missing_cols)}")
                    else:
                        print("\n   ✅ All new columns already exist!")
                else:
                    print("   ⚠️  'trips' table does not exist yet")
                print()
            except Exception as e:
                print(f"   ❌ Error checking trips schema: {e}\n")
            
            # Test 4: Check current schema of ride_requests table
            print("📊 Test 4: Checking 'ride_requests' table schema...")
            try:
                if 'ride_requests' in tables:
                    columns = inspector.get_columns('ride_requests')
                    print(f"   ✅ 'ride_requests' table has {len(columns)} columns:")
                    for col in columns:
                        nullable = "NULL" if col['nullable'] else "NOT NULL"
                        print(f"      - {col['name']}: {col['type']} ({nullable})")
                    
                    # Check for new columns we need to add
                    existing_cols = [col['name'] for col in columns]
                    needed_cols = ['departure_time', 'request_date', 'matched_trip_id', 
                                  'suggested_hub_id', 'created_at', 'updated_at']
                    missing_cols = [col for col in needed_cols if col not in existing_cols]
                    
                    if missing_cols:
                        print(f"\n   📝 Missing columns that need to be added: {', '.join(missing_cols)}")
                    else:
                        print("\n   ✅ All new columns already exist!")
                else:
                    print("   ⚠️  'ride_requests' table does not exist yet")
                print()
            except Exception as e:
                print(f"   ❌ Error checking ride_requests schema: {e}\n")
            
            # Test 5: Test write operation (if tables exist)
            print("📊 Test 5: Testing write operation...")
            try:
                if 'trips' in tables:
                    # Try a simple SELECT to verify read access
                    result = connection.execute(text("SELECT COUNT(*) FROM trips"))
                    count = result.scalar()
                    print(f"   ✅ Read access confirmed (found {count} row(s) in trips table)")
                else:
                    print("   ⚠️  Cannot test - trips table doesn't exist yet")
                print()
            except Exception as e:
                print(f"   ⚠️  Could not test write operation: {e}\n")
            
            print("=" * 60)
            print("✅ Connection test completed successfully!")
            print("=" * 60)
            print("\n💡 Next steps:")
            if 'trips' in tables or 'ride_requests' in tables:
                print("   1. Review the missing columns listed above")
                print("   2. Run: python migrate_database.py")
            else:
                print("   1. Tables will be created automatically when you start the app")
                print("   2. No migration needed for new tables")
            print()
            
    except Exception as e:
        print("=" * 60)
        print("❌ Connection failed!")
        print("=" * 60)
        print(f"\nError: {e}\n")
        print("💡 Troubleshooting:")
        print("   1. Ensure the database is running in GCP")
        print("   2. If running locally, ensure Cloud SQL Proxy is running:")
        print("      cloud_sql_proxy -instances=skipool-483602:us-central1:skipooldb=tcp:5432")
        print("   3. Check your connection string in database.py")
        print("   4. Verify network access to GCP Cloud SQL")
        print("   5. Check firewall rules allow your IP")
        print("   6. Verify credentials are correct")
        sys.exit(1)

if __name__ == "__main__":
    test_connection()
