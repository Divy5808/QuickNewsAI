import psycopg2

DB_CONFIG = {
    "dbname": "quicknews",
    "user": "postgres",
    "password": "123",
    "host": "localhost",
    "port": "5432"
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_db_size():
    """Return the total size of the database in a human-readable format."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT pg_size_pretty(pg_database_size(%s))", (DB_CONFIG['dbname'],))
        size = cur.fetchone()[0]
        cur.close()
        conn.close()
        return size
    except:
        return "Unknown"
