# ABC Loyalty Assistant

A chatbot designed to help customers query their loyalty points, coupons, rewards, and purchase history.

## 1. How to set up PostgreSQL

1. Install PostgreSQL on your system (e.g., via Homebrew on Mac: `brew install postgresql`).
2. Start the PostgreSQL service: `brew services start postgresql`.
3. Create a new database called `abc_loyalty`:
   ```bash
   createdb abc_loyalty
   ```
4. Alternatively, use `psql` to create the database:
   ```sql
   CREATE DATABASE abc_loyalty;
   ```

## 2. How to create the database tables

Connect to the `abc_loyalty` database and run the following SQL commands to create the necessary tables:

```sql

LOYALTY AI ASSISTANT - Schema


1. MERCHANTS
A merchant is a business (like a shop or brand) using the loyalty system
CREATE TABLE merchants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

2. STORES
One merchant can have multiple physical store locations
CREATE TABLE stores (
    id SERIAL PRIMARY KEY,
    merchant_id INT NOT NULL REFERENCES merchants(id),
    name VARCHAR(100) NOT NULL,
    city VARCHAR(50),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

3. CUSTOMERS
End users who shop at merchant stores

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    merchant_id INT NOT NULL REFERENCES merchants(id),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

4. LOYALTY ACCOUNTS
Each customer has one loyalty account per merchant
This tracks their overall points summary
CREATE TABLE loyalty_accounts (
    id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(id),
    merchant_id INT NOT NULL REFERENCES merchants(id),
    total_points INT DEFAULT 0,
    available_points INT DEFAULT 0,
    redeemed_points INT DEFAULT 0,
    expired_points INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(customer_id, merchant_id)
);

5. LOYALTY RULES
Rules set by the merchant: how many points per rupee spent, minimums, etc.
CREATE TABLE loyalty_rules (
    id SERIAL PRIMARY KEY,
    merchant_id INT NOT NULL REFERENCES merchants(id),
    rule_name VARCHAR(100),
    points_per_rupee NUMERIC(5,2) DEFAULT 1.0,
    min_transaction_amount NUMERIC(10,2) DEFAULT 0,
    max_points_per_transaction INT DEFAULT 10000,
    min_points_for_redemption INT DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

6. TRANSACTIONS
Every purchase a customer makes at a store
points_awarded_status tells us if points were given or not
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(id),
    merchant_id INT NOT NULL REFERENCES merchants(id),
    store_id INT NOT NULL REFERENCES stores(id),
    invoice_number VARCHAR(50) UNIQUE,
    transaction_amount NUMERIC(10,2) NOT NULL,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    points_awarded_status VARCHAR(20) DEFAULT 'awarded'
        CHECK (points_awarded_status IN ('awarded', 'pending', 'denied'))
);

7. POINTS LEDGER
Every single points movement (earned, redeemed, expired, adjusted)
Think of this like a bank statement for points
CREATE TABLE points_ledger (
    id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(id),
    merchant_id INT NOT NULL REFERENCES merchants(id),
    transaction_id INT REFERENCES transactions(id),
    points INT NOT NULL,
    type VARCHAR(20) NOT NULL
        CHECK (type IN ('earned', 'redeemed', 'expired', 'adjusted')),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'pending', 'expired', 'redeemed')),
    description TEXT,
    expiry_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

8. COUPONS
Discount coupons created by merchants
CREATE TABLE coupons (
    id SERIAL PRIMARY KEY,
    merchant_id INT NOT NULL REFERENCES merchants(id),
    coupon_code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    discount_type VARCHAR(20) NOT NULL
        CHECK (discount_type IN ('percentage', 'flat')),
    discount_value NUMERIC(10,2) NOT NULL,
    min_purchase_amount NUMERIC(10,2) DEFAULT 0,
    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

9. CUSTOMER COUPONS
Tracks which coupons have been assigned to which customer

CREATE TABLE customer_coupons (
    id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(id),
    merchant_id INT NOT NULL REFERENCES merchants(id),
    coupon_id INT NOT NULL REFERENCES coupons(id),
    status VARCHAR(20) DEFAULT 'available'
        CHECK (status IN ('available', 'used', 'expired')),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP,
    UNIQUE(customer_id, coupon_id)
);
```

## 3. How to insert dummy data

Run the following SQL commands to insert dummy data for testing:

