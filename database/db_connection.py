# ====================================================================
# DB_CONNECTION.PY - Database Connection Handling
# ====================================================================
# Responsible for:
# 1. Creating database folder
# 2. Managing database connections
# 3. Handling connection errors and corruption
# ====================================================================

import sqlite3
from pathlib import Path

# Create a folder called 'database' in your project
DB_DIR = Path("database")
DB_DIR.mkdir(exist_ok=True)

# This is the actual database file path
DB_PATH = DB_DIR / "elderly_care.db"


def get_connection():
    """
    Creates and returns a connection to the SQLite database.
    Checks for corruption before connecting.
    
    Returns:
        sqlite3.Connection: Database connection object with row_factory set to sqlite3.Row
    """
    # Check if database file is corrupted before connecting
    if DB_PATH.exists():
        try:
            test_conn = sqlite3.connect(str(DB_PATH))
            test_conn.cursor().execute("SELECT 1")
            test_conn.close()
        except sqlite3.DatabaseError:
            print("⚠️ Corrupted database found. Creating new one...")
            DB_PATH.unlink()  # Delete the corrupted file
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # Access columns by name (like row['name'])
    return conn


def close_connection(conn):
    """
    Safely close a database connection.
    
    Args:
        conn: sqlite3 connection object to close
    """
    if conn:
        conn.close()