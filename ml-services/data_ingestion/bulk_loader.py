import csv
import json
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
    for term in [
        "PRIVATE LIMITED", "PVT LTD", "PVT. LTD.", "PVT.LTD.",
        "LIMITED", "LTD.", "LTD", "ENTERPRISES", "ENTERPRISE", "INC", "LLP"
    ]:
        v = v.replace(term, "")
    import re
    return re.sub(r"[^A-Z0-9]", "", v).strip()


def stream_ingest_mca(csv_path: str, chunk_size: int = 10000):
    """Streams the official MCA Master Data CSV into database with low memory footprint."""
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
            cin = row.get("CIN") or row.get("cin")
            name = row.get("CompanyName") or row.get("company_name") or row.get("COMPANY_NAME")
            if not cin or not name:
                continue

            norm_name = normalize_string(name)
            roc = row.get("CompanyROCcode") or row.get("ROC") or ""
            cat = row.get("CompanyCategory") or ""
            cclass = row.get("CompanyClass") or ""
            status = row.get("CompanyStatus") or row.get("company_status") or "Active"
            reg_date = row.get("CompanyRegistrationdate_date") or row.get("DATE_OF_INCORPORATION") or None
            addr = row.get("Registered_Office_Address") or row.get("REGISTERED_OFFICE_ADDRESS") or ""
            auth_cap = None
            paid_cap = None
            try:
                auth_cap = float(row.get("AuthorizedCapital") or 0.0)
                paid_cap = float(row.get("PaidupCapital") or 0.0)
            except (ValueError, TypeError):
                pass

            batch.append((
                cin.strip(), name.strip(), norm_name, roc, cat, cclass,
                reg_date, auth_cap, paid_cap, status, addr
            ))

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
            INSERT INTO mca_companies (
                cin, company_name, normalized_name, roc_code, company_category,
                class_of_company, date_of_incorporation, authorized_capital,
                paidup_capital, company_status, registered_address
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (cin) DO UPDATE SET
                company_name = EXCLUDED.company_name,
                normalized_name = EXCLUDED.normalized_name,
                company_status = EXCLUDED.company_status;
        """
        cursor.executemany(query, batch)
    else:
        query = """
            INSERT OR REPLACE INTO mca_companies (
                cin, company_name, normalized_name, roc_code, company_category,
                class_of_company, date_of_incorporation, authorized_capital,
                paidup_capital, company_status, registered_address
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.executemany(query, batch)


def stream_ingest_msme(csv_path: str, chunk_size: int = 10000):
    """Streams the official MSME Registered Enterprises CSV into database."""
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
        for row_idx, row in enumerate(reader):
            name = row.get("EnterpriseName") or row.get("enterprise_name")
            if not name:
                continue

            norm_name = normalize_string(name)
            state = row.get("State") or ""
            dist = row.get("District") or ""
            pincode = row.get("Pincode") or ""
            reg_date = row.get("RegistrationDate") or None
            
            # Parse Activities JSON
            activities_raw = row.get("Activities") or ""
            nic_code = ""
            desc = ""
            major_activity = "Services"
            if activities_raw:
                try:
                    acts = json.loads(activities_raw)
                    if isinstance(acts, list) and len(acts) > 0:
                        first_act = acts[0]
                        nic_code = str(first_act.get("NIC5DigitId", ""))
                        desc = str(first_act.get("Description", ""))
                        # NIC 2-digit classifications in India:
                        # 10 to 33 = Manufacturing
                        # 45 to 47 = Retail/Wholesale (Trading)
                        # Others = Services
                        if nic_code:
                            nic2 = nic_code[:2]
                            try:
                                n2_int = int(nic2)
                                if 10 <= n2_int <= 33:
                                    major_activity = "Manufacturing"
                                elif 45 <= n2_int <= 47:
                                    major_activity = "Trading"
                                else:
                                    major_activity = "Services"
                            except ValueError:
                                if "manufactur" in desc.lower():
                                    major_activity = "Manufacturing"
                                elif "retail" in desc.lower() or "wholesale" in desc.lower():
                                    major_activity = "Trading"
                except Exception:
                    pass

            # Synthetic or fallback identifier if udyam number not present
            udyam_id = f"UDYAM-{state[:2].upper()}-{dist[:2].upper()}-{row_idx:07d}"

            batch.append((
                udyam_id, name.strip(), norm_name, "Micro",
                major_activity, nic_code[:2], nic_code, state, dist
            ))

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
            INSERT INTO msme_enterprises (
                udyam_registration_number, enterprise_name, normalized_name, enterprise_type,
                major_activity, nic_2digit_code, nic_4digit_code, state, district
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (udyam_registration_number) DO UPDATE SET
                enterprise_name = EXCLUDED.enterprise_name,
                normalized_name = EXCLUDED.normalized_name,
                major_activity = EXCLUDED.major_activity;
        """
        cursor.executemany(query, batch)
    else:
        query = """
            INSERT OR REPLACE INTO msme_enterprises (
                udyam_registration_number, enterprise_name, normalized_name, enterprise_type,
                major_activity, nic_2digit_code, nic_4digit_code, state, district
            )
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
