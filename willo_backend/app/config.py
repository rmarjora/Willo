import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "mydatabase"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "")
}

# Flask configuration
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))

# CORS configuration: comma-separated list of origins or '*' for all
_origins_raw = os.getenv("ALLOWED_ORIGINS", "*").strip()
if _origins_raw == '*':
    ALLOWED_ORIGINS = '*'
else:
    # Filter out empty fragments after splitting
    ALLOWED_ORIGINS = [o.strip() for o in _origins_raw.split(',') if o.strip()]