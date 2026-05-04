from sqlalchemy import create_engine, text
from config import DATABASE_URL

# Create a single DB engine reused across all tools
engine = create_engine(DATABASE_URL)


def get_points_balance(customer_id: int, merchant_id: int) -> dict:
    """Returns the full points summary for a customer."""
    query = text("""
        SELECT 
            total_points,
            available_points,
            redeemed_points,
            expired_points
        FROM loyalty_accounts
        WHERE customer_id = :customer_id
          AND merchant_id = :merchant_id
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {
            "customer_id": customer_id,
            "merchant_id": merchant_id
        }).fetchone()

    if not result:
        return {"error": "No loyalty account found for this customer."}

    return {
        "total_points": result.total_points,
        "available_points": result.available_points,
        "redeemed_points": result.redeemed_points,
        "expired_points": result.expired_points
    }


def get_expiring_points(customer_id: int, merchant_id: int, days: int = 60) -> dict:
    """Returns points that are expiring within the next N days."""
    query = text("""
        SELECT
            points,
            description,
            expiry_date
        FROM points_ledger
        WHERE customer_id = :customer_id
          AND merchant_id = :merchant_id
          AND status = 'active'
          AND expiry_date <= CURRENT_DATE + INTERVAL ':days days'
        ORDER BY expiry_date ASC
    """)
    # NOTE: INTERVAL doesn't accept bind params directly, so we use a workaround
    query = text(f"""
        SELECT
            points,
            description,
            expiry_date
        FROM points_ledger
        WHERE customer_id = :customer_id
          AND merchant_id = :merchant_id
          AND status = 'active'
          AND expiry_date IS NOT NULL
          AND expiry_date <= CURRENT_DATE + INTERVAL '{days} days'
        ORDER BY expiry_date ASC
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {
            "customer_id": customer_id,
            "merchant_id": merchant_id
        }).fetchall()

    if not rows:
        return {"expiring_points": []}

    return {
        "expiring_points": [
            {
                "points": row.points,
                "description": row.description,
                "expiry_date": str(row.expiry_date)
            }
            for row in rows
        ]
    }


def get_available_coupons(customer_id: int, merchant_id: int) -> dict:
    """Returns all coupons currently available to the customer."""
    query = text("""
        SELECT
            c.coupon_code,
            c.description,
            c.discount_type,
            c.discount_value,
            c.min_purchase_amount,
            c.valid_to
        FROM customer_coupons cc
        JOIN coupons c ON cc.coupon_id = c.id
        WHERE cc.customer_id = :customer_id
          AND cc.merchant_id = :merchant_id
          AND cc.status = 'available'
          AND c.valid_to >= CURRENT_DATE
          AND c.is_active = TRUE
        ORDER BY c.valid_to ASC
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {
            "customer_id": customer_id,
            "merchant_id": merchant_id
        }).fetchall()

    if not rows:
        return {"coupons": []}

    return {
        "coupons": [
            {
                "coupon_code": row.coupon_code,
                "description": row.description,
                "discount_type": row.discount_type,
                "discount_value": float(row.discount_value),
                "min_purchase_amount": float(row.min_purchase_amount),
                "valid_to": str(row.valid_to)
            }
            for row in rows
        ]
    }


def get_recent_loyalty_activity(customer_id: int, merchant_id: int, limit: int = 10) -> dict:
    """Returns the most recent points ledger entries for the customer."""
    query = text("""
        SELECT
            pl.points,
            pl.type,
            pl.status,
            pl.description,
            pl.expiry_date,
            pl.created_at,
            t.invoice_number,
            t.transaction_amount
        FROM points_ledger pl
        LEFT JOIN transactions t ON pl.transaction_id = t.id
        WHERE pl.customer_id = :customer_id
          AND pl.merchant_id = :merchant_id
        ORDER BY pl.created_at DESC
        LIMIT :limit
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {
            "customer_id": customer_id,
            "merchant_id": merchant_id,
            "limit": limit
        }).fetchall()

    if not rows:
        return {"activity": []}

    return {
        "activity": [
            {
                "points": row.points,
                "type": row.type,
                "status": row.status,
                "description": row.description,
                "expiry_date": str(row.expiry_date) if row.expiry_date else None,
                "date": str(row.created_at),
                "invoice_number": row.invoice_number,
                "transaction_amount": float(row.transaction_amount) if row.transaction_amount else None
            }
            for row in rows
        ]
    }


