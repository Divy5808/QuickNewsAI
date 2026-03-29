import psycopg2
import os
import urllib.parse as urlparse

import socket

def resolve_to_ipv4(host):
    """Force resolution to IPv4 to avoid IPv6 issues on some cloud platforms."""
    try:
        # Get all address info for the host
        addr_info = socket.getaddrinfo(host, None, socket.AF_INET)
        if addr_info:
            res = addr_info[0][4][0]
            print(f"✅ Resolved {host} to IPv4: {res}", flush=True)
            return res
    except Exception as e:
        print(f"⚠️ IPv4 Resolution failed for {host}: {e}. Falling back to hostname.", flush=True)
    return host

# Connect to database using configuration or DATABASE_URL environment variable
# Use PostgreSQL as requested for the project/thesis
def get_connection():
    # Check for ANY environment variables that start with DB_
    found_db_vars = [k for k in os.environ.keys() if k.startswith("DB_")]
    print(f"📊 DEBUG: Environment variables found starting with 'DB_': {found_db_vars}", flush=True)

    # Priority 1: Individual Components (Most Reliable for Hugging Face)
    db_host = os.environ.get("DB_HOST")
    db_user = os.environ.get("DB_USER")
    db_pass = os.environ.get("DB_PASS")
    db_port = os.environ.get("DB_PORT", "6543")
    db_name = os.environ.get("DB_NAME", "postgres")

    # Diagnostic: Print status of required components
    print(f"🔍 DB Status Check: HOST={'✅' if db_host else '❌'}, USER={'✅' if db_user else '❌'}, PASS={'✅' if db_pass else '❌'}", flush=True)

    if db_host and db_user and db_pass:
        # Force IPv4 resolution to avoid "Network is unreachable" issues on some IPv6-resolving DNS
        ipv4_host = resolve_to_ipv4(db_host)
        try:
            print(f"🔄 Attempting DB connection to {db_host} ({ipv4_host}):{db_port} as {db_user} (SSL Require)...")
            return psycopg2.connect(
                host=ipv4_host,
                port=db_port,
                user=db_user,
                password=db_pass,
                dbname=db_name,
                connect_timeout=15,
                sslmode='require'
            )
        except Exception as e:
            print(f"❌ Component Connection Failed: {str(e)}", flush=True)
            
            # Specific hint for Supabase Pooler "Tenant or user not found"
            if "Tenant or user not found" in str(e):
                print("🚨 CRITICAL: Supabase Pooler requires the username format 'postgres.[project-id]'.")
                print(f"🔍 Current USER is '{db_user}'. Change it to 'postgres.bwjatqxxgvkkdlkzbtwg' in Settings.")
            
            if "5432" in str(db_port):
                print("💡 TIP: If using Supabase Pooler, ensure port 6543 is used.")
            
            # If components are provided but fail, don't fall back to localhost silently
            if os.environ.get("SPACE_ID") or os.environ.get("HF_TOKEN"):
                print("🛑 Cloud connection failed. Please verify your DB credentials on HuggingFace Settings.")
                raise e
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
                port=url.port or 5432,
                sslmode='require'
            )
        except Exception as e:
            print(f"❌ DATABASE_URL Connection Failed: {e}")
            try:
                # Add sslmode if not present in URI
                if "sslmode=" not in db_url:
                    sep = "&" if "?" in db_url else "?"
                    db_url_ssl = f"{db_url}{sep}sslmode=require"
                else:
                    db_url_ssl = db_url
                    
                return psycopg2.connect(db_url_ssl)
            except Exception as last_e:
                print(f"❌ Direct URI fallback failed: {last_e}")
                if os.environ.get("SPACE_ID"):
                    raise last_e
    
    # Priority 3: Local Dev Config (ONLY if not on Spaces)
    if not os.environ.get("SPACE_ID"):
        print("🏠 Running locally, using default local config...")
        db_config = {"dbname": "quicknews", "user": "postgres", "password": "123", "host": "localhost", "port": "5432"}
        return psycopg2.connect(**db_config)
    else:
        raise Exception("❌ Database configuration missing or invalid for cloud environment (Spaces).")

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