```sql

SEED DATA - ABC Loyalty Assistant


1. MERCHANT
INSERT INTO merchants (id, name, email, phone) VALUES
(1, 'ABC Company', 'contact@abccompany.com', '+91-9876543210');

2. STORES
INSERT INTO stores (id, merchant_id, name, city, address) VALUES
(1, 1, 'ABC Store - Bandra', 'Mumbai', 'Shop 12, Linking Road, Bandra West'),
(2, 1, 'ABC Store - Andheri', 'Mumbai', 'Plot 45, Andheri East'),
(3, 1, 'ABC Store - Pune', 'Pune', 'FC Road, Shivajinagar');

3. CUSTOMERS
Customer 101 is our fixed test customer (as per assignment)
INSERT INTO customers (id, merchant_id, name, email, phone) VALUES
(101, 1, 'Samarth Singh', 'samarth@gmail.com', '+91-9876500101'),
(102, 1, 'Priya Mehta',   'priya@gmail.com',   '+91-9876500102'),
(103, 1, 'Rahul Sharma',  'rahul@gmail.com',   '+91-9876500103');

4. LOYALTY ACCOUNTS
Customer 101 has a healthy account with various point states

INSERT INTO loyalty_accounts (customer_id, merchant_id, total_points, available_points, redeemed_points, expired_points) VALUES
(101, 1, 2450, 1200, 950, 300),
(102, 1, 800,  800,  0,   0),
(103, 1, 500,  200,  300, 0);

5. LOYALTY RULES

INSERT INTO loyalty_rules (merchant_id, rule_name, points_per_rupee, min_transaction_amount, max_points_per_transaction, min_points_for_redemption) VALUES
(1, 'Standard Earn Rule', 1.0, 200.00, 5000, 500);

6. TRANSACTIONS
Various transactions for customer 101 covering all scenarios

INSERT INTO transactions (id, customer_id, merchant_id, store_id, invoice_number, transaction_amount, transaction_date, points_awarded_status) VALUES
Recent transactions (points awarded normally)
(1,  101, 1, 1, 'INV-2026-001', 1500.00, '2026-04-28 11:00:00', 'awarded'),
(2,  101, 1, 2, 'INV-2026-002', 2200.00, '2026-04-20 14:30:00', 'awarded'),
(3,  101, 1, 1, 'INV-2026-003', 850.00,  '2026-04-10 10:15:00', 'awarded'),
Pending transaction (points not yet confirmed)
(4,  101, 1, 3, 'INV-2026-004', 3000.00, '2026-04-30 16:00:00', 'pending'),
Denied transaction (below minimum purchase amount of Rs 200)
(5,  101, 1, 2, 'INV-2026-005', 150.00,  '2026-04-25 09:00:00', 'denied'),
Older transactions
(6,  101, 1, 1, 'INV-2025-101', 5000.00, '2025-12-15 13:00:00', 'awarded'),
(7,  101, 1, 2, 'INV-2025-102', 1200.00, '2025-11-20 15:00:00', 'awarded'),
Other customers
(8,  102, 1, 1, 'INV-2026-102', 800.00,  '2026-04-22 12:00:00', 'awarded'),
(9,  103, 1, 3, 'INV-2026-103', 500.00,  '2026-04-18 11:00:00', 'awarded');

7. POINTS LEDGER
Detailed record of every points movement for customer 101

INSERT INTO points_ledger (customer_id, merchant_id, transaction_id, points, type, status, description, expiry_date, created_at) VALUES

Earned points (active, not expiring soon)

(101, 1, 1, 1500, 'earned', 'active', 'Points earned on INV-2026-001', '2027-04-28', '2026-04-28 11:00:00'),
(101, 1, 2, 2200, 'earned', 'active', 'Points earned on INV-2026-002', '2027-04-20', '2026-04-20 14:30:00'),
(101, 1, 3, 850,  'earned', 'active', 'Points earned on INV-2026-003', '2027-04-10', '2026-04-10 10:15:00'),

Pending points (from recent transaction, not yet confirmed)

(101, 1, 4, 3000, 'earned', 'pending', 'Points pending for INV-2026-004 - under review', '2027-04-30', '2026-04-30 16:00:00'),

EXPIRING SOON - this is critical for the "are my points expiring" question

(101, 1, 6, 300, 'earned', 'active', 'Points expiring soon - earned Dec 2025', '2026-06-15', '2025-12-15 13:00:00'),

Redeemed points (used by customer previously)
(101, 1, 7, 950, 'redeemed', 'redeemed', 'Points redeemed for discount on order', NULL, '2025-11-20 15:00:00'),

Expired points (already gone)
(101, 1, NULL, 300, 'expired', 'expired', 'Points expired from 2024 purchases', '2025-12-31', '2024-06-01 00:00:00'),

Adjusted points (manual correction by merchant)
(101, 1, NULL, 100, 'adjusted', 'active', 'Bonus points added by merchant for festival offer', '2027-01-01', '2026-01-15 00:00:00'),

Other customers ledger
(102, 1, 8, 800,  'earned', 'active', 'Points earned on INV-2026-102', '2027-04-22', '2026-04-22 12:00:00'),
(103, 1, 9, 500,  'earned', 'active', 'Points earned on INV-2026-103', '2027-04-18', '2026-04-18 11:00:00');

8. COUPONS
INSERT INTO coupons (id, merchant_id, coupon_code, description, discount_type, discount_value, min_purchase_amount, valid_from, valid_to, is_active) VALUES

Active coupons (customer 101 will have these)
(1, 1, 'SAVE10',   'Get 10% off on orders above Rs 1,000',  'percentage', 10.00, 1000.00, '2026-01-01', '2026-06-30', TRUE),
(2, 1, 'FLAT200',  'Get Rs 200 off on orders above Rs 2,000', 'flat',     200.00, 2000.00, '2026-01-01', '2026-07-10', TRUE),
Used coupon
(3, 1, 'WELCOME50','Welcome offer: Rs 50 off on first purchase', 'flat',   50.00,  500.00,  '2026-01-01', '2026-12-31', TRUE),
Expired coupon
(4, 1, 'DIWALI20', 'Diwali special: 20% off',               'percentage', 20.00, 1000.00, '2025-10-01', '2025-11-15', FALSE),
A coupon that customer 101 does NOT have (to test no-coupon edge case)

(5, 1, 'VIP500',   'VIP exclusive: Rs 500 off',             'flat',       500.00, 5000.00, '2026-01-01', '2026-12-31', TRUE);

9. CUSTOMER COUPONS
Assign coupons to customer 101 covering all status scenarios

INSERT INTO customer_coupons (customer_id, merchant_id, coupon_id, status, assigned_at, used_at) VALUES
Available (can use right now)
(101, 1, 1, 'available', '2026-01-01 00:00:00', NULL),
(101, 1, 2, 'available', '2026-01-01 00:00:00', NULL),
Used (already redeemed)
(101, 1, 3, 'used',      '2026-01-01 00:00:00', '2026-02-10 14:00:00'),
Expired (coupon itself expired)
(101, 1, 4, 'expired',   '2025-10-01 00:00:00', NULL),
Other customers
(102, 1, 1, 'available', '2026-02-01 00:00:00', NULL),
(103, 1, 5, 'available', '2026-03-01 00:00:00', NULL);
```

