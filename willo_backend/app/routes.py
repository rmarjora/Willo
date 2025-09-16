from flask import Blueprint, request, jsonify, g
import psycopg2
from app.config import DB_CONFIG

routes_bp = Blueprint('routes', __name__)

def get_db():
    from flask import current_app
    return getattr(current_app, 'db_conn', None)


def _fetch_form_questions_with_choices(cur, form_id):
    """Internal helper to fetch all questions (and their choices) for a form.

    Returns list of dicts: { id, question_text, allow_open_responses, choices: [ {id, choice_text} ] }
    Performs two queries to avoid N+1 pattern.
    """
    cur.execute(
        """
        SELECT q.id, q.question_text, q.allow_open_responses
        FROM questions q
        WHERE q.form_id = %s
        ORDER BY q.id;
        """,
        (form_id,)
    )
    question_rows = cur.fetchall()
    if not question_rows:
        return []
    question_ids = [r[0] for r in question_rows]
    cur.execute(
        """
        SELECT c.id, c.question_id, c.choice_text
        FROM choices c
        WHERE c.question_id = ANY(%s)
        ORDER BY c.id;
        """,
        (question_ids,)
    )
    choices_map = {qid: [] for qid in question_ids}
    for cid, qid, ctext in cur.fetchall():
        choices_map[qid].append({"id": cid, "choice_text": ctext})
    return [
        {
            "id": r[0],
            "question_text": r[1],
            "allow_open_responses": r[2],
            "choices": choices_map.get(r[0], [])
        }
        for r in question_rows
    ]

@routes_bp.route('/submit', methods=['POST'])
def submit_response_legacy():
    """Deprecated submission endpoint.

    Use POST /forms/<form_id>/responses instead.
    """
    return (
        jsonify({
            "error": "Deprecated endpoint. Use form-scoped submission.",
            "use": "/forms/<form_id>/responses"
        }),
        410,
    )


@routes_bp.route('/forms/<int:form_id>/responses', methods=['POST'])
def submit_form_responses(form_id):
    """Submit user responses for a specific form.

    Expected JSON body:
    {
        "name": "Alice",                # required
        "email": "alice@example.com",  # optional (unique)
        "responses": {                  # required
            "12": "Blue",             # question_id -> response_text (string)
            "13": "Yes"               
        }
    }

    Validation steps:
    - Ensure form exists.
    - Ensure responses dict present and non-empty.
    - Convert question_id keys to integers; reject invalid ids.
    - Ensure all question_ids belong to the form (return invalid ids list if not).
    - Insert user (upsert by email if provided) then insert responses.
    - Enforce UNIQUE(question_id,user_id); duplicate answer attempt returns 409.
    """
    data = request.get_json(silent=True) or {}
    name = data.get('name')
    email = data.get('email')
    responses_map = data.get('responses')

    if not name or not isinstance(responses_map, dict) or not responses_map:
        return jsonify({"error": "Missing required fields: name and non-empty responses dict"}), 400

    # Normalize & validate question ids
    try:
        question_ids = [int(k) for k in responses_map.keys()]
    except (ValueError, TypeError):
        return jsonify({"error": "All response keys must be integer question IDs"}), 400

    conn = get_db()
    if conn is None:
        return jsonify({"error": "Database connection not available"}), 500

    try:
        with conn.cursor() as cur:
            # Verify form
            cur.execute("SELECT 1 FROM forms WHERE id = %s;", (form_id,))
            if cur.fetchone() is None:
                return jsonify({"error": "Form not found"}), 404

            # Fetch valid questions for form
            cur.execute(
                "SELECT id FROM questions WHERE form_id = %s AND id = ANY(%s);",
                (form_id, question_ids)
            )
            valid_ids = {row[0] for row in cur.fetchall()}
            invalid_ids = [qid for qid in question_ids if qid not in valid_ids]
            if invalid_ids:
                return jsonify({
                    "error": "Some question IDs do not belong to this form",
                    "invalid_question_ids": invalid_ids
                }), 400

            # Insert or upsert user
            if email:
                # Try to insert; on conflict update name (optional) then return id
                cur.execute(
                    """
                    INSERT INTO users (name, email)
                    VALUES (%s, %s)
                    ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id;
                    """,
                    (name, email)
                )
            else:
                cur.execute(
                    "INSERT INTO users (name) VALUES (%s) RETURNING id;",
                    (name,)
                )
            user_id = cur.fetchone()[0]

            # Insert responses
            inserted = []
            for qid, resp_text in responses_map.items():
                qid_int = int(qid)
                if resp_text is None or (isinstance(resp_text, str) and resp_text.strip() == ""):
                    continue  # skip empty answers silently (or choose to error)
                try:
                    cur.execute(
                        """
                        INSERT INTO responses (question_id, user_id, response_text)
                        VALUES (%s, %s, %s)
                        RETURNING id, created_at;
                        """,
                        (qid_int, user_id, resp_text)
                    )
                    rid, created_at = cur.fetchone()
                    inserted.append({
                        "response_id": rid,
                        "question_id": qid_int,
                        "response_text": resp_text,
                        "created_at": created_at.isoformat() if hasattr(created_at, 'isoformat') else created_at
                    })
                except psycopg2.errors.UniqueViolation:  # type: ignore
                    conn.rollback()
                    return jsonify({
                        "error": "Duplicate response for question by this user",
                        "question_id": qid_int
                    }), 409

        conn.commit()
        return jsonify({
            "message": "Responses submitted successfully",
            "user_id": user_id,
            "inserted": inserted,
            "skipped_empty": [int(q) for q, v in responses_map.items() if not v]
        }), 201
    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

