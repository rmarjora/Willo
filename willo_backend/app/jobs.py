"""Simple background job system for asynchronous clustering.

Uses a single worker thread and an in-memory queue. This is intentionally
minimal (no persistence, no retry/backoff) and suitable for a single-process
Flask deployment. If you scale to multiple processes or machines, replace with
something like RQ / Celery / Dramatiq + Redis.
"""
from __future__ import annotations

import threading
import queue
import time
import traceback
from typing import Callable, Any
import psycopg2

from app.cluster import compute_cluster_matches, ClusteringDependencyError
from app.config import DB_CONFIG

# Public states for a form's clustering background task
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_FAILED = "failed"
STATUS_COMPLETED = "completed"

# In-memory registry of clustering job status by form_id
_job_status: dict[int, dict[str, Any]] = {}
_status_lock = threading.Lock()

# Work queue items are callables that perform the job
_work_q: "queue.Queue[Callable[[], None]]" = queue.Queue()

_worker_started = False
_worker_lock = threading.Lock()


def _set_status(form_id: int, state: str, error: str | None = None):
    with _status_lock:
        _job_status[form_id] = {
            "state": state,
            "error": error,
            "updated_at": time.time(),
        }


def get_clustering_status(form_id: int) -> dict[str, Any] | None:
    """Return current clustering job status for a form (or None if never enqueued)."""
    with _status_lock:
        return _job_status.get(form_id)


def _worker_loop():
    while True:
        fn = _work_q.get()
        if fn is None:  # sentinel for shutdown (not currently used)
            break
        try:
            fn()
        except Exception:
            traceback.print_exc()
        finally:
            _work_q.task_done()


def _ensure_worker():
    global _worker_started
    if _worker_started:
        return
    with _worker_lock:
        if _worker_started:
            return
        t = threading.Thread(target=_worker_loop, name="clustering-worker", daemon=True)
        t.start()
        _worker_started = True


def enqueue_clustering(form_id: int) -> bool:
    """Enqueue a clustering job for the given form.

    Returns False if a job is already pending/running/completed for that form,
    True if a new job was enqueued. (Idempotent: won't enqueue duplicates.)
    """
    with _status_lock:
        existing = _job_status.get(form_id)
        if existing and existing["state"] in {STATUS_PENDING, STATUS_RUNNING, STATUS_COMPLETED}:
            return False  # Don't enqueue duplicate
        _job_status[form_id] = {"state": STATUS_PENDING, "error": None, "updated_at": time.time()}

    def _job():  # closure capturing form_id
        _set_status(form_id, STATUS_RUNNING)
        try:
            # Fetch responses from DB (duplicated logic to avoid Flask app context dependency)
            conn = psycopg2.connect(**DB_CONFIG)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT r.user_id, r.question_id, COALESCE(r.response_text, '')
                        FROM responses r
                        JOIN questions q ON q.id = r.question_id
                        WHERE q.form_id = %s
                        ORDER BY r.user_id, r.question_id;
                        """,
                        (form_id,),
                    )
                    rows = cur.fetchall()
                data: dict[int, dict[int, str]] = {}
                for user_id, question_id, response_text in rows:
                    data.setdefault(user_id, {})[question_id] = response_text or ""
            finally:
                conn.close()

            # Run clustering
            try:
                compute_cluster_matches(form_id, data)
            except ClusteringDependencyError as cde:
                _set_status(form_id, STATUS_FAILED, str(cde))
                return
            except Exception as e:  # catch-all; mark failed
                _set_status(form_id, STATUS_FAILED, f"Unexpected error: {e!r}")
                return

            _set_status(form_id, STATUS_COMPLETED)
        except Exception as outer:
            _set_status(form_id, STATUS_FAILED, f"Fatal job wrapper failure: {outer!r}")

    _ensure_worker()
    _work_q.put(_job)
    return True

__all__ = [
    "enqueue_clustering",
    "get_clustering_status",
    "STATUS_PENDING",
    "STATUS_RUNNING",
    "STATUS_FAILED",
    "STATUS_COMPLETED",
]
