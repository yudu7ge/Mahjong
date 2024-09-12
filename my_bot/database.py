import os
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv('DB_URL')

def get_db_connection():
    return psycopg2.connect(DB_URL, sslmode='require', cursor_factory=RealDictCursor)

def create_tables():
    conn = get_db_connection()
    with conn.cursor() as cur:
        # 创建用户表
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id TEXT UNIQUE,
                username TEXT,
                invite_code TEXT UNIQUE,
                balance INTEGER DEFAULT 1000,
                inviter_id INTEGER REFERENCES users(id)
            )
        ''')
        
        # 创建游戏历史表
        cur.execute('''
            CREATE TABLE IF NOT EXISTS game_histories (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                bet_amount INTEGER,
                result TEXT,
                profit INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    conn.commit()
    conn.close()

def get_user_by_telegram_id(telegram_id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
        user = cur.fetchone()
    conn.close()
    return user

def get_user_by_invite_code(invite_code):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE invite_code = %s", (invite_code,))
        user = cur.fetchone()
    conn.close()
    return user

def create_user(telegram_id, username, inviter_id=None):
    conn = get_db_connection()
    invite_code = str(uuid.uuid4())[:8].upper()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (telegram_id, username, invite_code, inviter_id) VALUES (%s, %s, %s, %s) RETURNING *",
                (telegram_id, username, invite_code, inviter_id)
            )
            new_user = cur.fetchone()
        conn.commit()
        print(f"New user created: {new_user}")  # 添加日志
        return new_user
    except psycopg2.Error as e:
        print(f"Error creating user: {e}")  # 添加错误日志
        conn.rollback()
        return None
    finally:
        conn.close()
def create_tables():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id TEXT UNIQUE,
                username TEXT,
                invite_code TEXT UNIQUE,
                balance INTEGER DEFAULT 1000,
                inviter_id INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    conn.close()

# 在主函数中调用这个函数
if __name__ == '__main__':
    create_tables()

def update_user_balance(telegram_id, amount):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET balance = balance + %s WHERE telegram_id = %s", (amount, telegram_id))
    conn.commit()
    conn.close()

def add_game_history(user_id, bet_amount, result, profit):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO game_histories (user_id, bet_amount, result, profit) VALUES (%s, %s, %s, %s)",
            (user_id, bet_amount, result, profit)
        )
    conn.commit()
    conn.close()

# 初始化数据库
create_tables()

# 创建官方账户（如果不存在）
def ensure_official_account():
    official_user = get_user_by_telegram_id("project_account_id")
    if not official_user:
        create_user("project_account_id", "OfficialAccount")
        print("Official account created")
    else:
        print("Official account already exists")

ensure_official_account()