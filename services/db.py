import psycopg2
import os
import urllib.parse as urlparse

# Connect to database using configuration or DATABASE_URL environment variable
# Use PostgreSQL as requested for the project/thesis
def get_connection():
    # Check for ANY environment variables that start with DB_
    found_db_vars = [k for k in os.environ.keys() if k.startswith("DB_")]
    print(f"📊 DEBUG: Environment variables found starting with 'DB_': {found_db_vars}")

    # Priority 1: Individual Components (Most Reliable for Hugging Face)
    db_host = os.environ.get("DB_HOST")
    db_user = os.environ.get("DB_USER")
    db_pass = os.environ.get("DB_PASS")
    db_port = os.environ.get("DB_PORT", "6543")
    db_name = os.environ.get("DB_NAME", "postgres")

    # Diagnostic: Print status of required components
    print(f"🔍 DB Status Check: HOST={'✅' if db_host else '❌'}, USER={'✅' if db_user else '❌'}, PASS={'✅' if db_pass else '❌'}")

    if db_host and db_user and db_pass:
        try:
            print(f"🔄 Attempting DB connection to {db_host}:{db_port} as {db_user}...")
            return psycopg2.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_pass,
                dbname=db_name,
                connect_timeout=10
            )
        except Exception as e:
            print(f"❌ Component Connection Failed: {e}")
    else:
        print("💡 Skipping Component Connection (missing HOST/USER/PASS). Checking for DATABASE_URL...")

    # Priority 2: DATABASE_URL (Fallback)
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
            try:
                return psycopg2.connect(db_url)
            except Exception as last_e:
                print(f"❌ Direct URI fallback failed: {last_e}")
                raise last_e
    
    # Priority 3: Local Dev Config
    db_config = {"dbname": "quicknews", "user": "postgres", "password": "123", "host": "localhost", "port": "5432"}
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
