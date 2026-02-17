"""
Database configuration with Cloud SQL Python Connector and retry logic.

This module provides robust database connectivity for both local development
(via Cloud SQL Auth Proxy) and production (Cloud Run with Cloud SQL Connector).

Environment Variables:
    Local Development (with Cloud SQL Auth Proxy):
        - DATABASE_URL: Full connection string (e.g., postgresql://postgres:password@127.0.0.1:5432/skipooldb)
        OR
        - DB_USER, DB_PASSWORD, DB_NAME: Individual connection parameters
    
    Cloud Run (production):
        - INSTANCE_CONNECTION_NAME: Cloud SQL instance (e.g., project:region:instance)
        - DB_USER, DB_PASSWORD, DB_NAME: Database credentials
"""

import os
import time
import logging
from typing import Optional
from sqlalchemy import create_engine, text, pool
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file (local development)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Detect environment
IS_CLOUD_RUN = os.getenv("K_SERVICE") is not None

# Database configuration
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "skipooldb")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME", "skipool-483602:us-central1:skipooldb")

# Connection retry settings
MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]  # Exponential backoff: 2s, 4s, 8s


def get_connection_string() -> str:
    """Get the database connection string based on environment."""
    # Check for explicit DATABASE_URL first (local development)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        logger.info("Using DATABASE_URL from environment")
        return database_url
    
    # Require password if not using DATABASE_URL
    if not DB_PASSWORD:
        raise ValueError(
            "Database password not configured. Set either:\n"
            "  - DATABASE_URL environment variable, OR\n"
            "  - DB_PASSWORD environment variable\n"
            "For local development, copy .env.example to .env and fill in your password."
        )
    
    # Cloud Run: use Cloud SQL Python Connector (handled separately)
    if IS_CLOUD_RUN:
        logger.info("Cloud Run environment detected - will use Cloud SQL Python Connector")
        return None
    
    # Local development: use TCP connection to Cloud SQL Auth Proxy
    connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@127.0.0.1:5432/{DB_NAME}"
    logger.info("Local development: using TCP connection to Cloud SQL Auth Proxy")
    return connection_string


def create_cloud_sql_engine():
    """Create SQLAlchemy engine using Cloud SQL Python Connector (for Cloud Run)."""
    try:
        from google.cloud.sql.connector import Connector
        import pg8000
        
        logger.info(f"Initializing Cloud SQL Connector for {INSTANCE_CONNECTION_NAME}")
        
        connector = Connector()
        
        def getconn():
            """Create a connection to Cloud SQL using the connector."""
            conn = connector.connect(
                INSTANCE_CONNECTION_NAME,
                "pg8000",
                user=DB_USER,
                password=DB_PASSWORD,
                db=DB_NAME,
            )
            return conn
        
        # Use NullPool for serverless (Cloud Run instances are ephemeral)
        engine = create_engine(
            "postgresql+pg8000://",
            creator=getconn,
            poolclass=pool.NullPool,
            connect_args={
                "connect_timeout": 30,
            },
        )
        
        logger.info("Cloud SQL Connector engine created successfully")
        return engine
        
    except ImportError as e:
        logger.error(f"Cloud SQL Connector not available: {e}")
        logger.error("Install with: pip install cloud-sql-python-connector[pg8000]")
        raise


def create_local_engine(connection_string: str):
    """Create SQLAlchemy engine for local development (via Cloud SQL Auth Proxy)."""
    # Small pool for local development with aggressive recycling
    engine = create_engine(
        connection_string,
        connect_args={
            "connect_timeout": 30,
            "options": "-c statement_timeout=60000",
        },
        pool_size=2,
        max_overflow=0,
        pool_pre_ping=True,
        pool_recycle=300,  # 5 minutes (aggressive for development)
    )
    
    logger.info("Local development engine created successfully")
    return engine


def create_engine_with_retry():
    """Create database engine with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            if IS_CLOUD_RUN:
                return create_cloud_sql_engine()
            else:
                connection_string = get_connection_string()
                return create_local_engine(connection_string)
                
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.warning(
                    f"Failed to create database engine (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                )
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"Failed to create database engine after {MAX_RETRIES} attempts")
                raise


def verify_connection(engine) -> bool:
    """Verify database connection with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                result.scalar()
                logger.info("Database connection verified successfully")
                return True
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.warning(
                    f"Database connection failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                )
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"Database connection failed after {MAX_RETRIES} attempts: {e}")
                if not IS_CLOUD_RUN:
                    logger.error(
                        "\nLocal development troubleshooting:\n"
                        "  1. Ensure Cloud SQL Auth Proxy is running:\n"
                        "     cloud_sql_proxy -instances=skipool-483602:us-central1:skipooldb=tcp:5432\n"
                        "  2. Verify .env file exists with correct DATABASE_URL or DB_PASSWORD\n"
                        "  3. Check that the Cloud SQL instance is running in GCP"
                    )
                raise
    
    return False


# Create engine with retry logic
logger.info("Initializing database connection...")
engine = create_engine_with_retry()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base using modern SQLAlchemy 2.0 syntax
class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Dependency to use in FastAPI endpoints
def get_db():
    """FastAPI dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()