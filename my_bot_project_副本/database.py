# database.py
import psycopg2 # type: ignore
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT, DB_SSL

def get_connection():
    """获取数据库连接，支持 SSL"""
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        sslmode='require' if DB_SSL == 'true' else 'disable'
    )
    return conn

def get_user_by_telegram_id(telegram_id):
    """通过 telegram_id 查找用户"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(telegram_id, username, invite_code, inviter_id):
    """创建用户"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (telegram_id, username, balance, invite_code, inviter_id)
        VALUES (%s, %s, 1000, %s, %s)
        """, (telegram_id, username, invite_code, inviter_id))
    conn.commit()
    conn.close()

def get_user_by_invite_code(invite_code):
    """通过邀请码查找用户"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE invite_code = %s", (invite_code,))
    user = cursor.fetchone()
    conn.close()
    return user
