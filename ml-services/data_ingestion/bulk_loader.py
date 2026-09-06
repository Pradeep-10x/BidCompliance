import csv
import sys
import logging
import argparse
from pathlib import Path
from db.connection import get_db_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bulk_loader")


def normalize_string(val: str) -> str:
    """Uppercase, remove corporate suffixes, strip non-alphanumeric."""
    if not val:
        return ""
    v = val.upper()
    for term in ["PRIVATE LIMITED", "PVT LTD", "PVT. LTD.", "LIMITED", "LTD", "ENTERPRISES", "INC"]:
        v = v.replace(term, "")
    import re
    return re.sub(r"[^A-Z0-9]", "", v).strip()


def stream_ingest_mca(csv_path: str, chunk_size: int = 10000):
    """Streams large MCA Master Data CSV into database with low memory footprint."""
    path = Path(csv_path)
    if not path.exists():
        logger.error("File not found: %s", csv_path)
        return

    conn, engine_type = get_db_connection()
    cursor = conn.cursor()
    logger.info("Starting MCA streaming ingestion from %s into %s", path.name, engine_type)

    total = 0
    batch = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cin = row.get("CIN") or row.get("cin") or row.get("Corporate_Identification_Number")
            name = row.get("COMPANY_NAME") or row.get("company_name") or row.get("Company_Name")
            if not cin or not name:
                continue

            norm_name = normalize_string(name)
            status = row.get("COMPANY_STATUS") or row.get("company_status") or "Active"
            roc = row.get("ROC") or row.get("roc_code")
            reg_date = row.get("DATE_OF_INCORPORATION") or row.get("date_of_incorporation")
            address = row.get("REGISTERED_OFFICE_ADDRESS") or row.get("registered_address")

            batch.append((cin.strip(), name.strip(), norm_name, roc, status, reg_date, address))

            if len(batch) >= chunk_size:
                _insert_mca_batch(cursor, batch, engine_type)
                conn.commit()
                total += len(batch)
                logger.info("Ingested %d MCA records...", total)
                batch = []

        if batch:
            _insert_mca_batch(cursor, batch, engine_type)
            conn.commit()
            total += len(batch)

    conn.close()
    logger.info("Successfully ingested %d MCA companies into %s.", total, engine_type)


def _insert_mca_batch(cursor, batch, engine_type):
    if engine_type == "postgresql":
        query = """
            INSERT INTO mca_companies (cin, company_name, normalized_name, roc_code, company_status, date_of_incorporation, registered_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (cin) DO UPDATE SET
                company_name = EXCLUDED.company_name,
                normalized_name = EXCLUDED.normalized_name,
                company_status = EXCLUDED.company_status;
        """
        cursor.executemany(query, batch)
    else:
        query = """
            INSERT OR REPLACE INTO mca_companies (cin, company_name, normalized_name, roc_code, company_status, date_of_incorporation, registered_address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        cursor.executemany(query, batch)


def stream_ingest_msme(csv_path: str, chunk_size: int = 10000):
    """Streams large Udyam/MSME CSV into database with low memory footprint."""
    path = Path(csv_path)
    if not path.exists():
        logger.error("File not found: %s", csv_path)
        return

    conn, engine_type = get_db_connection()
    cursor = conn.cursor()
    logger.info("Starting MSME streaming ingestion from %s into %s", path.name, engine_type)

    total = 0
    batch = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            udyam = row.get("UDYAM_REGISTRATION_NUMBER") or row.get("udyam_registration_number") or row.get("Udyam_No")
            name = row.get("ENTERPRISE_NAME") or row.get("enterprise_name")
            if not udyam or not name:
                continue

            norm_name = normalize_string(name)
            etype = row.get("ENTERPRISE_TYPE") or row.get("enterprise_type") or "Micro"
            activity = row.get("MAJOR_ACTIVITY") or row.get("major_activity") or "Manufacturing"
            nic2 = row.get("NIC_2_DIGIT") or row.get("nic_2digit_code")
            nic4 = row.get("NIC_4_DIGIT") or row.get("nic_4digit_code")
            state = row.get("STATE") or row.get("state")
            dist = row.get("DISTRICT") or row.get("district")

            batch.append((udyam.strip(), name.strip(), norm_name, etype, activity, nic2, nic4, state, dist))

            if len(batch) >= chunk_size:
                _insert_msme_batch(cursor, batch, engine_type)
                conn.commit()
                total += len(batch)
                logger.info("Ingested %d MSME records...", total)
                batch = []

        if batch:
            _insert_msme_batch(cursor, batch, engine_type)
            conn.commit()
            total += len(batch)

    conn.close()
    logger.info("Successfully ingested %d MSME enterprises into %s.", total, engine_type)


def _insert_msme_batch(cursor, batch, engine_type):
    if engine_type == "postgresql":
        query = """
            INSERT INTO msme_enterprises (udyam_registration_number, enterprise_name, normalized_name, enterprise_type, major_activity, nic_2digit_code, nic_4digit_code, state, district)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (udyam_registration_number) DO UPDATE SET
                enterprise_name = EXCLUDED.enterprise_name,
                normalized_name = EXCLUDED.normalized_name,
                enterprise_type = EXCLUDED.enterprise_type,
                major_activity = EXCLUDED.major_activity;
        """
        cursor.executemany(query, batch)
    else:
        query = """
            INSERT OR REPLACE INTO msme_enterprises (udyam_registration_number, enterprise_name, normalized_name, enterprise_type, major_activity, nic_2digit_code, nic_4digit_code, state, district)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.executemany(query, batch)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Streaming Bulk Ingestion for Large MCA & MSME Datasets")
    parser.add_argument("--type", choices=["mca", "msme"], required=True, help="Dataset type: mca or msme")
    parser.add_argument("--file", required=True, help="Path to raw CSV file on local disk")
    args = parser.parse_args()

    if args.type == "mca":
        stream_ingest_mca(args.file)
    elif args.type == "msme":
        stream_ingest_msme(args.file)
