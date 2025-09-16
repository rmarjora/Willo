"""Unified startup script.

Previously this script spawned a new Python process to run the server via
`subprocess.run([python, -m app.server])`. On some platforms (especially Windows)
that pattern can interfere with reliable Ctrl+C (SIGINT) handling because the
KeyboardInterrupt is raised in the parent process while the child (running Waitress)
continues to serve. That makes it appear that Ctrl+C “stops working”.

We now:
 1. Initialize the database in-process.
 2. Create the Flask application.
 3. Run Waitress directly in the same process.
 4. Install explicit signal handlers for SIGINT / SIGTERM for graceful shutdown.

This ensures a single process owns the console and receives Ctrl+C, allowing a
clean exit.
"""

import signal
import sys
from typing import Optional

from app.init_db import init_db
from app.server import create_app
from app.config import FLASK_HOST, FLASK_PORT

SHUTTING_DOWN = False


def _graceful_shutdown(app):
    global SHUTTING_DOWN
    if SHUTTING_DOWN:
        return
    SHUTTING_DOWN = True
    print("\n[INFO] Shutting down server...")
    # Close DB connection if it exists
    db = getattr(app, 'db_conn', None)
    if db is not None:
        try:
            db.close()
            print("[INFO] Database connection closed.")
        except Exception as e:  # pragma: no cover - defensive
            print(f"[WARN] Error closing DB connection: {e}")


def main():
    print("[INFO] Initializing database (idempotent)...")
    try:
        init_db()
    except Exception as e:  # pragma: no cover - we just report and continue
        print(f"[ERROR] Database initialization encountered an error: {e}")

    app = create_app()

    def handle_signal(signum, frame):
        _graceful_shutdown(app)
        # Exit after cleanup. Using sys.exit to raise SystemExit in main thread.
        sys.exit(0)

    # Register handlers (SIGTERM for container / service stop, SIGINT for Ctrl+C)
    for sig in (getattr(signal, 'SIGINT', None), getattr(signal, 'SIGTERM', None)):
        if sig is not None:
            try:
                signal.signal(sig, handle_signal)
            except Exception:  # pragma: no cover - some signals may not be settable on Windows
                pass

    from waitress import serve
    print(f"[INFO] Serving app on http://{FLASK_HOST}:{FLASK_PORT} (Press Ctrl+C to quit)")
    try:
        serve(app, host=FLASK_HOST, port=FLASK_PORT)
    except KeyboardInterrupt:
        handle_signal(signal.SIGINT if hasattr(signal, 'SIGINT') else 0, None)


if __name__ == "__main__":
    main()
