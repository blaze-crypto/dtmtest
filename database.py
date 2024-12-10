import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import datetime, timedelta
import csv
import io
from config import DATABASE_URL

@contextmanager
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()

def create_tables():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS tests (
                    id SERIAL PRIMARY KEY,
                    creator_id BIGINT,
                    code TEXT UNIQUE,
                    name TEXT NOT NULL,
                    answers TEXT NOT NULL,
                    scores TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (creator_id) REFERENCES users (id)
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS test_results (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    test_id INTEGER,
                    score REAL,
                    user_answers TEXT,
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (test_id) REFERENCES tests (id)
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_test_attempts (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    test_id INTEGER,
                    attempt_count INTEGER DEFAULT 1,
                    last_attempt_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (test_id) REFERENCES tests (id),
                    UNIQUE(user_id, test_id)
                )
            ''')
        conn.commit()

def get_test_count():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM tests")
            return cur.fetchone()[0]

def ban_user(user_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET is_banned = TRUE WHERE id = %s", (user_id,))
        conn.commit()
        return conn.rowcount > 0

def unban_user(user_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET is_banned = FALSE WHERE id = %s", (user_id,))
        conn.commit()
        return conn.rowcount > 0

def is_user_banned(user_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT is_banned FROM users WHERE id = %s", (user_id,))
            result = cur.fetchone()
            return result and result[0]

def get_all_tests():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM tests ORDER BY created_at DESC")
            return cur.fetchall()

def delete_test(test_code: str):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tests WHERE code = %s", (test_code,))
        conn.commit()

def get_user_stats():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            user_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM tests")
            test_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM test_results")
            result_count = cur.fetchone()[0]
            return user_count, test_count, result_count

def search_test(query: str):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT t.id, t.code, t.name, t.created_at, u.name as creator_name
                FROM tests t
                JOIN users u ON t.creator_id = u.id
                WHERE t.code ILIKE %s OR t.name ILIKE %s
                ORDER BY t.created_at DESC
                LIMIT 10
            """, (f"%{query}%", f"%{query}%"))
            return cur.fetchall()

def delete_old_tests(days=30):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            threshold_date = datetime.now() - timedelta(days=days)
            cur.execute("DELETE FROM tests WHERE created_at < %s", (threshold_date,))
            deleted_count = cur.rowcount
        conn.commit()
        return deleted_count

def get_user_count():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            return cur.fetchone()[0]

def register_user(user_id: int, name: str, phone: str, username: str):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (id, name, phone, username)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name, phone = EXCLUDED.phone, username = EXCLUDED.username
            """, (user_id, name, phone, username))
        conn.commit()

def is_user_registered(user_id: int) -> bool:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cur.fetchone() is not None

def create_test(creator_id: int, code: str, answers: str, name: str):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tests (creator_id, code, answers, name)
                VALUES (%s, %s, %s, %s)
            """, (creator_id, code, answers, name))
        conn.commit()

def get_test(code: str):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM tests WHERE code = %s", (code,))
            return cur.fetchone()

def update_test(code: str, new_answers: str, new_name: str):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE tests SET answers = %s, name = %s WHERE code = %s", (new_answers, new_name, code))
        conn.commit()

def save_test_result(user_id: int, test_id: int, score: float, user_answers: str):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO test_results (user_id, test_id, score, user_answers)
                VALUES (%s, %s, %s, %s)
            """, (user_id, test_id, score, user_answers))
            
            cur.execute("""
                INSERT INTO user_test_attempts (user_id, test_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, test_id) DO UPDATE SET
                attempt_count = user_test_attempts.attempt_count + 1,
                last_attempt_at = CURRENT_TIMESTAMP
            """, (user_id, test_id))
        
        conn.commit()

def get_all_user_ids():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users")
            return [row[0] for row in cur.fetchall()]

def get_user_tests(user_id: int):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT code, name, created_at
                FROM tests
                WHERE creator_id = %s
                ORDER BY created_at DESC
            """, (user_id,))
            return cur.fetchall()

def get_test_statistics(test_id: int):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT u.id, u.name, u.username, u.phone, tr.score, tr.user_answers, tr.submitted_at,
                       uta.attempt_count
                FROM test_results tr
                JOIN users u ON tr.user_id = u.id
                JOIN user_test_attempts uta ON tr.user_id = uta.user_id AND tr.test_id = uta.test_id
                WHERE tr.test_id = %s
                ORDER BY tr.score DESC, tr.submitted_at ASC
            """, (test_id,))
            return cur.fetchall()

def get_user_info(user_id: int):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name, username, phone FROM users WHERE id = %s", (user_id,))
            return cur.fetchone()

def get_all_users():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name, username, phone FROM users")
            return cur.fetchall()

def generate_users_csv():
    users = get_all_users()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['ID', 'Name', 'Username', 'Phone'])
    for user in users:
        writer.writerow([
            user['id'],
            user['name'],
            f"@{user['username']}" if user['username'] else "N/A",
            user['phone'] if user['phone'] else "N/A"
        ])
    return output.getvalue()

def update_user_username(user_id: int, username: str):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET username = %s WHERE id = %s", (username, user_id))
        conn.commit()

def add_test_scores(test_code: str, scores: list):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            scores_str = ','.join(map(str, scores))
            cur.execute("UPDATE tests SET scores = %s WHERE code = %s", (scores_str, test_code))
        conn.commit()

def get_test_scores(test_code: str):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT scores FROM tests WHERE code = %s", (test_code,))
            result = cur.fetchone()
            if result and result[0]:
                return list(map(float, result[0].split(',')))
            return None

def get_user_test_attempts(user_id: int, test_id: int):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT attempt_count, last_attempt_at
                FROM user_test_attempts
                WHERE user_id = %s AND test_id = %s
            """, (user_id, test_id))
            return cur.fetchone()

def get_leaderboard(limit=10):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT u.name, u.username, AVG(tr.score) as avg_score, COUNT(tr.id) as tests_taken
                FROM users u
                JOIN test_results tr ON u.id = tr.user_id
                GROUP BY u.id
                ORDER BY avg_score DESC, tests_taken DESC
                LIMIT %s
            """, (limit,))
            return cur.fetchall()

def get_test_by_id(test_id: int):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT t.*, u.name as creator_name
                FROM tests t
                JOIN users u ON t.creator_id = u.id
                WHERE t.id = %s
            """, (test_id,))
            return cur.fetchone()

