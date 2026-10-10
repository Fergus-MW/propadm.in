"""Typed source records using the current platform's actual field names."""

import random

AS_OF = "2026-10-10T12:00:00Z"
TRADES = ["plumbing", "heating/gas", "electrical", "appliance repair", "locksmith", "damp/mould",
          "carpentry", "gardening", "cleaning", "roofing", "drainage", "general building"]
DISTRICTS = [("E1", "London"), ("N1", "London"), ("SE1", "London"), ("SW1A", "London"),
             ("M1", "Manchester"), ("B1", "Birmingham"), ("LS1", "Leeds"), ("BS1", "Bristol")]
FIRST = ["Sam", "Aisha", "Daniel", "Priya", "Morgan", "Leila", "Noah", "Amara", "Oliver", "Mei",
         "Ravi", "Sofia", "Alex", "Zara", "Leo", "Imani", "Hannah", "Omar", "Jules", "Niamh"]
LAST = ["Osei", "Khan", "Reed", "Patel", "Taylor", "Morgan", "Chen", "Okafor", "Evans", "Singh",
        "Walsh", "Ahmed", "Brown", "Wilson", "Clarke", "Lewis", "Thomas", "Young", "Hughes", "Ali"]


def record(kind, slug, name, fields, **extra):
    return {"id": f"{kind}:{slug}", "type": kind, "name": name, "fields": fields, **extra}


def person(number, role):
    offset = {"tenant": 0, "landlord": 7, "contractor": 13}[role]
    name = f"{FIRST[(number + offset) % len(FIRST)]} {LAST[((number // 20) + offset) % len(LAST)]}"
    # Name collisions across distinct emails are intentional identity stress data.
    return record("person", f"{role}-{number:04}", name,
                  {"roles": [role], "emails": [f"{role}.{number:04}@portfolio.example.test"],
                   "preferred_contact": "email"},
                  external_ids={"synthetic_crm": f"{role.upper()}-{number:04}"})


def catalogue(seed=20261010):
    rng = random.Random(seed)
    agency = record("company", "portfolio-agency", "Hawthorn Synthetic Property Services", {
        "type": "managing agent", "emails": ["operations@portfolio.example.test"],
        "domains": ["portfolio.example.test"], "notes": ["Synthetic development portfolio."]})
    landlords = [person(n, "landlord") for n in range(1, 31)]
    providers, contacts, offerings = [], [], []
    for n in range(1, 37):
        trade = TRADES[(n - 1) % len(TRADES)]
        prefix = ["Willow", "Cedar", "Orchard", "Beacon", "Moor", "Elm"][(n - 1) % 6]
        status = "suspended" if n % 17 == 0 else "trial" if n % 7 == 0 else "approved"
        accreditations = []
        if trade in {"heating/gas", "electrical"}:
            accreditations = [{"scheme": "Gas Safe" if trade == "heating/gas" else "NICEIC",
                              "number": f"SYNTHETIC-NOT-VALID-{n:04}",
                              "expires_on": "2026-09-30" if n % 5 == 0 else "2027-09-30"}]
        provider = record("service_provider", f"provider-{n:03}", f"{prefix} {trade.title()} {n:03}", {
            "ref": f"SUP-{n:03}", "trading_name": f"{prefix} {trade.title()} {n:03}",
            "legal_name": f"Synthetic Supplier {n:03}", "business_type": "sole trader",
            "trades": [trade], "emails": [f"bookings.{n:03}@portfolio.example.test"],
            "postcode_districts": [district for district, _ in DISTRICTS],
            "working_hours": "Monday-Friday 08:00-17:00", "emergency_callout": n % 3 != 0,
            "typical_response_hours": rng.choice([2, 4, 12, 24, 48]), "booking_method": "email",
            "accreditations": accreditations, "insurance_public_liability_minor": 500_000_000,
            "insurance_expires_on": "2026-09-01" if n % 11 == 0 else "2027-09-01",
            "status": status, "status_reason": "Synthetic service history",
            "notes": ["All qualifications and company details are fabricated test data."]})
        providers.append(provider)
        contact = person(n, "contractor")
        contacts.append(contact)
        for tier, label in enumerate(["Diagnostic visit", "Standard hourly labour", "Emergency callout"]):
            offerings.append(record("service_offering", f"offering-{n:03}-{tier}",
                f"SUP-{n:03} {label}", {"name": label, "trade": trade,
                 "pricing_model": "hourly" if tier == 1 else "fixed",
                 "price_minor": (65 + n % 8 * 5 + tier * 30) * 100, "vat_included": True,
                 "price_source": "admin", "valid_from": "2026-01-01",
                 "last_confirmed_at": "2026-02-01" if n % 9 == 0 else "2026-10-01"},
                 provider_id=provider["id"]))
    return {"agency": agency, "landlords": landlords, "providers": providers,
            "provider_contacts": contacts, "offerings": offerings}


def property_record(number, seed):
    rng = random.Random(seed + number)
    district, city = DISTRICTS[((number - 1) // 4) % len(DISTRICTS)]
    rent = rng.randrange(90, 241) * 1000
    building = (number - 1) // 4 + 1
    unit = (number - 1) % 4 + 1
    return record("property", f"property-{number:04}", f"SYN-P{number:04} · Flat {unit}, Hawthorn Court {building}", {
        "ref": f"SYN-P{number:04}", "address_line1": f"Flat {unit}, {building} Synthetic Avenue",
        "postcode": f"{district} 1AA", "city": city, "unit_label": f"Flat {unit}",
        "building_name": f"Synthetic Court {building}", "property_type": "flat",
        "bedrooms": 1 + number % 3, "bathrooms": 1, "status": "let",
        "rent_amount_minor": rent, "rent_frequency": "monthly", "rent_due_day": 1,
        "deposit_amount_minor": rent, "management_fee_pct": 10,
        "tenancy_start": "2026-05-01", "tenancy_end": "2027-04-30",
        "access_notes": "Obtain current tenant consent; agency key possession is not consent.",
        "notes": ["Fabricated address for synthetic testing; never dispatch real contractors."]})
