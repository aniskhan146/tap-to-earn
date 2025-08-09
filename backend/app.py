import sqlite3
import time
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import os
import json
import urllib.parse

DATABASE = os.path.join(os.path.dirname(__file__), 'data.db')

app = Flask(__name__)
CORS(app, supports_credentials=True)

# DB helper
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

def parse_telegram_init_data(init_data):
    try:
        params = dict(pair.split('=') for pair in init_data.split('&'))
        user_json = params.get('user')
        if user_json:
            user_json = urllib.parse.unquote(user_json)
            user_data = json.loads(user_json)
            return user_data
    except Exception as e:
        print("Failed to parse initData:", e)
    return {}

def get_or_create_user(telegram_data, platform='unknown'):
    telegram_id = telegram_data.get('id')
    username = telegram_data.get('username')
    first_name = telegram_data.get('first_name')
    last_name = telegram_data.get('last_name')
    now = int(time.time())

    db = get_db()
    cur = db.execute('SELECT * FROM users WHERE telegram_id=?', (telegram_id,))
    row = cur.fetchone()
    if row:
        db.execute('UPDATE users SET last_active=?, platform=?, username=?, first_name=?, last_name=? WHERE telegram_id=?',
                   (now, platform, username, first_name, last_name, telegram_id))
        db.commit()
        return db.execute('SELECT * FROM users WHERE telegram_id=?', (telegram_id,)).fetchone()

    db.execute(
        'INSERT INTO users (telegram_id, username, first_name, last_name, platform, points, last_tap, created_at, last_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (telegram_id, username, first_name, last_name, platform, 0, 0, now, now)
    )
    db.commit()
    return db.execute('SELECT * FROM users WHERE telegram_id=?', (telegram_id,)).fetchone()

MIN_INTERVAL_MS = 200
POINTS_PER_TAP = 1

@app.route('/api/tap', methods=['POST'])
def tap():
    data = request.get_json() or {}
    init_data = data.get('init_data')
    platform = data.get('platform', 'unknown')

    if not init_data:
        return jsonify({'error': 'missing init_data'}), 400

    telegram_user = parse_telegram_init_data(init_data)
    if not telegram_user or 'id' not in telegram_user:
        return jsonify({'error': 'invalid init_data'}), 400

    user = get_or_create_user(telegram_user, platform)
    telegram_id = user['telegram_id']

    now_ms = int(time.time() * 1000)
    last_tap = user['last_tap'] or 0
    if now_ms - last_tap < MIN_INTERVAL_MS:
        return jsonify({'error': 'rate_limited', 'retry_after_ms': MIN_INTERVAL_MS - (now_ms-last_tap)}), 429

    db = get_db()
    new_points = user['points'] + POINTS_PER_TAP
    db.execute('UPDATE users SET points=?, last_tap=?, last_active=?, platform=? WHERE telegram_id=?',
               (new_points, now_ms, int(time.time()), platform, telegram_id))
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