def check_redemption_eligibility(customer_id: int, merchant_id: int) -> dict:
    """Checks if the customer has enough points to redeem."""
    balance_query = text("""
        SELECT available_points
        FROM loyalty_accounts
        WHERE customer_id = :customer_id
          AND merchant_id = :merchant_id
    """)
    rule_query = text("""
        SELECT min_points_for_redemption, points_per_rupee
        FROM loyalty_rules
        WHERE merchant_id = :merchant_id
        LIMIT 1
    """)
    with engine.connect() as conn:
        balance = conn.execute(balance_query, {
            "customer_id": customer_id,
            "merchant_id": merchant_id
        }).fetchone()

        rule = conn.execute(rule_query, {
            "merchant_id": merchant_id
        }).fetchone()

    if not balance:
        return {"error": "No loyalty account found."}

    available = balance.available_points
    min_required = rule.min_points_for_redemption if rule else 500

    return {
        "available_points": available,
        "min_points_for_redemption": min_required,
        "is_eligible": available >= min_required,
        "points_per_rupee": float(rule.points_per_rupee) if rule else 1.0
    }


def check_missing_points(customer_id: int, merchant_id: int) -> dict:
    """Returns recent transactions where points were denied or are pending."""
    query = text("""
        SELECT
            invoice_number,
            transaction_amount,
            transaction_date,
            points_awarded_status
        FROM transactions
        WHERE customer_id = :customer_id
          AND merchant_id = :merchant_id
          AND points_awarded_status IN ('denied', 'pending')
        ORDER BY transaction_date DESC
        LIMIT 5
    """)
    rule_query = text("""
        SELECT min_transaction_amount
        FROM loyalty_rules
        WHERE merchant_id = :merchant_id
        LIMIT 1
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {
            "customer_id": customer_id,
            "merchant_id": merchant_id
        }).fetchall()
        rule = conn.execute(rule_query, {
            "merchant_id": merchant_id
        }).fetchone()

    min_amount = float(rule.min_transaction_amount) if rule else 200.0

    if not rows:
        return {"missing_points": [], "min_transaction_amount": min_amount}

    return {
        "missing_points": [
            {
                "invoice_number": row.invoice_number,
                "transaction_amount": float(row.transaction_amount),
                "transaction_date": str(row.transaction_date),
                "status": row.points_awarded_status
            }
            for row in rows
        ],
        "min_transaction_amount": min_amount
    }


def get_last_transaction(customer_id: int, merchant_id: int) -> dict:
    """Returns the most recent transaction for the customer."""
    query = text("""
        SELECT
            t.invoice_number,
            t.transaction_amount,
            t.transaction_date,
            t.points_awarded_status,
            s.name AS store_name,
            s.city,
            pl.points AS points_earned
        FROM transactions t
        JOIN stores s ON t.store_id = s.id
        LEFT JOIN points_ledger pl ON pl.transaction_id = t.id
            AND pl.type = 'earned'
        WHERE t.customer_id = :customer_id
          AND t.merchant_id = :merchant_id
        ORDER BY t.transaction_date DESC
        LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(query, {
            "customer_id": customer_id,
            "merchant_id": merchant_id
        }).fetchone()

    if not row:
        return {"error": "No transactions found."}

    return {
        "invoice_number": row.invoice_number,
        "transaction_amount": float(row.transaction_amount),
        "transaction_date": str(row.transaction_date),
        "points_awarded_status": row.points_awarded_status,
        "store_name": row.store_name,
        "city": row.city,
        "points_earned": row.points_earned
    }


def get_customer_name(customer_id: int, merchant_id: int) -> dict:
    """Returns the customer's name — used to personalise responses."""
    query = text("""
        SELECT name, email
        FROM customers
        WHERE id = :customer_id
          AND merchant_id = :merchant_id
    """)
    with engine.connect() as conn:
        row = conn.execute(query, {
            "customer_id": customer_id,
            "merchant_id": merchant_id
        }).fetchone()

    if not row:
        return {"name": "Customer", "email": None}

    return {"name": row.name, "email": row.email}