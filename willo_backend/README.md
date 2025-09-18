# Willo Backend

## Overview
Flask + Waitress backend with PostgreSQL persistence. Database is initialized with placeholder data on each start (idempotent) for convenience during development.

## Running the Server
```powershell
python start_server.py
```
This will:
1. Initialize (and idempotently seed) the database.
2. Create the Flask application.
3. Run the Waitress WSGI server in the same process.

Visit: http://localhost:5000

## Graceful Shutdown (Ctrl+C)
Previously `start_server.py` spawned a child process using `subprocess.run` to start the server module. On Windows this caused the parent process to receive the Ctrl+C (`SIGINT`) while the child (hosting Waitress) sometimes continued running, making it appear that Ctrl+C "stopped working".

The startup logic has been refactored so the server now runs in-process. Explicit signal handlers for `SIGINT` and `SIGTERM` perform a clean shutdown:
- Close the shared database connection (`app.db_conn`) if open.
- Exit the process with code 0.

If you press Ctrl+C you should now see a shutdown message immediately.

## Database Connection
A single PostgreSQL connection is opened eagerly during app creation (instead of using the removed `before_first_request` decorator from older Flask versions). If the connection fails, routes relying on it will return errors until the backend is restarted with a working database.

## Environment Configuration
Environment variables are loaded from `.env` (see `app/config.py`). Defaults are provided for local development.

## Future Improvements
- Connection pooling (e.g. `psycopg2.pool.SimpleConnectionPool`) for better concurrency.
- Robust migration handling instead of ad-hoc initialization.
- Per-request DB cursors with automatic rollback on errors.

## Python Version & PyTorch Note
Clustering uses `sentence-transformers` which depends on PyTorch. PyTorch wheels typically lag behind brand new Python releases. If you see an error like:

```
cannot import name 'Tensor' from 'torch' (unknown location)
```

you are likely running on an unsupported Python version (e.g. Python 3.13 before official wheels). Fix:

1. Install / use Python 3.12 (recommended).
2. Create a fresh virtual environment.
3. Reinstall requirements.

PowerShell example:
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

Then retry the clustering endpoint / task.

## API (Selected Endpoints)

### Create a Form
`POST /forms`

Request JSON:
```json
{
	"title": "Event Registration",
	"description": "Pre-event survey",
	"created_by": 1,
	"questions": [
		{"question_text": "How are you?", "allow_open_responses": true},
		{"question_text": "Favorite color?", "allow_open_responses": false, "choices": ["Red", "Blue"]}
	]
}
```

Response 201 JSON:
```json
{
	"id": 12,
	"title": "Event Registration",
	"description": "Pre-event survey",
	"created_at": "2025-09-16T09:30:21.123456",
	"questions": [
		{"id": 41, "question_text": "How are you?", "allow_open_responses": true, "choices": []},
		{"id": 42, "question_text": "Favorite color?", "allow_open_responses": false, "choices": [
			{"id": 77, "choice_text": "Red"},
			{"id": 78, "choice_text": "Blue"}
		]}
	]
}
```

Error codes:
- `400` missing required `title` or malformed question objects
- `500` database failure

