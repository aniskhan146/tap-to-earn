CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  telegram_id TEXT UNIQUE,
  username TEXT,
  first_name TEXT,
  last_name TEXT,
  platform TEXT,
  points INTEGER DEFAULT 0,
  last_tap INTEGER DEFAULT 0,
  created_at INTEGER,
  last_active INTEGER
);

CREATE TABLE IF NOT EXISTS taps (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  telegram_id TEXT,
  ts INTEGER,
  count INTEGER
);
