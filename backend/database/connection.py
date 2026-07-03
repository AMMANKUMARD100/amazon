import sqlite3
import os
import logging
from backend.config import Config

logger = logging.getLogger('mcp')

def get_db_connection():
    """Establishes and returns a database connection with row factory enabled."""
    db_path = Config.DATABASE_PATH
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")  # Enforce foreign key constraints
    return conn

def execute_query(query, params=(), fetch_one=False, fetch_all=False, commit=False):
    """Executes a SQL query safely using parameterized queries."""
    conn = get_db_connection()
    cursor = conn.cursor()
    result = None
    try:
        cursor.execute(query, params)
        if commit:
            conn.commit()
            result = cursor.lastrowid if cursor.lastrowid else cursor.rowcount
        elif fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Database error executing query: {query}. Error: {e}")
        if commit:
            conn.rollback()
        raise e
    finally:
        conn.close()
    return result

def init_db():
    """Initializes the database schema if tables do not exist."""
    db_path = Config.DATABASE_PATH
    
    # Check if database schema file exists
    base_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(base_dir, 'schema.sql')
    
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema SQL file not found at: {schema_path}")
        
    conn = get_db_connection()
    try:
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise e
    finally:
        conn.close()
