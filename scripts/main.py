"""Simple DB connection script.

Behavior:
- Loads environment variables via python-dotenv
- If DATABASE_URL exists, uses it as DSN
- Otherwise reads USER/PASSWORD/HOST/PORT/DBNAME environment variables
- Connects with psycopg2 and runs SELECT NOW(); to verify connectivity

Run with:
  python scripts/main.py

"""
from dotenv import load_dotenv
import os
import psycopg2
from urllib.parse import urlparse, parse_qs

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

# If DATABASE_URL provided, use it directly; otherwise assemble from parts
if DATABASE_URL:
    dsn = DATABASE_URL
else:
    user = os.getenv('USER') or os.getenv('DB_USER') or os.getenv('POSTGRES_USER')
    password = os.getenv('PASSWORD') or os.getenv('DB_PASS') or os.getenv('POSTGRES_PASSWORD')
    host = os.getenv('HOST') or os.getenv('DB_HOST') or os.getenv('POSTGRES_HOST')
    port = os.getenv('PORT') or os.getenv('DB_PORT') or os.getenv('POSTGRES_PORT') or '5432'
    dbname = os.getenv('DBNAME') or os.getenv('POSTGRES_DB') or 'postgres'
    if not all([user, password, host]):
        print('Missing DB connection parts. Please set DATABASE_URL or USER/PASSWORD/HOST.')
        raise SystemExit(1)
    # build libpq style dsn
    dsn = f"dbname={dbname} user={user} password={password} host={host} port={port}"

print('Using DSN:', dsn if len(dsn) < 200 else dsn[:200] + '...')

try:
    conn = psycopg2.connect(dsn)
    print('Connection successful!')
    cur = conn.cursor()
    cur.execute('SELECT NOW();')
    print('Current Time:', cur.fetchone())
    cur.close()
    conn.close()
    print('Connection closed.')
except Exception as e:
    print('Failed to connect:', e)
    raise
