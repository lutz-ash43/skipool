"""
Schema Verification Script

This script verifies that all columns required by the application code
actually exist in the database. It compares the models.py definitions
with what's actually in the database.
"""

from sqlalchemy import inspect, text
from database import engine
from models import Trip, RideRequest

def verify_schema():
    """Verify database schema matches models"""
    print("=" * 70)
    print("Database Schema Verification")
    print("=" * 70)
    
    inspector = inspect(engine)
    
    # Expected columns from models.py
    expected_trips = {
        'id': 'INTEGER (PK)',
        'driver_name': 'VARCHAR',
        'resort': 'VARCHAR',
        'start_location_text': 'VARCHAR',
        'start_lat': 'FLOAT (nullable)',
        'start_lng': 'FLOAT (nullable)',
        'current_lat': 'FLOAT (nullable)',
        'current_lng': 'FLOAT (nullable)',
        'last_location_update': 'TIMESTAMP (nullable)',
        'departure_time': 'VARCHAR',
        'available_seats': 'INTEGER',
        'is_realtime': 'BOOLEAN',
        'trip_date': 'DATE (nullable)',
        'created_at': 'TIMESTAMP',
        'updated_at': 'TIMESTAMP (nullable)'
    }
    
    expected_ride_requests = {
        'id': 'INTEGER (PK)',
        'passenger_name': 'VARCHAR',
        'resort': 'VARCHAR',
        'pickup_lat': 'FLOAT',
        'pickup_lng': 'FLOAT',
        'pickup_address': 'VARCHAR',
        'departure_time': 'VARCHAR',
        'status': 'VARCHAR',
        'request_date': 'DATE (nullable)',
        'matched_trip_id': 'INTEGER (nullable, FK)',
        'suggested_hub_id': 'VARCHAR (nullable)',
        'created_at': 'TIMESTAMP',
        'updated_at': 'TIMESTAMP (nullable)'
    }
    
    all_good = True
    
    # Check trips table
    print("\n📋 Checking 'trips' table...")
    print("-" * 70)
    
    if 'trips' not in inspector.get_table_names():
        print("❌ ERROR: 'trips' table does not exist!")
        all_good = False
    else:
        actual_columns = {col['name']: col['type'] for col in inspector.get_columns('trips')}
        
        for col_name, col_desc in expected_trips.items():
            if col_name in actual_columns:
                print(f"  ✅ {col_name:30s} - {col_desc}")
            else:
                print(f"  ❌ {col_name:30s} - MISSING! ({col_desc})")
                all_good = False
        
        # Check for unexpected columns
        unexpected = set(actual_columns.keys()) - set(expected_trips.keys())
        if unexpected:
            print(f"\n  ⚠️  Unexpected columns (not in model): {', '.join(unexpected)}")
    
    # Check ride_requests table
    print("\n📋 Checking 'ride_requests' table...")
    print("-" * 70)
    
    if 'ride_requests' not in inspector.get_table_names():
        print("❌ ERROR: 'ride_requests' table does not exist!")
        all_good = False
    else:
        actual_columns = {col['name']: col['type'] for col in inspector.get_columns('ride_requests')}
        
        for col_name, col_desc in expected_ride_requests.items():
            if col_name in actual_columns:
                print(f"  ✅ {col_name:30s} - {col_desc}")
            else:
                print(f"  ❌ {col_name:30s} - MISSING! ({col_desc})")
                all_good = False
        
        # Check for unexpected columns
        unexpected = set(actual_columns.keys()) - set(expected_ride_requests.keys())
        if unexpected:
            print(f"\n  ⚠️  Unexpected columns (not in model): {', '.join(unexpected)}")
    
    # Check foreign key constraint
    print("\n🔗 Checking foreign key constraints...")
    print("-" * 70)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.table_constraints 
                WHERE constraint_name = 'ride_requests_matched_trip_id_fkey'
                AND table_name = 'ride_requests'
            """))
            fk_exists = result.scalar() > 0
            
            if fk_exists:
                print("  ✅ Foreign key constraint 'ride_requests_matched_trip_id_fkey' exists")
            else:
                print("  ⚠️  Foreign key constraint 'ride_requests_matched_trip_id_fkey' missing (optional)")
    except Exception as e:
        print(f"  ⚠️  Could not check foreign key: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    if all_good:
        print("✅ Schema verification PASSED - All required columns exist!")
        print("   Your database schema matches the application models.")
    else:
        print("❌ Schema verification FAILED - Missing columns detected!")
        print("   Run the migration script to add missing columns.")
    print("=" * 70)
    
    return all_good

if __name__ == "__main__":
    try:
        verify_schema()
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        print("\n💡 Make sure:")
        print("   1. Database is running and accessible")
        print("   2. Connection string is correct")
        print("   3. You have proper permissions")
