import psycopg2
from psycopg2 import OperationalError, errorcodes
from app.config import DB_CONFIG


def test_db_connection():
    print("[INFO] Testing PostgreSQL connection...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"[SUCCESS] Connected to PostgreSQL! Server version: {version[0]}")
        
        cur.close()
        conn.close()
        return True

    except OperationalError as e:
        if e.pgcode == errorcodes.INVALID_PASSWORD:
            print("[ERROR] Invalid password. Please check the password in app/config.py.")
        elif "authentication failed" in str(e).lower():
            print("[ERROR] Authentication failed. The username or password is incorrect.")
        elif "connection refused" in str(e).lower():
            print(
                "[ERROR] Could not connect to PostgreSQL: Connection refused.\n"
                "  - Ensure the PostgreSQL service is running.\n"
                "  - Verify the port is set to 5432 in postgresql.conf.\n"
                "  - Check pg_hba.conf for host authentication settings."
            )
        elif "does not exist" in str(e).lower():
            print("[ERROR] The specified database does not exist. Please create it in PostgreSQL.")
        else:
            print(f"[ERROR] Unexpected connection error: {e}")
        return False

    except Exception as e:
        print(f"[ERROR] General error: {e}")
        return False


if __name__ == "__main__":
    success = test_db_connection()
    if success:
        print("[INFO] Database test completed successfully.")
    else:
        print("[INFO] Database test failed. Please fix the above issues.")