@routes_bp.route('/questions', methods=['GET', 'POST', 'DELETE', 'PUT'])
def questions_legacy():
    """Deprecated endpoint.

    This route is deprecated in favor of form-scoped routes:
      - GET/POST /forms/<form_id>/questions
      - GET/PUT/DELETE /forms/<form_id>/questions/<question_id>

    For backward compatibility, a 410 Gone status is returned with guidance.
    """
    return (
        jsonify({
            "error": "Deprecated endpoint. Use form-scoped endpoints.",
            "use_endpoints": {
                "list_or_create": "/forms/<form_id>/questions",
                "detail": "/forms/<form_id>/questions/<question_id>"
            }
        }),
        410,
    )

@routes_bp.route('/clear', methods=['POST'])
def clear_data():
    '''
    Clears all data in the database
    '''
    data = request.get_json()
    
    print('Clearing all data in the database...')

    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM responses;")
            cur.execute("DELETE FROM users;")
            cur.execute("DELETE FROM questions;")
        conn.commit()
        return jsonify({"message": "All data cleared."}), 200
    except psycopg2.Error as e:
        return jsonify({"error": str(e)}), 500


@routes_bp.route('/forms', methods=['POST'])
def create_form():
    """Create a new form (and optionally its questions).

    Expected JSON body:
    {
        "title": "Event Registration",
        "questions": [                                # optional array
            {"question_text": "How are you?", "allow_open_responses": true},
            {"question_text": "Favorite color?", "allow_open_responses": false, "choices": ["Red", "Blue"]}
        ]
    }

    Behavior:
    - Inserts a row into forms.
    - If questions provided, inserts each into questions with form_id.
    - If a question includes a non-empty choices list AND allow_open_responses is false (or omitted), creates choices rows.
    - All operations execute in a single transaction; any failure rolls back.
    """
    data = request.get_json(silent=True) or {}
    title = data.get('title')
    questions = data.get('questions', []) or []

    if not title:
        return jsonify({"error": "Missing required field: title"}), 400

    conn = get_db()
    if conn is None:
        return jsonify({"error": "Database connection not available"}), 500

    try:
        with conn.cursor() as cur:
            # Insert form
            cur.execute(
                """
                INSERT INTO forms (title)
                VALUES (%s)
                RETURNING id, created_at;
                """,
                (title,)
            )
            form_id, created_at = cur.fetchone()

            created_questions = []
            for q in questions:
                q_text = q.get('question_text') if isinstance(q, dict) else None
                if not q_text:
                    raise ValueError("Each question must have question_text")
                allow_open = q.get('allow_open_responses', True)
                cur.execute(
                    """
                    INSERT INTO questions (form_id, question_text, allow_open_responses)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (form_id, q_text, allow_open)
                )
                question_id = cur.fetchone()[0]
                # Insert choices if provided
                choices = q.get('choices') if isinstance(q, dict) else None
                created_choices = []
                if choices and isinstance(choices, list):
                    for choice_text in choices:
                        if not choice_text:
                            continue
                        cur.execute(
                            """
                            INSERT INTO choices (question_id, choice_text)
                            VALUES (%s, %s)
                            RETURNING id;
                            """,
                            (question_id, choice_text)
                        )
                        choice_id = cur.fetchone()[0]
                        created_choices.append({"id": choice_id, "choice_text": choice_text})
                created_questions.append({
                    "id": question_id,
                    "question_text": q_text,
                    "allow_open_responses": allow_open,
                    "choices": created_choices
                })

        conn.commit()
        return jsonify({
            "id": form_id,
            "title": title,
            "created_at": created_at.isoformat() if hasattr(created_at, 'isoformat') else created_at,
            "questions": created_questions
        }), 201
    except ValueError as ve:
        conn.rollback()
        return jsonify({"error": str(ve)}), 400
    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500


@routes_bp.route('/forms/<int:form_id>', methods=['DELETE'])
def delete_form(form_id):
    """Delete a form and all dependent data (questions, choices, responses) via ON DELETE CASCADE.

    Response:
    200 { "message": "Form deleted", "form_id": <id>, "deleted": {"forms":1, "questions":N, "choices":M, "responses":R} }
    404 if form does not exist.

    Note: Because cascade happens automatically, we gather counts beforehand in a single transaction.
    """
    conn = get_db()
    if conn is None:
        return jsonify({"error": "Database connection not available"}), 500
    try:
        with conn.cursor() as cur:
            # Check form existence
            cur.execute("SELECT id FROM forms WHERE id = %s;", (form_id,))
            if cur.fetchone() is None:
                return jsonify({"error": "Form not found"}), 404
            # Count related rows
            cur.execute("SELECT COUNT(*) FROM questions WHERE form_id = %s;", (form_id,))
            q_count = cur.fetchone()[0]
            cur.execute(
                """
                SELECT COUNT(*) FROM choices c
                WHERE c.question_id IN (SELECT id FROM questions WHERE form_id = %s);
                """,
                (form_id,)
            )
            c_count = cur.fetchone()[0]
            cur.execute(
                """
                SELECT COUNT(*) FROM responses r
                WHERE r.question_id IN (SELECT id FROM questions WHERE form_id = %s);
                """,
                (form_id,)
            )
            r_count = cur.fetchone()[0]

            # Delete form (cascades)
            cur.execute("DELETE FROM forms WHERE id = %s;", (form_id,))
        conn.commit()
        return jsonify({
            "message": "Form deleted",
            "form_id": form_id,
            "deleted": {
                "forms": 1,
                "questions": q_count,
                "choices": c_count,
                "responses": r_count
            }
        }), 200
    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500


@routes_bp.route('/forms/<int:form_id>/questions', methods=['GET', 'POST'])
def form_questions(form_id):
    """List or create questions for a specific form.

    GET /forms/<form_id>/questions -> [ { id, question_text, allow_open_responses, choices: [ {id, choice_text} ] } ]
    POST body example:
    {
        "question_text": "Favorite color?",
        "allow_open_responses": false,
        "choices": ["Red", "Green", "Blue"]
    }
    """
    conn = get_db()
    if conn is None:
        return jsonify({"error": "Database connection not available"}), 500

    if request.method == 'GET':
        print('Received GET request for questions')
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM forms WHERE id = %s;", (form_id,))
                if cur.fetchone() is None:
                    return jsonify({"error": "Form not found"}), 404
                questions = _fetch_form_questions_with_choices(cur, form_id)
            return jsonify(questions), 200
        except psycopg2.Error as e:
            return jsonify({"error": str(e)}), 500

    # POST create question
    print('Received POST request for creating questions')
    data = request.get_json(silent=True) or {}
    q_text = data.get('question_text')
    allow_open = data.get('allow_open_responses', True)
    choices = data.get('choices') if isinstance(data, dict) else None
    if not q_text:
        return jsonify({"error": "Missing question_text"}), 400

    try:
        with conn.cursor() as cur:
            # Ensure form exists
            cur.execute("SELECT 1 FROM forms WHERE id = %s;", (form_id,))
            if cur.fetchone() is None:
                return jsonify({"error": "Form not found"}), 404
            cur.execute(
                """
                INSERT INTO questions (form_id, question_text, allow_open_responses)
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (form_id, q_text, allow_open)
            )
            question_id = cur.fetchone()[0]
            created_choices = []
            if choices and isinstance(choices, list):
                for choice_text in choices:
                    if not choice_text:
                        continue
                    cur.execute(
                        """
                        INSERT INTO choices (question_id, choice_text)
                        VALUES (%s, %s)
                        RETURNING id;
                        """,
                        (question_id, choice_text)
                    )
                    choice_id = cur.fetchone()[0]
                    created_choices.append({"id": choice_id, "choice_text": choice_text})
        conn.commit()
        return jsonify({
            "id": question_id,
            "question_text": q_text,
            "allow_open_responses": allow_open,
            "choices": created_choices
        }), 201
    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500


