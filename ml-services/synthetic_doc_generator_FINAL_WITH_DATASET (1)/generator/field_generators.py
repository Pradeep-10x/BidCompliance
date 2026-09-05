from datetime import date, timedelta
from faker import Faker
import random

fake = Faker("en_IN")

COMPANY_SUFFIXES = ["Demo Labs", "Synthetic Systems", "Fictional Devices", "Sample Enterprises", "Test Works"]
PRODUCTS = ["Smart Watch", "LED Lamp", "Pressure Cooker", "Mobile Charger", "Desk Fan"]
PRODUCT_CATEGORIES = ["Consumer Electronics", "Home Appliances", "Lighting Products", "Small Devices"]
CONSTITUTIONS = ["Private Limited", "Partnership", "Proprietorship", "Limited Liability Partnership"]
STATES = ["Sample State", "Demo Pradesh", "Test Karnataka", "Fictional Maharashtra"]
CITIES = ["Sample City", "Demo Nagar", "Testpur", "Example Town"]


def fake_person_name() -> str:
    return f"Synthetic Person {random.randint(100, 999)}"


def fake_company_name() -> str:
    return f"{random.choice(COMPANY_SUFFIXES)} {random.randint(10,99)}"


def fake_address() -> str:
    number = random.randint(1, 99)
    return f"{number} Demo Industrial Road, {random.choice(CITIES)}, {random.choice(STATES)}"


def fake_city() -> str:
    return random.choice(CITIES)


def fake_state() -> str:
    return random.choice(STATES)


def fake_pin() -> str:
    return f"SYN-PIN-{random.randint(1,999999):06d}"


def fake_email() -> str:
    return f"demo{random.randint(1,999999):06d}@example.invalid"


def fake_mobile() -> str:
    return f"SYN-MOBILE-{random.randint(1,999999):06d}"


def fake_date(start_year=2021, end_year=2026) -> str:
    return fake.date_between(date(start_year,1,1), date(end_year,12,31)).isoformat()


def later_date(base: str, days: int) -> str:
    return (date.fromisoformat(base) + timedelta(days=days)).isoformat()


def random_bool() -> bool:
    return bool(random.getrandbits(1))
