import numpy as np
import psycopg2
from psycopg2.extras import execute_batch
from app.config import DB_CONFIG

# Lazy imports to avoid importing heavy ML libraries at app startup
_model = None

def _get_model():
    """
    Lazily load and cache the SentenceTransformer model. This avoids importing
    transformers/torch until we actually need them.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('paraphrase-mpnet-base-v2')
    return _model

def _correlate_responses(responses):
    """
    Input: list of lists of responses to each question
    Correlate two sets of responses using a simple similarity metric using a sentence tranformer
    """

    # Import here to avoid import-time failures if sklearn isn't installed at startup
    from sklearn.metrics.pairwise import cosine_similarity

    similarity_matrices = []
    for responseList in responses:
        responseList = [r.strip() for r in responseList]
        no_response_idx = [i for i, r in enumerate(responseList) if r == '']
        model = _get_model()
        embeddings = model.encode(responseList, batch_size=32, show_progress_bar=True, normalize_embeddings=True)
        
        print('embeddings shape:', embeddings.shape)

        # Each column in similarity matrix corresponds to a single user's correlations with other user's responses to the same question
        similarity_matrix = cosine_similarity(embeddings)
        
        # Zero out similarities for no responses
        for idx in no_response_idx:
            similarity_matrix[idx, :] = 0.0
            similarity_matrix[:, idx] = 0.0

        print('similarity matrix:', similarity_matrix)

        similarity_matrices.append(similarity_matrix)

    return similarity_matrices

def get_responses(form_id: int):
    """
    Fetch responses for a given form and return a nested mapping:
    { user_id: { question_id: response_text, ... }, ... }

    Only responses belonging to questions of the specified form are returned.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(
                (
                    """
                    SELECT r.user_id, r.question_id, COALESCE(r.response_text, '')
                    FROM responses r
                    INNER JOIN questions q ON q.id = r.question_id
                    WHERE q.form_id = %s
                    ORDER BY r.user_id, r.question_id;
                    """
                ),
                (form_id,),
            )
            rows = cur.fetchall()

        data = {}
        for user_id, question_id, response_text in rows:
            if user_id not in data:
                data[user_id] = {}
            data[user_id][question_id] = response_text or ""
        return data
    finally:
        conn.close()


def _save_similarity_scores(form_id: int, user_ids: list[int], question_ids: list[int], overall_similarity: np.ndarray, best_questions: np.ndarray) -> int:
    """
    Persist pairwise similarity scores into the matches table using upsert.
    Returns number of rows upserted.
    Note: The table has UNIQUE(user_id_1, user_id_2) so we order ids to respect uniqueness.
    """
    n = len(user_ids)
    if n == 0:
        return 0

    # Prepare rows for all ordered pairs (i != j) to store both directions; skip diagonal
    rows = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue  # skip self-pairs
            u1 = user_ids[i]
            u2 = user_ids[j]
            score = float(overall_similarity[i, j])
            best_question_id = question_ids[best_questions[i][j]]  # Get the question with the highest similarity
            rows.append((form_id, u1, u2, score, best_question_id))

    if not rows:
        return 0

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            execute_batch(
                cur,
                (
                    """
                    INSERT INTO matches (form_id, user_id_1, user_id_2, score, best_question_id)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id_1, user_id_2)
                    DO UPDATE SET score = EXCLUDED.score, form_id = EXCLUDED.form_id, best_question_id = EXCLUDED.best_question_id;
                    """
                ),
                rows,
                page_size=200,
            )
            
            # Mark form as clustered
            cur.execute("UPDATE forms SET clustered = TRUE WHERE id = %s;", (form_id,))
        conn.commit()
        return len(rows)
    finally:
        conn.close()

def compute_cluster_matches(form_id):
    '''
    Returns the top n people who match the given person_id based on correlated responses.
    '''
    
    data = get_responses(form_id)  # { user_id: { question_id: response_text } }
    user_ids = list(data.keys())
    print('user_ids:', user_ids)
    
    # There may be missing responses for some users, fill them with ""
    
    # Get all question IDs
    question_ids = set()
    for user_id in user_ids:
        question_ids.update(data[user_id].keys())
    
    # Get all responses in a consistent order
    question_ids = list(question_ids)
    responses = []
    for question_id in question_ids:
        question_responses = []
        for user_id in user_ids:
            question_responses.append(data[user_id].get(question_id, ""))
        responses.append(question_responses)

    similarity_matrices = _correlate_responses(responses)

    # Sum the similarity matrices to get an overall similarity score
    overall_similarity = (np.sum(similarity_matrices, axis=0) + len(similarity_matrices)) / (2 * len(similarity_matrices))  # map to [0, 1]
    
    # Get the best question for each pair
    best_questions = np.argmax(similarity_matrices, axis=0)

    # Persist pairwise similarity scores
    upserted = _save_similarity_scores(form_id, user_ids, question_ids, overall_similarity, best_questions)
    print(f"Upserted {upserted} match rows for form_id={form_id}")