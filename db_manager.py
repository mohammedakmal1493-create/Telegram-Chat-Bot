# db_manager.py - Simplified Database Manager for Telegram Canteen Bot
import sqlite3
import json
from pathlib import Path
from datetime import datetime

# Database configuration
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / 'simple_canteen_bot.db'


def create_connection():
    """Create database connection."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None


def create_tables():
    """Create necessary database tables."""
    try:
        conn = create_connection()
        if not conn:
            return False

        cursor = conn.cursor()

        # Create menu table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                available BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create orders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_phone TEXT NOT NULL,
                items TEXT NOT NULL,
                total_amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                pickup_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create user sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                student_phone TEXT PRIMARY KEY,
                state TEXT DEFAULT 'initial',
                current_order_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()
        print("✅ Simplified Database tables verified/created successfully!")
        return True

    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False


def add_default_menu_items():
    """Add some default menu items if menu is empty."""
    try:
        conn = create_connection()
        if not conn:
            return False

        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM menu')
        count = cursor.fetchone()[0]

        if count == 0:
            default_items = [
                ('Samosa', 15.0),
                ('Tea', 10.0),
                ('Coffee', 15.0),
                ('Vada Pav', 20.0),
            ]
            cursor.executemany('INSERT INTO menu (name, price) VALUES (?, ?)', default_items)
            conn.commit()
            print("✅ Default menu items added successfully!")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error adding default menu items: {e}")
        return False


# ========== MENU OPERATIONS ==========

def get_menu():
    """Get all available menu items."""
    try:
        conn = create_connection()
        if not conn: return []
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM menu WHERE available = 1 ORDER BY id')
        items = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return items
    except Exception as e:
        print(f"❌ Error getting menu: {e}")
        return []


def get_menu_item(item_id):
    """Get a single menu item by its ID."""
    try:
        conn = create_connection()
        if not conn: return None
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM menu WHERE id = ? AND available = 1', (item_id,))
        item = cursor.fetchone()
        conn.close()
        return dict(item) if item else None
    except Exception as e:
        print(f"❌ Error getting menu item {item_id}: {e}")
        return None


def add_menu_item(name, price):
    """Admin function: Add a new menu item."""
    try:
        conn = create_connection()
        if not conn: return "❌ Database connection error"
        cursor = conn.cursor()
        cursor.execute('INSERT INTO menu (name, price) VALUES (?, ?)', (name, price))
        conn.commit()
        item_id = cursor.lastrowid
        conn.close()
        return f"✅ Added '{name}' for ₹{price:.2f} (ID: {item_id})"
    except Exception as e:
        print(f"❌ Error adding menu item: {e}")
        return "❌ Error adding menu item"


def delete_menu_item(item_id):
    """Admin function: Make menu item unavailable (Soft Delete)."""
    try:
        conn = create_connection()
        if not conn: return "❌ Database connection error"
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM menu WHERE id = ?', (item_id,))
        item = cursor.fetchone()
        if not item:
            conn.close()
            return f"❌ Item ID {item_id} not found"
        cursor.execute('UPDATE menu SET available = 0 WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()
        return f"✅ Removed '{item[0]}' from menu"
    except Exception as e:
        print(f"❌ Error deleting menu item: {e}")
        return "❌ Error deleting menu item"


# ========== ORDER OPERATIONS ==========

def create_order(student_phone, order_details, total_amount, status='pending'):
    """Create a new record entry inside the orders table."""
    try:
        conn = create_connection()
        if not conn: return None
        cursor = conn.cursor()
        items_json = json.dumps(order_details)

        cursor.execute('''
            INSERT INTO orders (student_phone, items, total_amount, status)
            VALUES (?, ?, ?, ?)
        ''', (student_phone, items_json, total_amount, status))

        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        print(f"✅ Order #{order_id} created for user {student_phone}")
        return order_id
    except Exception as e:
        print(f"❌ Error creating order: {e}")
        return None


def get_order_details(order_id):
    """Retrieve details of an order using its ID."""
    try:
        conn = create_connection()
        if not conn: return None
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        order = cursor.fetchone()
        conn.close()
        return dict(order) if order else None
    except Exception as e:
        print(f"❌ Error getting order details for {order_id}: {e}")
        return None


def update_order_status(order_id, status):
    """Update order lifecycle state (e.g., pending -> confirmed)."""
    try:
        conn = create_connection()
        if not conn: return False
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (status, order_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    except Exception as e:
        print(f"❌ Error updating order status: {e}")
        return False


def update_order_pickup_code(order_id, pickup_code):
    """Store the unique security code required for manual counter collection."""
    try:
        conn = create_connection()
        if not conn: return False
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE orders SET pickup_code = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (pickup_code, order_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    except Exception as e:
        print(f"❌ Error updating pickup code: {e}")
        return False


def parse_order_items(items_json):
    """Convert stored JSON strings back into readable Python collections."""
    try:
        if isinstance(items_json, str):
            return json.loads(items_json)
        return items_json
    except Exception as e:
        print(f"❌ Error parsing order items: {e}")
        return []


# ========== SESSION MANAGEMENT ==========

def get_session_state(student_phone):
    """Track conversational stage mapping for a unique Telegram user ID."""
    try:
        conn = create_connection()
        if not conn: return 'initial'
        cursor = conn.cursor()
        cursor.execute('SELECT state FROM user_sessions WHERE student_phone = ?', (student_phone,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 'initial'
    except Exception as e:
        print(f"❌ Error getting session state: {e}")
        return 'initial'


def set_session_state(student_phone, state, order_id=None):
    """Overwrites or registers current student navigation workflow milestones."""
    try:
        conn = create_connection()
        if not conn: return False
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO user_sessions 
            (student_phone, state, current_order_id, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (student_phone, state, order_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error setting session state: {e}")
        return False


def get_session_order_id(student_phone):
    """Find out which order ID is tied to the student's active conversational session."""
    try:
        conn = create_connection()
        if not conn: return None
        cursor = conn.cursor()
        cursor.execute('SELECT current_order_id FROM user_sessions WHERE student_phone = ?', (student_phone,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Error getting session order ID: {e}")
        return None


if __name__ == '__main__':
    # Initialize when running module directly
    create_tables()
    add_default_menu_items()
