
from flask import Flask
from flask_cors import CORS
import psycopg2
from app.routes import routes_bp
from app.config import FLASK_HOST, FLASK_PORT, DB_CONFIG, ALLOWED_ORIGINS


def create_app():
    app = Flask(__name__)
    app.register_blueprint(routes_bp)

    # Enable CORS
    cors_kwargs = {
        'resources': {r"/*": {"origins": ALLOWED_ORIGINS}},
        'supports_credentials': True,
    }
    CORS(app, **cors_kwargs)

    try:
        app.db_conn = psycopg2.connect(**DB_CONFIG)
    except psycopg2.Error as e:
        # Defer hard failure; routes will raise if they attempt to use None.
        app.db_conn = None
        print(f"[ERROR] Failed to connect to database at startup: {e}")

    return app


app = create_app()

if __name__ == "__main__":
    # Use Waitress WSGI server for reliable signal handling
    from waitress import serve
    print(f"[INFO] Serving app on http://{FLASK_HOST}:{FLASK_PORT}")
    serve(app, host=FLASK_HOST, port=FLASK_PORT)
