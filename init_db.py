import psycopg2
from psycopg2 import sql

# ======================
# Configuration
# ======================
DB_CONFIG = {
    "host": "localhost",
    "database": "your_database_name",
    "user": "your_username",
    "password": "your_password",
    "port": 5432
}

# Sample placeholder data
PLACEHOLDER_QUESTIONS = [
    "Millä mielellä olet lähdössä tapahtumaan?",
    "Mikä on koulutustaustasi?",
    "Mikä on lempinimesi?",
    "Mitä aiot laittaa päällesi tapahtumassa?",
    "Millä kielellä puhut mieluiten?",
    "Kahvi vai viini?",
    "Mitä harrastat?",
    "Kiinnostaako astrologia?",
],

PLACEHOLDER_USERS = [
    "Alice",
    "Bob",
    "Charlie",
    "Diana",
    "Ethan"
]

PLACEHOLDER_RESPONSES_ALICE = [
    "Erittäin innoissani!",
    "Olen insinööri.",
    "Minua kutsutaan Ace.",
    "Pukeudun rentoon asuun.",
    "Suomea.",
    "Kahvi ehdottomasti.",
    "Rakastan maalaamista.",
    "Kyllä, se on kiehtovaa."
]

PLACEHOLDER_RESPONSES_BOB = [
    "Odotan innolla tapahtumaa.",
    "Olen taiteilija.",
    "Minua kutsutaan Bobo.",
    "Pukeudun muodikkaasti.",
    "Englanti.",
    "Viini on parempi.",
    "Pidän pyöräilystä.",
    "En ole kovin kiinnostunut."
]

def init_db():
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # ======================
        # 1. Create users table
        # ======================
        create_table_query = """
        CREATE TABLE IF NOT EXISTS questions (
            id SERIAL PRIMARY KEY,
            question TEXT NOT NULL,
        );
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS responses (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            question_id INTEGER REFERENCES questions(id),
            response TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cur.execute(create_table_query)
        conn.commit()

        insert_placeholderdata_query = """
        INSERT INTO questions (question) VALUES (%s) ON CONFLICT DO NOTHING;
        INSERT INTO users (name) VALUES (%s) ON CONFLICT DO NOTHING;
        INSERT INTO responses (user_id, question_id, response) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;
        """

        cur.executemany(insert_placeholderdata_query, [(q,) for q in PLACEHOLDER_QUESTIONS])
        cur.executemany(insert_placeholderdata_query, [(u,) for u in PLACEHOLDER_USERS])

        # Insert responses for Alice and Bob
        for idx, response in enumerate(PLACEHOLDER_RESPONSES_ALICE):
            cur.execute("INSERT INTO responses (user_id, question_id, response) VALUES (%s, %s, %s)", (1, idx+1, response))
        for idx, response in enumerate(PLACEHOLDER_RESPONSES_BOB):
            cur.execute("INSERT INTO responses (user_id, question_id, response) VALUES (%s, %s, %s)", (2, idx+1, response))
            
        conn.commit()
        print("[INFO] Database initialized and placeholder data inserted.")
        cur.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"[ERROR] PostgreSQL error: {e}")

if __name__ == "__main__":
    init_db()
