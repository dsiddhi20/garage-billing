import os
import logging
import sqlite3
from config import Config

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_pool = None
_use_sqlite = False
_sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "garage_billing.db")

def is_sqlite():
    global _use_sqlite
    return _use_sqlite

def get_pool():
    global _pool, _use_sqlite
    if _use_sqlite:
        return None
    if _pool is None:
        try:
            import oracledb
            # Enable thin mode connection pooling
            _pool = oracledb.create_pool(
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                dsn=Config.DB_DSN,
                min=2,
                max=10,
                increment=1
            )
            logger.info("Oracle Database connection pool created successfully.")
        except Exception as e:
            logger.warning(f"Oracle Database unavailable ({e}). Switching to SQLite engine.")
            _use_sqlite = True
            _pool = None
    return _pool

def get_connection():
    global _use_sqlite
    if _use_sqlite:
        conn = sqlite3.connect(_sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn
    try:
        pool = get_pool()
        if pool:
            return pool.acquire()
    except Exception:
        _use_sqlite = True
        conn = sqlite3.connect(_sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

def execute_query(query, params=None, commit=False):
    """
    Execute a parameterized query and return cursor and conn.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if _use_sqlite:
            # Adapt Oracle functions to SQLite if needed
            adapted_query = query.replace("TO_DATE(", "(").replace(", 'YYYY-MM-DD')", "")
            if params:
                cursor.execute(adapted_query, params)
            else:
                cursor.execute(adapted_query)
        else:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
        
        if commit:
            conn.commit()
            
        return cursor, conn
    except Exception as e:
        if commit:
            conn.rollback()
        cursor.close()
        conn.close()
        raise e

def execute_fetch_all(query, params=None):
    """
    Execute a query and fetch all results as a list of dicts.
    """
    cursor = None
    conn = None
    try:
        cursor, conn = execute_query(query, params)
        if _use_sqlite:
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        else:
            columns = [col[0].lower() for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return results
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def execute_fetch_one(query, params=None):
    """
    Execute a query and fetch the first result as a dict.
    """
    cursor = None
    conn = None
    try:
        cursor, conn = execute_query(query, params)
        if _use_sqlite:
            row = cursor.fetchone()
            return dict(row) if row else None
        else:
            columns = [col[0].lower() for col in cursor.description]
            row = cursor.fetchone()
            if row:
                return dict(zip(columns, row))
            return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def init_db():
    """
    Creates tables if they do not exist.
    """
    global _use_sqlite
    
    # Check if we should use Oracle or SQLite
    try:
        pool = get_pool()
    except Exception:
        pool = None
        
    if _use_sqlite or pool is None:
        logger.info("Initializing SQLite schema...")
        conn = sqlite3.connect(_sqlite_path)
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                mobile TEXT NOT NULL UNIQUE,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS vehicles (
                vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                vehicle_number TEXT NOT NULL UNIQUE,
                make TEXT,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS bills (
                bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_number TEXT NOT NULL UNIQUE,
                customer_id INTEGER NOT NULL,
                vehicle_id INTEGER NOT NULL,
                bill_date TEXT NOT NULL,
                km INTEGER NOT NULL,
                subtotal REAL NOT NULL,
                discount REAL DEFAULT 0.00,
                tax REAL DEFAULT 0.00,
                total REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id)
            );

            CREATE INDEX IF NOT EXISTS idx_bill_date ON bills(bill_date);

            CREATE TABLE IF NOT EXISTS bill_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE
            );
        """)
        conn.commit()
        conn.close()
        logger.info("SQLite schema initialized successfully.")
        return

    # Oracle Database Initialization
    ddl_blocks = [
        # CUSTOMERS
        """
        DECLARE
            cnt NUMBER;
        BEGIN
            SELECT count(*) INTO cnt FROM user_tables WHERE table_name = 'CUSTOMERS';
            IF cnt = 0 THEN
                EXECUTE IMMEDIATE 'CREATE TABLE customers (
                    customer_id NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    name VARCHAR2(100) NOT NULL,
                    mobile VARCHAR2(15) NOT NULL UNIQUE,
                    address VARCHAR2(1000),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )';
            END IF;
        END;
        """,
        
        # VEHICLES
        """
        DECLARE
            cnt NUMBER;
        BEGIN
            SELECT count(*) INTO cnt FROM user_tables WHERE table_name = 'VEHICLES';
            IF cnt = 0 THEN
                EXECUTE IMMEDIATE 'CREATE TABLE vehicles (
                    vehicle_id NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    customer_id NUMBER NOT NULL,
                    vehicle_number VARCHAR2(20) NOT NULL UNIQUE,
                    make VARCHAR2(50),
                    model VARCHAR2(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_vehicle_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
                )';
            END IF;
        END;
        """,
        
        # BILLS
        """
        DECLARE
            cnt NUMBER;
        BEGIN
            SELECT count(*) INTO cnt FROM user_tables WHERE table_name = 'BILLS';
            IF cnt = 0 THEN
                EXECUTE IMMEDIATE 'CREATE TABLE bills (
                    bill_id NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    bill_number VARCHAR2(20) NOT NULL UNIQUE,
                    customer_id NUMBER NOT NULL,
                    vehicle_id NUMBER NOT NULL,
                    bill_date DATE NOT NULL,
                    km NUMBER NOT NULL,
                    subtotal NUMBER(10, 2) NOT NULL,
                    discount NUMBER(10, 2) DEFAULT 0.00,
                    tax NUMBER(10, 2) DEFAULT 0.00,
                    total NUMBER(10, 2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_bill_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                    CONSTRAINT fk_bill_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id)
                )';
                EXECUTE IMMEDIATE 'CREATE INDEX idx_bill_date ON bills(bill_date)';
            END IF;
        END;
        """,
        
        # BILL_ITEMS
        """
        DECLARE
            cnt NUMBER;
        BEGIN
            SELECT count(*) INTO cnt FROM user_tables WHERE table_name = 'BILL_ITEMS';
            IF cnt = 0 THEN
                EXECUTE IMMEDIATE 'CREATE TABLE bill_items (
                    item_id NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    bill_id NUMBER NOT NULL,
                    description VARCHAR2(255) NOT NULL,
                    amount NUMBER(10, 2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_item_bill FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE
                )';
            END IF;
        END;
        """
    ]
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for block in ddl_blocks:
            cursor.execute(block)
        conn.commit()
        logger.info("Oracle Database schema initialized successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to initialize Oracle database: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()
