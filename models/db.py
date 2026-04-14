import sqlite3

DATABASE = "gamingportal.db"

def get_db_connection():
    try:
        conn = sqlite3.connect(DATABASE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print("Database Error:", e)
        return None