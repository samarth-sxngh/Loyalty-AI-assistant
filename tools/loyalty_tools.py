import datetime
from sqlalchemy import create_engine, Column, Integer, String, Numeric, DateTime, Date, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Merchant(Base):
    __tablename__ = "merchants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100))
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Store(Base):
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    city = Column(String(50))
    address = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100))
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LoyaltyAccount(Base):
    __tablename__ = "loyalty_accounts"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    total_points = Column(Integer, default=0)
    available_points = Column(Integer, default=0)
    redeemed_points = Column(Integer, default=0)
    expired_points = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LoyaltyRule(Base):
    __tablename__ = "loyalty_rules"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    rule_name = Column(String(100))
    points_per_rupee = Column(Numeric(5, 2), default=1.0)
    min_transaction_amount = Column(Numeric(10, 2), default=0)
    max_points_per_transaction = Column(Integer, default=10000)
    min_points_for_redemption = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    invoice_number = Column(String(50), unique=True)
    transaction_amount = Column(Numeric(10, 2), nullable=False)
    transaction_date = Column(DateTime, default=datetime.datetime.utcnow)
    points_awarded_status = Column(String(20), default='awarded')

class PointsLedger(Base):
    __tablename__ = "points_ledger"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    points = Column(Integer, nullable=False)
    type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default='active')
    description = Column(String)
    expiry_date = Column(Date)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Coupon(Base):
    __tablename__ = "coupons"
    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    coupon_code = Column(String(50), unique=True, nullable=False)
    description = Column(String)
    discount_type = Column(String(20), nullable=False)
    discount_value = Column(Numeric(10, 2), nullable=False)
    min_purchase_amount = Column(Numeric(10, 2), default=0)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class CustomerCoupon(Base):
    __tablename__ = "customer_coupons"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=False)
    status = Column(String(20), default='available')
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow)
    used_at = Column(DateTime)


def get_points_balance(customer_id: int, merchant_id: int) -> dict:
    """Returns the full points summary for a customer."""
    with SessionLocal() as session:
        account = session.query(LoyaltyAccount).filter(
            LoyaltyAccount.customer_id == customer_id,
            LoyaltyAccount.merchant_id == merchant_id
        ).first()

        if not account:
            return {"error": "No loyalty account found for this customer."}

        return {
            "total_points": account.total_points,
            "available_points": account.available_points,
            "redeemed_points": account.redeemed_points,
            "expired_points": account.expired_points
        }


def get_expiring_points(customer_id: int, merchant_id: int, days: int = 60) -> dict:
    """Returns points that are expiring within the next N days."""
    target_date = datetime.date.today() + datetime.timedelta(days=days)
    
    with SessionLocal() as session:
        expiring = session.query(PointsLedger).filter(
            PointsLedger.customer_id == customer_id,
            PointsLedger.merchant_id == merchant_id,
            PointsLedger.status == 'active',
            PointsLedger.expiry_date.isnot(None),
            PointsLedger.expiry_date <= target_date
        ).order_by(PointsLedger.expiry_date.asc()).all()

        if not expiring:
            return {"expiring_points": []}

        return {
            "expiring_points": [
                {
                    "points": item.points,
                    "description": item.description,
                    "expiry_date": str(item.expiry_date)
                }
                for item in expiring
            ]
        }


def get_available_coupons(customer_id: int, merchant_id: int) -> dict:
    """Returns all coupons currently available to the customer."""
    with SessionLocal() as session:
        coupons = session.query(Coupon).join(
            CustomerCoupon, Coupon.id == CustomerCoupon.coupon_id
        ).filter(
            CustomerCoupon.customer_id == customer_id,
            CustomerCoupon.merchant_id == merchant_id,
            CustomerCoupon.status == 'available',
            Coupon.is_active == True,
            Coupon.valid_to >= datetime.date.today()
        ).order_by(Coupon.valid_to.asc()).all()

        if not coupons:
            return {"coupons": []}

        return {
            "coupons": [
                {
                    "coupon_code": c.coupon_code,
                    "description": c.description,
                    "discount_type": c.discount_type,
                    "discount_value": float(c.discount_value),
                    "min_purchase_amount": float(c.min_purchase_amount),
                    "valid_to": str(c.valid_to)
                }
                for c in coupons
            ]
        }