## 4. Required environment variables

Create a `.env` file in the root directory and configure the following variables:

```ini
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://username:password@localhost:5432/abc_loyalty
LLM_MODEL=llama-3.3-70b-versatile
CUSTOMER_ID=101
MERCHANT_ID=1
```

## 5. How to run the chatbot locally

1. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```

## 6. How to test sample questions

Once the app is running locally, open the provided URL (usually `http://localhost:8501`).
You can use the sidebar buttons to test predefined questions, or type them in the chat input. Sample questions include:
- "How many points do I have?"
- "Are my points expiring soon?"
- "Do I have any coupons?"
- "Can I redeem my points?"
- "Show my recent activity"
- "Why didn't I get points?"
- "What was my last purchase?"

## 7. Which LLM/model was used

The project uses Groq's API with the **Llama 3.3 70B Versatile** model (`llama-3.3-70b-versatile`) for natural language understanding and tool dispatching.

## 8. Assumptions made

- The user operates in a single-tenant fashion (or the UI context is statically mapped to a specific user via `CUSTOMER_ID` and `MERCHANT_ID` in the `.env` file).
- The database runs locally on PostgreSQL and can be accessed via the standard `psycopg2` driver.
- The assistant is strictly constrained to answering loyalty-related questions and should deflect off-topic inputs.
- Only the specific customer's data can be accessed; queries attempting to fetch other customers' details are blocked.

## 9. Known limitations

- The application uses fixed IDs (`CUSTOMER_ID` and `MERCHANT_ID`) rather than implementing a full authentication system.
- The LLM relies on specific keywords and patterns to detect off-topic or privacy-violating questions. More sophisticated prompt injections might occasionally bypass these simple guardrails.
- Advanced querying (like filtering activities by specific date ranges or complex transaction joins) may require additional or enhanced tools.

