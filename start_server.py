import subprocess
import sys

if __name__ == "__main__":
    # Initialize the database
    print("[INFO] Initializing database...")
    subprocess.run([sys.executable, "willo_backend/init_db.py"], check=True)
    print("[INFO] Starting Flask server...")
    subprocess.run([sys.executable, "willo_backend/server.py"])