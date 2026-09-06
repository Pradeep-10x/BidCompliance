import os
import sqlite3
import logging
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger("ml_services.db")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/bidcompliance"
)

LOCAL_SQLITE_PATH = Path(__file__).resolve().parent.parent / "data" / "bidcompliance_local.db"


def get_db_connection():
    """Attempts PostgreSQL connection; falls back gracefully to local SQLite.
    
    This ensures that testing, local evaluation, and offline demonstrations
    always succeed even if the PostgreSQL daemon is not yet started.
    """
    LOCAL_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Try PostgreSQL if psycopg2 or psycopg is installed
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        return conn, "postgresql"
    except Exception as pg_err:
        logger.debug("PostgreSQL not accessible (%s). Using local SQLite fallback.", pg_err)

    # Fallback: SQLite
    conn = sqlite3.connect(str(LOCAL_SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    return conn, "sqlite"


def init_db():
    """Initializes tables in either PostgreSQL or SQLite."""
    conn, engine_type = get_db_connection()
    cursor = conn.cursor()
    
    if engine_type == "postgresql":
        schema_path = Path(__file__).resolve().parent / "schema.sql"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                cursor.execute(f.read())
            conn.commit()
            logger.info("Initialized PostgreSQL schema.")
    else:
        # SQLite equivalent tables
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS mca_companies (
                cin TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                normalized_name TEXT,
                roc_code TEXT,
                registration_number TEXT,
                company_category TEXT,
                class_of_company TEXT,
                date_of_incorporation TEXT,
                authorized_capital REAL,
                paidup_capital REAL,
                company_status TEXT DEFAULT 'Active',
                registered_address TEXT,
                email TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS msme_enterprises (
                udyam_registration_number TEXT PRIMARY KEY,
                enterprise_name TEXT NOT NULL,
                normalized_name TEXT,
                enterprise_type TEXT,
                major_activity TEXT,
                nic_2digit_code TEXT,
                nic_4digit_code TEXT,
                state TEXT,
                district TEXT,
                date_of_registration TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS cpcl_debarment_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bidder_name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                pan_masked TEXT,
                pan_full TEXT,
                login_id TEXT,
                organisation_chain TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                active_status INTEGER DEFAULT 1,
                source_reference TEXT DEFAULT 'CPCL e-Procurement Portal',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS bid_evaluations (
                bid_id TEXT PRIMARY KEY,
                tender_number TEXT,
                bidder_name TEXT,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                classification_summary TEXT,
                extracted_fields TEXT,
                contradictions TEXT,
                statutory_verifications TEXT,
                recommendation_status TEXT,
                recommendation_narrative TEXT
            );

            CREATE TABLE IF NOT EXISTS officer_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bid_id TEXT,
                officer_id TEXT NOT NULL,
                officer_name TEXT,
                decision TEXT NOT NULL,
                reason_narrative TEXT NOT NULL,
                ip_address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        logger.info("Initialized local SQLite fallback schema.")
    
    conn.close()