def get_recent_loyalty_activity(customer_id: int, merchant_id: int, limit: int = 10) -> dict:
    """Returns the most recent points ledger entries for the customer."""
    with SessionLocal() as session:
        activities = session.query(PointsLedger, Transaction).outerjoin(
            Transaction, PointsLedger.transaction_id == Transaction.id
        ).filter(
            PointsLedger.customer_id == customer_id,
            PointsLedger.merchant_id == merchant_id
        ).order_by(PointsLedger.created_at.desc()).limit(limit).all()

        if not activities:
            return {"activity": []}

        return {
            "activity": [
                {
                    "points": pl.points,
                    "type": pl.type,
                    "status": pl.status,
                    "description": pl.description,
                    "expiry_date": str(pl.expiry_date) if pl.expiry_date else None,
                    "date": str(pl.created_at),
                    "invoice_number": t.invoice_number if t else None,
                    "transaction_amount": float(t.transaction_amount) if t and t.transaction_amount else None
                }
                for pl, t in activities
            ]
        }


def check_redemption_eligibility(customer_id: int, merchant_id: int) -> dict:
    """Checks if the customer has enough points to redeem."""
    with SessionLocal() as session:
        account = session.query(LoyaltyAccount).filter(
            LoyaltyAccount.customer_id == customer_id,
            LoyaltyAccount.merchant_id == merchant_id
        ).first()

        rule = session.query(LoyaltyRule).filter(
            LoyaltyRule.merchant_id == merchant_id
        ).first()

        if not account:
            return {"error": "No loyalty account found."}

        available = account.available_points
        min_required = rule.min_points_for_redemption if rule else 500

        return {
            "available_points": available,
            "min_points_for_redemption": min_required,
            "is_eligible": available >= min_required,
            "points_per_rupee": float(rule.points_per_rupee) if rule else 1.0
        }


def check_missing_points(customer_id: int, merchant_id: int) -> dict:
    """Returns recent transactions where points were denied or are pending."""
    with SessionLocal() as session:
        transactions = session.query(Transaction).filter(
            Transaction.customer_id == customer_id,
            Transaction.merchant_id == merchant_id,
            Transaction.points_awarded_status.in_(['denied', 'pending'])
        ).order_by(Transaction.transaction_date.desc()).limit(5).all()

        rule = session.query(LoyaltyRule).filter(
            LoyaltyRule.merchant_id == merchant_id
        ).first()

        min_amount = float(rule.min_transaction_amount) if rule else 200.0

        if not transactions:
            return {"missing_points": [], "min_transaction_amount": min_amount}

        return {
            "missing_points": [
                {
                    "invoice_number": t.invoice_number,
                    "transaction_amount": float(t.transaction_amount),
                    "transaction_date": str(t.transaction_date),
                    "status": t.points_awarded_status
                }
                for t in transactions
            ],
            "min_transaction_amount": min_amount
        }


def get_last_transaction(customer_id: int, merchant_id: int) -> dict:
    """Returns the most recent transaction for the customer."""
    with SessionLocal() as session:
        result = session.query(Transaction, Store, PointsLedger).join(
            Store, Transaction.store_id == Store.id
        ).outerjoin(
            PointsLedger, (PointsLedger.transaction_id == Transaction.id) & (PointsLedger.type == 'earned')
        ).filter(
            Transaction.customer_id == customer_id,
            Transaction.merchant_id == merchant_id
        ).order_by(Transaction.transaction_date.desc()).first()

        if not result:
            return {"error": "No transactions found."}

        t, s, pl = result

        return {
            "invoice_number": t.invoice_number,
            "transaction_amount": float(t.transaction_amount),
            "transaction_date": str(t.transaction_date),
            "points_awarded_status": t.points_awarded_status,
            "store_name": s.name,
            "city": s.city,
            "points_earned": pl.points if pl else None
        }


def get_customer_name(customer_id: int, merchant_id: int) -> dict:
    """Returns the customer's name — used to personalise responses."""
    with SessionLocal() as session:
        customer = session.query(Customer).filter(
            Customer.id == customer_id,
            Customer.merchant_id == merchant_id
        ).first()

        if not customer:
            return {"name": "Customer", "email": None}

        return {"name": customer.name, "email": customer.email}