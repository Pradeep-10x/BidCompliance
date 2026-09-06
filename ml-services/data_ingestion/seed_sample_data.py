import logging
from db.connection import get_db_connection, init_db
from ml3_reasoning.debarment import CPCL_OFFICIAL_DEBARMENT_RECORDS, normalize_name

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_data")

SAMPLE_MCA_VENDORS = [
    ("U29100TN2015PTC101234", "CHENNAI VALVES & PIPING PRIVATE LIMITED", "U29100TN2015PTC101234", "ROC Chennai", "Active", "2015-04-12", "Plot 45, Manali Industrial Estate, Chennai 600068"),
    ("U28112DL2018PTC334567", "RADIANT HITECH ENG PVT LTD", "U28112DL2018PTC334567", "ROC Delhi", "Active", "2018-06-20", "Industrial Area, Okhla Phase II, New Delhi 110020"),
    ("U74999TN2020PTC139876", "FANIBHUSAN INFRATECH PRIVATE LIMITED", "U74999TN2020PTC139876", "ROC Chennai", "Active", "2020-01-15", "Old Mahabalipuram Road, Chennai 600096"),
    ("U29299GJ2012PTC071234", "TRIPLE OFFSET VALVE MFG CO LTD", "U29299GJ2012PTC071234", "ROC Ahmedabad", "Active", "2012-09-08", "GIDC Phase IV, Vatva, Ahmedabad 382445"),
]

SAMPLE_MSME_VENDORS = [
    ("UDYAM-TN-02-0012345", "CHENNAI VALVES & PIPING PRIVATE LIMITED", "Small", "Manufacturing", "28", "2812", "Tamil Nadu", "Chennai"),
    ("UDYAM-GJ-01-0098765", "TRIPLE OFFSET VALVE MFG CO LTD", "Medium", "Manufacturing", "28", "2812", "Gujarat", "Ahmedabad"),
    ("UDYAM-TN-02-0044556", "SRI BALAJI ENTERPRISES", "Micro", "Trading", "46", "4659", "Tamil Nadu", "Chennai"),
]


def seed():
    init_db()
    conn, engine_type = get_db_connection()
    cursor = conn.cursor()
    logger.info("Seeding initial sample data into %s...", engine_type)

    # 1. Seed Debarment records from CPCL portal
    for r in CPCL_OFFICIAL_DEBARMENT_RECORDS:
        norm = normalize_name(r["bidder_name"])
        if engine_type == "postgresql":
            cursor.execute("""
                INSERT INTO cpcl_debarment_records (bidder_name, normalized_name, pan_masked, login_id, organisation_chain, start_date, end_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
            """, (r["bidder_name"], norm, r["pan_masked"], r["login_id"], r["organisation_chain"], r["start_date"], r["end_date"]))
        else:
            cursor.execute("""
                INSERT OR IGNORE INTO cpcl_debarment_records (bidder_name, normalized_name, pan_masked, login_id, organisation_chain, start_date, end_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (r["bidder_name"], norm, r["pan_masked"], r["login_id"], r["organisation_chain"], r["start_date"], r["end_date"]))

    # 2. Seed MCA Sample Vendors
    for cin, name, reg_no, roc, status, d_inc, addr in SAMPLE_MCA_VENDORS:
        norm = normalize_name(name)
        if engine_type == "postgresql":
            cursor.execute("""
                INSERT INTO mca_companies (cin, company_name, normalized_name, roc_code, company_status, date_of_incorporation, registered_address)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (cin) DO NOTHING;
            """, (cin, name, norm, roc, status, d_inc, addr))
        else:
            cursor.execute("""
                INSERT OR IGNORE INTO mca_companies (cin, company_name, normalized_name, roc_code, company_status, date_of_incorporation, registered_address)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (cin, name, norm, roc, status, d_inc, addr))

    # 3. Seed MSME Sample Vendors
    for udyam, name, etype, activity, n2, n4, state, dist in SAMPLE_MSME_VENDORS:
        norm = normalize_name(name)
        if engine_type == "postgresql":
            cursor.execute("""
                INSERT INTO msme_enterprises (udyam_registration_number, enterprise_name, normalized_name, enterprise_type, major_activity, nic_2digit_code, nic_4digit_code, state, district)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (udyam_registration_number) DO NOTHING;
            """, (udyam, name, norm, etype, activity, n2, n4, state, dist))
        else:
            cursor.execute("""
                INSERT OR IGNORE INTO msme_enterprises (udyam_registration_number, enterprise_name, normalized_name, enterprise_type, major_activity, nic_2digit_code, nic_4digit_code, state, district)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (udyam, name, norm, etype, activity, n2, n4, state, dist))

    conn.commit()
    conn.close()
    logger.info("Database seeding completed successfully.")


if __name__ == "__main__":
    seed()
