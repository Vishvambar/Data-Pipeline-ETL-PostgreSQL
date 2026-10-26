"""
Configuration Module for PostgreSQL ETL Data Pipeline.
Manages database connection URLs, logging configuration, and pipeline constants.
"""

import os
import getpass
import logging
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

# Database credentials
DB_NAME = os.getenv("PGDATABASE", "pipeline_db")
DB_USER = os.getenv("PGUSER", os.getenv("USER", getpass.getuser()))
DB_PASSWORD = os.getenv("PGPASSWORD", "")
DB_HOST = os.getenv("PGHOST", "")
DB_PORT = os.getenv("PGPORT", "5432")

# Pipeline target settings
DEFAULT_TARGET_TABLE = "students_cleaned"


def get_db_url() -> str:
    """
    Constructs an SQLAlchemy-compatible PostgreSQL connection URL.
    Supports Unix domain socket (peer authentication) and TCP host connections.
    """
    encoded_user = quote_plus(DB_USER)
    
    if DB_HOST:
        encoded_pass = f":{quote_plus(DB_PASSWORD)}" if DB_PASSWORD else ""
        return f"postgresql+psycopg2://{encoded_user}{encoded_pass}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        # Local Unix domain socket connection (standard Linux / Fedora peer auth)
        return f"postgresql+psycopg2://{encoded_user}@/{DB_NAME}"


def get_engine() -> Engine:
    """Creates and returns an SQLAlchemy Engine."""
    url = get_db_url()
    return create_engine(url, pool_pre_ping=True)


def setup_logger(name: str = "ETL_Pipeline") -> logging.Logger:
    """
    Configures and returns a standardized logger with timestamp and level formatting.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid adding duplicate handlers if already configured
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger
