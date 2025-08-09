from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_NAME = "users.db"

# ডাটাবেস তৈরি
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    balance INTEGER DEFAULT 0,
                    last_mine TEXT
                )''')
    conn.commit()
    conn.close()

init_db()

# মাইনিং ফাংশন
@app.route('/mine', methods=['POST'])
def mine():
    username = request.json.get("username")
    if not username:
        return jsonify({"error": "Username required"}), 400

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # ইউজার চেক
    c.execute("SELECT balance, last_mine FROM users WHERE username=?", (username,))
    user = c.fetchone()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if user:
        # আগের থেকে আছে, তাহলে ব্যালেন্স +1
        new_balance = user[0] + 1
        c.execute("UPDATE users SET balance=?, last_mine=? WHERE username=?", (new_balance, now, username))
    else:
        # নতুন ইউজার
        c.execute("INSERT INTO users (username, balance, last_mine) VALUES (?, ?, ?)", (username, 1, now))

    conn.commit()
    conn.close()

    return jsonify({"message": "Mined successfully", "username": username, "new_balance": user[0] + 1 if user else 1})

# ব্যালেন্স চেক
@app.route('/balance/<username>', methods=['GET'])
def balance(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()

    if user:
        return jsonify({"username": username, "balance": user[0]})
    else:
        return jsonify({"username": username, "balance": 0})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
