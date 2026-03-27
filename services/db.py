import sqlite3
import os

# Base directory for the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "news.db")

class SQLiteCursorWrapper:
    def __init__(self, cur):
        self.cur = cur

    def execute(self, query, params=None):
        # Convert PostgreSQL's %s to SQLite's ?
        query = query.replace("%s", "?")
        if params is not None:
            return self.cur.execute(query, params)
        return self.cur.execute(query)

    def fetchone(self): return self.cur.fetchone()
    def fetchall(self): return self.cur.fetchall()
    def close(self): self.cur.close()
    
    @property
    def rowcount(self): return self.cur.rowcount
    
    @property
    def description(self): return self.cur.description

class SQLiteConnWrapper:
    def __init__(self, conn):
        self.conn = conn
    
    def cursor(self):
        return SQLiteCursorWrapper(self.conn.cursor())
    
    def commit(self): self.conn.commit()
    def rollback(self): self.conn.rollback()
    def close(self): self.conn.close()

def get_connection():
    # Automatically creates news.db if it doesn't exist
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    # Enable WAL mode for better concurrency in SQLite web apps
    conn.execute("PRAGMA journal_mode=WAL")
    return SQLiteConnWrapper(conn)

def get_db_size():
    if os.path.exists(DB_PATH):
        size_bytes = os.path.getsize(DB_PATH)
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    return "0 KB"
