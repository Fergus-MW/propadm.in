"""Fixed Addendum A schemas, separate from the original canonical registry."""

TRADES = [
    "plumbing",
    "heating/gas",
    "electrical",
    "roofing",
    "guttering",
    "drainage",
    "carpentry",
    "locksmith",
    "glazing",
    "damp/mould",
    "pest control",
    "appliance repair",
    "decorating",
    "plastering",
    "flooring",
    "cleaning",
    "gardening",
    "handyman",
    "general building",
]
PROVIDER_STATUSES = ["preferred", "approved", "trial", "suspended", "do_not_use"]
TRANSACTION_CATEGORIES = [
    "rent_due",
    "rent_received",
    "tenant_recharge",
    "deposit_received",
    "deposit_deduction",
    "deposit_returned",
    "management_fee",
    "expense",
    "service_charge",
    "ground_rent",
    "utility",
    "council_tax",
    "insurance",
    "compliance",
    "landlord_contribution",
    "landlord_payout",
    "refund",
    "adjustment",
]


def addendum_types(field):
    def optional(kind="string", **kwargs):
        return field(f"option<{kind}>", **kwargs)

    def nonnegative():
        return field("int", minimum=0)

    def money():
        return optional("int", minimum=0)

    def metric(kind="decimal", **kwargs):
        return optional(kind, read_only=True, **kwargs)

    property_fields = {
        "ref": field(unique=True, required=True),
        "address_line1": field(required=True),
        "address_line2": field(),
        "city": field(),
        "postcode": field(required=True),
        "address_text": field("text"),
        "unit_label": optional(),
        "building_name": optional(),
        "property_type": field(
            enum=["house", "flat", "maisonette", "studio", "room", "commercial"]
        ),
        "bedrooms": nonnegative(),
        "bathrooms": nonnegative(),
        "status": field(enum=["let", "vacant", "void_works", "off_market"]),
        "rent_amount_minor": nonnegative(),
        "rent_frequency": field(enum=["weekly", "monthly", "quarterly"]),
        "rent_due_day": field("int", minimum=1, maximum=31),
        "deposit_amount_minor": money(),
        "deposit_scheme_ref": optional(),
        "management_fee_pct": optional("decimal", minimum=0, maximum=100),
        "tenancy_start": optional("date"),
        "tenancy_end": optional("date"),
        "features": field("text"),
        "access_notes": field("text"),
        "compliance_notes": field("text"),
        "notes": field("array<text>"),
        "tenant_balance_minor": field("int", read_only=True),
        "landlord_balance_minor": field("int", read_only=True),
        "deposit_held_minor": field("int", read_only=True),
    }
    provider_fields = {
        "ref": field(unique=True, required=True),
        "trading_name": field(required=True),
        "legal_name": field(),
        "business_type": field(enum=["sole trader", "partnership", "limited company"]),
        "company_number": optional(),
        "vat_number": optional(),
        "trades": field("array<string>", enum=TRADES),
        "description": field("text"),
        "phone_main": optional(unique=True),
        "phone_emergency": optional(unique=True),
        "emails": field("array<string>", unique=True),
        "website": optional(),
        "portal_url": optional(),
        "address": field("text"),
        "service_area": field("text"),
        "postcode_districts": field("array<string>"),
        "working_hours": field("text"),
        "emergency_callout": field("bool"),
        "typical_response_hours": optional("int", minimum=0),
        "booking_method": field(enum=["phone", "email", "portal", "app"]),
        "booking_instructions": field("text"),
        "accreditations": field(
            "array<object>",
            properties={
                "scheme": field(
                    enum=["Gas Safe", "NICEIC", "NAPIT", "TrustMark", "CSCS", "other"],
                    required=True,
                ),
                "number": field(required=True),
                "expires_on": optional("date"),
            },
        ),
        "insurance_public_liability_minor": money(),
        "insurance_expires_on": optional("date"),
        "payment_terms": field("text"),
        "preferred_payment_method": optional(enum=["bank transfer", "card", "cheque"]),
        "status": field(enum=PROVIDER_STATUSES),
        "status_reason": field("text"),
        "notes": field("array<text>"),
        "jobs_completed": field("int", read_only=True, minimum=0),
        "avg_response_hours": metric(minimum=0),
        "first_time_fix_rate": metric(minimum=0, maximum=1),
        "avg_job_cost_minor": metric("int", minimum=0),
        "rating": metric(minimum=1, maximum=5),
    }
    offering_fields = {
        "name": field("text", required=True),
        "trade": field(enum=TRADES),
        "description": field("text"),
        "pricing_model": field(
            enum=["fixed", "hourly", "day rate", "call-out + hourly", "per unit", "quote only"]
        ),
        "price_minor": money(),
        "unit": optional(),
        "callout_fee_minor": money(),
        "hourly_rate_minor": money(),
        "day_rate_minor": money(),
        "min_charge_minor": money(),
        "out_of_hours_multiplier": optional("decimal", minimum=0),
        "vat_included": field("bool"),
        "typical_duration_hours": optional("decimal", minimum=0),
        "price_source": field(enum=["website", "quote", "invoice", "call", "email", "admin"]),
        "valid_from": field("date"),
        "last_confirmed_at": field("date"),
    }
    quote_fields = {
        "ref": optional(),
        "amount_minor": field("int", minimum=1, required=True),
        "vat_included": field("bool"),
        "scope": field("text"),
        "exclusions": field("text"),
        "earliest_start": optional("date"),
        "valid_until": optional("date"),
        "status": field(enum=["requested", "received", "accepted", "declined", "expired"]),
    }
    transaction_fields = {
        "ref": field(unique=True, required=True),
        "external_ref": optional(),
        "kind": field(enum=["charge", "payment", "transfer", "adjustment"], required=True),
        "category": field(enum=TRANSACTION_CATEGORIES, required=True),
        "amount_minor": field("int", minimum=1, required=True),
        "currency": field(enum=["GBP"], required=True),
        "effective_date": field("date", required=True),
        "period_start": optional("date"),
        "period_end": optional("date"),
        "status": field(
            enum=["expected", "pending", "cleared", "reconciled", "void"], required=True
        ),
        "payment_method": optional(
            enum=["bank transfer", "standing order", "direct debit", "card", "cash", "cheque"]
        ),
        "bank_account": optional(),
        "counterparty_name": field(),
        "description": field("text"),
        "notes": field("array<text>"),
        "recorded_by": field(
            "object",
            properties={
                "kind": field(enum=["ingestion", "agent session", "admin"], required=True),
                "ref": optional(),
            },
        ),
        "confidence": field("float", minimum=0, maximum=1),
        "adjustment_deltas": optional(
            "object",
            properties={
                "tenant_balance_minor": field("int"),
                "landlord_balance_minor": field("int"),
                "deposit_held_minor": field("int"),
            },
        ),
    }
    result = {}
    for name, fields in [
        ("property", property_fields),
        ("transaction", transaction_fields),
        ("service_provider", provider_fields),
        ("service_offering", offering_fields),
        ("quote", quote_fields),
    ]:
        result[name] = {
            "id": name,
            "name": name.replace("_", " ").title(),
            "fields": fields,
            "version": 1,
        }
    result["property"]["composite_keys"] = [["postcode", "address_line1"]]
    result["service_provider"]["composite_keys"] = [["legal_name", "company_number"]]
    result["transaction"]["composite_keys"] = [
        ["external_ref", "amount_minor", "effective_date", "kind", "category"]
    ]
    return result
