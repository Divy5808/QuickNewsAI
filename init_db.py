import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "news.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS news_summary (
            summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            article_title TEXT,
            news_url TEXT,
            full_news TEXT,
            summary_text TEXT,
            language TEXT,
            summary_length INTEGER,
            sentiment_result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialized.")

if __name__ == "__main__":
    init_db()
