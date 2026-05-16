import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from the .env file at the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

def verify_database():
    try:
        host = os.getenv("POSTGRES_HOST", "localhost")
        # Supabase requires SSL; local dev does not
        use_ssl = "supabase" in host.lower()

        # Establish the connection
        conn_params = dict(
            dbname=os.getenv("POSTGRES_DB", "postgres"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=host,
            port=os.getenv("POSTGRES_PORT", "5432"),
        )
        if use_ssl:
            conn_params["sslmode"] = "require"

        print(f"Connecting to {host}...")
        conn = psycopg2.connect(**conn_params)
        
        cur = conn.cursor()
        
        # 1. Verify basic connection
        cur.execute("SELECT version();")
        db_version = cur.fetchone()
        print(f"[OK] Connected successfully!\nPostgreSQL version: {db_version[0]}")
        
        # 2. Verify pgvector extension
        cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
        vector_version = cur.fetchone()
        
        if vector_version:
            print(f"[OK] pgvector is installed and active! (Version: {vector_version[0]})")
        else:
            print("[ERROR] pgvector is NOT active. Run 'CREATE EXTENSION vector;' in your SQL tool.")
        
        cur.close()
        conn.close()

    except Exception as e:
        print("[ERROR] Connection failed. Check your credentials and ensure Postgres is running.")
        print(f"Error details: {e}")

if __name__ == "__main__":
    verify_database()