@routes_bp.route('/forms/<int:form_id>/questions/<int:question_id>', methods=['GET', 'PUT', 'DELETE'])
def form_question_detail(form_id, question_id):
    """Retrieve, update, or delete a specific question belonging to a form.

    GET -> { id, question_text, allow_open_responses, choices: [...] }
    PUT body allows updating question_text, allow_open_responses, and optionally replacing choices list:
    {
        "question_text": "Updated text",
        "allow_open_responses": true,
        "choices": ["New", "Choices"]      # If provided replaces existing choices
    }
    DELETE -> removes the question (and cascades to choices if FK cascade) otherwise manually deletes choices first.
    """
    conn = get_db()
    if conn is None:
        return jsonify({"error": "Database connection not available"}), 500

    try:
        with conn.cursor() as cur:
            # Verify form and question relationship
            cur.execute(
                """
                SELECT id, question_text, allow_open_responses
                FROM questions
                WHERE id = %s AND form_id = %s;
                """,
                (question_id, form_id)
            )
            row = cur.fetchone()
            if row is None:
                return jsonify({"error": "Question not found for this form"}), 404

            if request.method == 'GET':
                cur.execute(
                    "SELECT id, choice_text FROM choices WHERE question_id = %s ORDER BY id;",
                    (question_id,)
                )
                choices = [
                    {"id": c_id, "choice_text": c_text}
                    for c_id, c_text in cur.fetchall()
                ]
                return jsonify({
                    "id": row[0],
                    "question_text": row[1],
                    "allow_open_responses": row[2],
                    "choices": choices
                }), 200

            if request.method == 'DELETE':
                # Delete choices first if not ON DELETE CASCADE (safe approach)
                cur.execute("DELETE FROM choices WHERE question_id = %s;", (question_id,))
                cur.execute("DELETE FROM questions WHERE id = %s;", (question_id,))
                conn.commit()
                return jsonify({"message": "Question deleted"}), 200

            # PUT update
            data = request.get_json(silent=True) or {}
            new_text = data.get('question_text', row[1])
            new_allow = data.get('allow_open_responses', row[2])
            new_choices = data.get('choices', None)

            cur.execute(
                "UPDATE questions SET question_text = %s, allow_open_responses = %s WHERE id = %s;",
                (new_text, new_allow, question_id)
            )

            updated_choices = None
            if new_choices is not None:
                # Replace choices set
                cur.execute("DELETE FROM choices WHERE question_id = %s;", (question_id,))
                updated_choices = []
                for choice_text in new_choices:
                    if not choice_text:
                        continue
                    cur.execute(
                        """
                        INSERT INTO choices (question_id, choice_text)
                        VALUES (%s, %s)
                        RETURNING id;
                        """,
                        (question_id, choice_text)
                    )
                    cid = cur.fetchone()[0]
                    updated_choices.append({"id": cid, "choice_text": choice_text})
            else:
                # Fetch existing choices if not replaced
                cur.execute(
                    "SELECT id, choice_text FROM choices WHERE question_id = %s ORDER BY id;",
                    (question_id,)
                )
                updated_choices = [
                    {"id": c_id, "choice_text": c_text}
                    for c_id, c_text in cur.fetchall()
                ]

        conn.commit()
        return jsonify({
            "id": question_id,
            "question_text": new_text,
            "allow_open_responses": new_allow,
            "choices": updated_choices
        }), 200
    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
