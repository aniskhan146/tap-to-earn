import os
import sqlite3
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv
import hmac
import hashlib
import json

# Load .env variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE = os.path.join(os.path.dirname(__file__), 'data.db')

app = Flask(__name__)
CORS(app, supports_credentials=True)

# ---------------------------
# Database Setup
# ---------------------------
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        telegram_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        points INTEGER DEFAULT 0,
                        joined_at TEXT
                    )''')
    conn.commit()
    conn.close()

init_db()

# ---------------------------
# Telegram Login Verification
# ---------------------------
def verify_telegram_auth(data):
    """Verify Telegram WebApp initData using HMAC-SHA256"""
    auth_data = {k: v for k, v in data.items() if k != 'hash'}
    sorted_data = "\n".join(f"{k}={v}" for k, v in sorted(auth_data.items()))
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    hash_check = hmac.new(secret_key, sorted_data.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(hash_check, data.get('hash'))

# ---------------------------
# Routes
# ---------------------------

@app.route('/auth', methods=['POST'])
def auth():
    init_data = request.json.get("initData", {})
    if not init_data or not verify_telegram_auth(init_data):
        return jsonify({"error": "Invalid Telegram authentication"}), 403

    telegram_id = int(init_data["id"])
    username = init_data.get("username", "")
    first_name = init_data.get("first_name", "")
    last_name = init_data.get("last_name", "")

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute(
            "INSERT INTO users (telegram_id, username, first_name, last_name, points, joined_at) VALUES (?, ?, ?, ?, ?, ?)",
            (telegram_id, username, first_name, last_name, 0, datetime.now().isoformat())
        )
        conn.commit()

    conn.close()
    return jsonify({"status": "ok", "telegram_id": telegram_id})

@app.route('/add_points', methods=['POST'])
def add_points():
    telegram_id = request.json.get("telegram_id")
    points = request.json.get("points", 0)

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET points = points + ? WHERE telegram_id = ?", (points, telegram_id))
    conn.commit()
    conn.close()

    return jsonify({"status": "points_added", "added": points})

@app.route('/get_points', methods=['GET'])
def get_points():
    telegram_id = request.args.get("telegram_id")

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT points FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({"points": row[0]})
    else:
        return jsonify({"error": "User not found"}), 404

# ---------------------------
# Run App
# ---------------------------
if __name__ == '__main__':
    app.run(debug=True)
