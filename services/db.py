import psycopg2
import os
import urllib.parse as urlparse

# Connect to database using configuration or DATABASE_URL environment variable
# Use PostgreSQL as requested for the project/thesis
def get_connection():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        try:
            # We use urlparse to handle complex credentials
            url = urlparse.urlparse(db_url)
            print(f"Connecting to DB at {url.hostname}:{url.port} as {url.username}...")
            
            # Reconstruct parameters for psycopg2 to be more stable
            return psycopg2.connect(
                dbname=url.path[1:],
                user=url.username,
                password=url.password,
                host=url.hostname,
                port=url.port or 5432
            )
        except Exception as e:
            print(f"❌ DATABASE_URL Connection Failed: {e}")
            # Fallback to direct connect if parsing fails
            try:
                return psycopg2.connect(db_url)
            except:
                raise e
    
    # Priority 2: Standard local configuration (for development)
    db_config = {
        "dbname": "quicknews",
        "user": "postgres",
        "password": "123",
        "host": "localhost",
        "port": "5432"
    }
    return psycopg2.connect(**db_config)

def get_db_size():
    """Return the total size of the database in a human-readable format."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        # Query depends on actual DB name if using config, otherwise it uses the URL's db name
        cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        size = cur.fetchone()[0]
        cur.close()
        conn.close()
        return size
    except Exception as e:
        print(f"Error getting db size: {e}")
        return "Unknown"
