import numpy as np
import psycopg2
from psycopg2.extras import execute_batch
from app.config import DB_CONFIG

# Use scikit-learn TF-IDF to avoid torch dependency
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def _correlate_responses(responses):
    """
    Input: list of lists of responses to each question (shape: questions x users)
    Return list of similarity matrices (one per question), computed via TF-IDF + cosine similarity.
    Empty responses get zeroed out so they don't contribute.
    """
    similarity_matrices = []
    for response_list in responses:
        # Normalize and track empty entries
        response_list = [(r or '').strip() for r in response_list]
        no_response_idx = [i for i, r in enumerate(response_list) if r == '']

        if len(response_list) == 0:
            similarity_matrices.append(np.zeros((0, 0), dtype=float))
            continue

        # Vectorize using TF-IDF; use character + word analyzer for short texts robustness
        if all(text == '' for text in response_list):
            # All empty: zero matrix
            sim = np.zeros((len(response_list), len(response_list)), dtype=float)
            similarity_matrices.append(sim)
            continue

        vectorizer = TfidfVectorizer(analyzer='word', ngram_range=(1, 2), min_df=1)
        try:
            X = vectorizer.fit_transform(response_list)
        except ValueError:
            # Rare case: no valid features (e.g., only stopwords). Treat as zeros
            sim = np.zeros((len(response_list), len(response_list)), dtype=float)
            similarity_matrices.append(sim)
            continue

        sim = cosine_similarity(X)

        # Zero out similarities for no responses
        for idx in no_response_idx:
            sim[idx, :] = 0.0
            sim[:, idx] = 0.0

        similarity_matrices.append(sim)

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


def _save_similarity_scores(form_id: int, user_ids: list[int], overall_similarity: np.ndarray) -> int:
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
            rows.append((form_id, u1, u2, score))

    if not rows:
        return 0

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            execute_batch(
                cur,
                (
                    """
                    INSERT INTO matches (form_id, user_id_1, user_id_2, score)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id_1, user_id_2)
                    DO UPDATE SET score = EXCLUDED.score, form_id = EXCLUDED.form_id;
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
    overall_similarity = np.sum(similarity_matrices, axis=0)

    # Persist pairwise similarity scores
    upserted = _save_similarity_scores(form_id, user_ids, overall_similarity)
    print(f"Upserted {upserted} match rows for form_id={form_id}")

    # Build a simple result: top 5 matches per user
    top_matches = {}
    if len(user_ids) > 1:
        for i, uid in enumerate(user_ids):
            # score to others (exclude self)
            scores = []
            for j, other_uid in enumerate(user_ids):
                if i == j:
                    continue
                scores.append((other_uid, float(overall_similarity[i, j])))
            # sort descending by score
            scores.sort(key=lambda x: x[1], reverse=True)
            top_matches[uid] = scores[:5]
    else:
        top_matches = {user_ids[0]: []} if user_ids else {}

    return top_matches