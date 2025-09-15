from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import sql

# ======================
# Configuration (reuse from init_db.py)
# ======================
DB_CONFIG = {
	"host": "localhost",
	"database": "your_database_name",
	"user": "your_username",
	"password": "your_password",
	"port": 5432
}

app = Flask(__name__)

@app.route('/submit_response', methods=['POST'])
def submit_response():
	data = request.get_json()
	user_id = data.get('user_id')
	question_id = data.get('question_id')
	response_text = data.get('response')

	if not all([user_id, question_id, response_text]):
		return jsonify({"error": "Missing required fields."}), 400

	try:
		conn = psycopg2.connect(**DB_CONFIG)
		cur = conn.cursor()
		insert_query = """
			INSERT INTO responses (user_id, question_id, response)
			VALUES (%s, %s, %s)
		"""
		cur.execute(insert_query, (user_id, question_id, response_text))
		conn.commit()
		cur.close()
		conn.close()
		return jsonify({"message": "Response submitted successfully."}), 201
	except psycopg2.Error as e:
		return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
	app.run(debug=True)