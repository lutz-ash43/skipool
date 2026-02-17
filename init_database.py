"""
Initialize Database Schema for SkiPool

This script creates the base database tables from the SQLAlchemy models.
Run this on a fresh database before running migrations.

Usage:
    python init_database.py
"""

from database import engine, Base, get_connection_string, IS_CLOUD_RUN
from models import Trip, RideRequest
from sqlalchemy import inspect, text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def table_exists(connection, table_name):
    """Check if a table exists in the database"""
    inspector = inspect(connection)
    return table_name in inspector.get_table_names()

def init_database():
    """Initialize database schema"""
    print("🗄️  Initializing SkiPool Database Schema")
    print("=" * 60)
    
    if IS_CLOUD_RUN:
        print("📡 Cloud Run environment - connecting via Cloud SQL Connector")
    else:
        connection_string = get_connection_string()
        if connection_string:
            # Hide password for security
            safe_connection = connection_string.split('@')[-1] if '@' in connection_string else "local database"
            print(f"📡 Connecting to database: {safe_connection}")
    
    try:
        # Check connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.scalar()
            print("✅ Database connection successful")
            
            # Check if tables already exist
            tables_exist = []
            tables_to_create = []
            
            for table_name in ['trips', 'ride_requests']:
                if table_exists(connection, table_name):
                    tables_exist.append(table_name)
                else:
                    tables_to_create.append(table_name)
            
            if tables_exist:
                print(f"\n📋 Existing tables found: {', '.join(tables_exist)}")
            
            if tables_to_create:
                print(f"\n🔨 Creating tables: {', '.join(tables_to_create)}")
            elif not tables_to_create and tables_exist:
                print(f"\n✅ All tables already exist. Nothing to create.")
                return
        
        # Create all tables (this is idempotent - won't recreate existing tables)
        print("\n🚀 Creating database schema...")
        Base.metadata.create_all(bind=engine)
        
        # Verify tables were created
        with engine.connect() as connection:
            inspector = inspect(connection)
            created_tables = inspector.get_table_names()
            
            print("\n✅ Database initialization complete!")
            print(f"\n📋 Available tables: {', '.join(created_tables)}")
            
            # Show column info for each table
            for table_name in created_tables:
                columns = inspector.get_columns(table_name)
                print(f"\n  {table_name}:")
                for col in columns:
                    col_type = str(col['type'])
                    nullable = "NULL" if col['nullable'] else "NOT NULL"
                    print(f"    - {col['name']}: {col_type} {nullable}")
        
        print("\n" + "=" * 60)
        print("🎉 Database is ready for use!")
        print("\nNext steps:")
        print("  1. Run migrations if needed: ./dev.sh migrate")
        print("  2. Create test data: python create_test_data.py")
        print("  3. Start the app: uvicorn main:app --reload")
        
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    init_database()
