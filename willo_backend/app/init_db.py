import psycopg2
from psycopg2 import sql
from app.config import DB_CONFIG

def init_db():
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        create_table_query = """
        -- 1. Forms table: stores form metadata
        CREATE TABLE IF NOT EXISTS forms (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 2. Questions table: stores questions linked to forms
        CREATE TABLE IF NOT EXISTS questions (
            id SERIAL PRIMARY KEY,
            form_id INTEGER NOT NULL REFERENCES forms(id) ON DELETE CASCADE,
            question_text TEXT NOT NULL,
            allow_open_responses BOOLEAN DEFAULT TRUE
        );

        -- 3. Choices table: stores possible choices for multiple-choice questions
        CREATE TABLE IF NOT EXISTS choices (
            id SERIAL PRIMARY KEY,
            question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
            choice_text TEXT NOT NULL
        );

        -- 4. Users table: stores responders
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE -- optional, enforce unique responders
        );

        -- 5. Responses table: stores user answers
        CREATE TABLE IF NOT EXISTS responses (
            id SERIAL PRIMARY KEY,
            question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            response_text TEXT, -- text response or selected choice IDs as JSON/array
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(question_id, user_id) -- ensures a user can't answer same question twice
        );
        """
        cur.execute(create_table_query)
        conn.commit()
        cur.close()
        conn.close()

    except psycopg2.OperationalError as e:
        print(f"[ERROR] Could not connect to PostgreSQL: {e}")
        print("[HINT] Make sure your PostgreSQL server is running and accepting connections on localhost:5432.")
        print("        You can start PostgreSQL using its service manager or command line, depending on your installation.")
    except psycopg2.Error as e:
        print(f"[ERROR] PostgreSQL error: {e}")

if __name__ == "__main__":
    init_db()
