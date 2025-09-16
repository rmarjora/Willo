from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import pipeline
import numpy as np

model = SentenceTransformer('paraphrase-mpnet-base-v2')

def correlate_responses(responses):
    """
    Input: list of lists of responses to each question
    Correlate two sets of responses using a simple similarity metric using a sentence tranformer
    """

    # Encode polarity as a numeric score (-1 to 1)
    def sentiment_score(s):
        return s['score'] if s['label'] == 'POSITIVE' else -s['score']

    similarity_matrices = []
    for responseList in responses:
        embeddings = model.encode(responseList, normalize_embeddings=True)
        
        print('embeddings shape:', embeddings.shape)

        # Each column in similarity matrix corresponds to a single user's correlations with other user's responses to the same question
        similarity_matrix = cosine_similarity(embeddings)

        print('similarity matrix:', similarity_matrix)

        similarity_matrices.append(similarity_matrix)

    return similarity_matrices

def test_correlate_responses():
    responses1 = [
        "Hiking",
        "Swimming",
        "Solving crosswords",
        "Hunting",
        "Programming",
        "Full stack development",
        "Wandering in nature"
    ]

    responses2 = [
        "Coding is my passion.",
        "I prefer JavaScript for web development.",
        "Debugging is part of the fun."
    ]

    similarity_matrices = correlate_responses([responses1, responses2])

    for i, matrix in enumerate(similarity_matrices):
        print(f"Similarity Matrix for Response Set {i+1}:\n{matrix}\n")


if __name__ == "__main__":
    test_correlate_responses()