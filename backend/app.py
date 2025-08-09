# backend/app.py
import sqlite3
import time
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import os
import hmac
import hashlib
from urllib.parse import parse_qs

app = Flask(__name__)
CORS(app, supports_credentials=True)

DATABASE = os.path.join(os.path.dirname(__file__), 'data.db')
BOT_TOKEN = os.environ.get('TG_BOT_TOKEN')

# DB helper functions
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE, check_same_thread=False)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with open(os.path.join(os.path.dirname(__file__), 'db_init.sql')) as f:
            db.executescript(f.read())
        db.commit()

if not os.path.exists(DATABASE):
    init_db()

def get_or_create_user(telegram_id):
    db = get_db()
    cur = db.execute('SELECT * FROM users WHERE telegram_id=?', (telegram_id,))
    row = cur.fetchone()
    if row:
        return row
    db.execute('INSERT INTO users(telegram_id, points, last_tap) VALUES(?,?,?)', (telegram_id, 0, 0))
    db.commit()
    cur = db.execute('SELECT * FROM users WHERE telegram_id=?', (telegram_id,))
    return cur.fetchone()

# Rate limiting params
MIN_INTERVAL_MS = 200  # minimum ms between taps
POINTS_PER_TAP = 1

# Telegram init_data verification function
def verify_telegram_init_data(init_data: str, bot_token: str) -> bool:
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    # Parse key=value pairs excluding 'hash'
    data_params = dict(pair.split('=') for pair in init_data.split('&') if not pair.startswith('hash'))
    sorted_items = sorted(data_params.items())
    data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted_items)

    hmac_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    qs = parse_qs(init_data)
    received_hash = qs.get('hash', [None])[0]

    return hmac_hash == received_hash

@app.route('/api/tap', methods=['POST'])
def tap():
    data = request.get_json() or {}

    init_data = data.get('init_data')
    if not init_data:
        return jsonify({'error': 'missing init_data'}), 400

    if not BOT_TOKEN:
        return jsonify({'error': 'server misconfiguration, missing BOT_TOKEN'}), 500

    if not verify_telegram_init_data(init_data, BOT_TOKEN):
        return jsonify({'error': 'invalid init_data signature'}), 403

    # Parse telegram_id from init_data
    parsed = dict(pair.split('=') for pair in init_data.split('&'))
    telegram_id = parsed.get('user.id')
    if not telegram_id:
        # try alternate key or error
        return jsonify({'error': 'telegram_id not found in init_data'}), 400

    now_ms = int(time.time() * 1000)

    user = get_or_create_user(telegram_id)
    last_tap = user['last_tap'] or 0
    if now_ms - last_tap < MIN_INTERVAL_MS:
        return jsonify({'error': 'rate_limited', 'retry_after_ms': MIN_INTERVAL_MS - (now_ms - last_tap)}), 429

    # Update points and last_tap
    db = get_db()
    new_points = user['points'] + POINTS_PER_TAP
    db.execute('UPDATE users SET points=?, last_tap=? WHERE telegram_id=?', (new_points, now_ms, telegram_id))
    db.execute('INSERT INTO taps(telegram_id, ts, count) VALUES(?,?,?)', (telegram_id, now_ms, 1))
    db.commit()

    return jsonify({'points': new_points})

@app.route('/api/balance', methods=['GET'])
def balance():
    telegram_id = request.args.get('telegram_id')
    if not telegram_id:
        return jsonify({'error': 'missing telegram_id'}), 400
    db = get_db()
    cur = db.execute('SELECT points FROM users WHERE telegram_id=?', (telegram_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({'points': 0})
    return jsonify({'points': row['points']})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
