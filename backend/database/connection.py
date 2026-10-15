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

def run_migrations(conn):
    """Executes non-destructive schema migrations safely."""
    cursor = conn.cursor()

    # 1. Clean up fake GEN subject rows that were created previously
    # Reassign any assignments on fake GEN subjects to subject_id = NULL
    try:
        gen_subs = cursor.execute("SELECT id FROM subjects WHERE code = 'GEN';").fetchall()
        for g in gen_subs:
            cursor.execute("UPDATE assignments SET subject_id = NULL WHERE subject_id = ?;", (g[0],))
            cursor.execute("DELETE FROM subjects WHERE id = ?;", (g[0],))
    except sqlite3.Error:
        pass

    # 2. Check assignments table structure
    cursor.execute("PRAGMA table_info(assignments);")
    cols = {row['name']: row for row in cursor.fetchall()}
    
    # Add created_at if missing
    if 'created_at' not in cols:
        try:
            cursor.execute("ALTER TABLE assignments ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        except sqlite3.Error:
            pass

    # Add updated_at if missing
    if 'updated_at' not in cols:
        try:
            cursor.execute("ALTER TABLE assignments ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        except sqlite3.Error:
            pass

    # Check if subject_id is nullable (notnull == 0)
    # If notnull == 1, migrate assignments table to allow subject_id NULL
    if cols.get('subject_id') and cols['subject_id']['notnull'] == 1:
        try:
            cursor.execute("PRAGMA foreign_keys = OFF;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assignments_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    subject_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_date DATE NOT NULL,
                    status TEXT CHECK(status IN ('Pending', 'Completed')) NOT NULL DEFAULT 'Pending',
                    priority TEXT CHECK(priority IN ('High', 'Medium', 'Low')) NOT NULL DEFAULT 'Medium',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                    FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
                );
            """)
            cursor.execute("""
                INSERT INTO assignments_new (id, student_id, subject_id, title, description, due_date, status, priority, created_at, updated_at)
                SELECT id, student_id, subject_id, title, description, due_date, status, priority,
                       COALESCE(created_at, CURRENT_TIMESTAMP), COALESCE(updated_at, CURRENT_TIMESTAMP)
                FROM assignments;
            """)
            cursor.execute("DROP TABLE assignments;")
            cursor.execute("ALTER TABLE assignments_new RENAME TO assignments;")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignments_student_due ON assignments(student_id, due_date);")
            cursor.execute("PRAGMA foreign_keys = ON;")
        except sqlite3.Error as e:
            logger.warning(f"Assignments table migration note: {e}")

    # 3. Create exams table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER,
            title TEXT NOT NULL,
            exam_date DATE NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exams_student_date ON exams(student_id, exam_date);")

    # 4. Create study_preferences table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            weekday TEXT CHECK(weekday IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')) NOT NULL,
            available_hours REAL NOT NULL CHECK(available_hours >= 0.0 AND available_hours <= 12.0),
            UNIQUE(student_id, weekday),
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
        );
    """)

    # 5. Create chat_sessions and chat_messages tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            student_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'Chat Session',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            student_id INTEGER NOT NULL,
            role TEXT CHECK(role IN ('user', 'assistant')) NOT NULL,
            content TEXT NOT NULL,
            action_executed TEXT,
            tool_trace TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_student ON chat_sessions(student_id, updated_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_student ON chat_messages(student_id);")

    conn.commit()


def init_db():
    """Initializes the database schema if tables do not exist and runs migrations."""
    db_path = Config.DATABASE_PATH
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(base_dir, 'schema.sql')
    
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema SQL file not found at: {schema_path}")
        
    conn = get_db_connection()
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        run_migrations(conn)
        conn.commit()
        logger.info("Database schema initialized and migrations applied successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise e
    finally:
        conn.close()
