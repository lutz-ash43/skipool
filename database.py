from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Replace with your actual GCP credentials
# Format: postgresql://[USER]:[PASSWORD]@[PUBLIC_IP]/[DB_NAME]
# SQLALCHEMY_DATABASE_URL = "postgresql://postgres:N44}57p+~}?uB;1Z@34.60.29.140:5432/skipooldb"
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:SkiPoolTest_1@/skipooldb?host=/cloudsql/skipool-483602:us-central1:skipooldb"

# Add connection timeout and pool settings for better reliability
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "connect_timeout": 30,  # 30 second connection timeout
        "options": "-c statement_timeout=60000"  # 60 second statement timeout
    },
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to use in main.py
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()