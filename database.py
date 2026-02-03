import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Cloud SQL Unix socket: only works inside GCP (Cloud Run) or with Auth Proxy.
# For local runs (create_test_data, scripts): set DATABASE_URL to a TCP connection.
#
# Option 1 – Cloud SQL Auth Proxy (TCP):
#   cloud_sql_proxy -instances=skipool-483602:us-central1:skipooldb=tcp:5432
#   export DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@127.0.0.1:5432/skipooldb"
#
# Option 2 – Public IP (if enabled on instance):
#   export DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@YOUR_PUBLIC_IP:5432/skipooldb"
#
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:SkiPoolTest_1@/skipooldb?host=/cloudsql/skipool-483602:us-central1:skipooldb",
)

# Add connection timeout and pool settings for better reliability
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "connect_timeout": 30,
        "options": "-c statement_timeout=60000",
    },
    pool_pre_ping=True,
    pool_recycle=3600,
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