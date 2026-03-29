from services.db import get_connection
from services.logger import logger

def init_postgres_db():
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # 1. users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id   SERIAL PRIMARY KEY,
                name      VARCHAR(100) UNIQUE NOT NULL,
                email     VARCHAR(200) UNIQUE NOT NULL,
                password  TEXT NOT NULL,
                role      VARCHAR(50) DEFAULT 'user',
                is_blocked BOOLEAN DEFAULT FALSE,
                profile_pic VARCHAR(255) DEFAULT 'default.png',
                is_verified BOOLEAN DEFAULT FALSE,
                verification_token VARCHAR(100),
                reset_token VARCHAR(100),
                last_login TIMESTAMP,
                last_active TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. news_summary
        cur.execute("""
            CREATE TABLE IF NOT EXISTS news_summary (
                summary_id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
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

        # 3. otp_codes
        cur.execute("""
            CREATE TABLE IF NOT EXISTS otp_codes (
                id SERIAL PRIMARY KEY,
                email VARCHAR(200) NOT NULL,
                otp VARCHAR(10) NOT NULL,
                is_used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. latest_news
        cur.execute("""
            CREATE TABLE IF NOT EXISTS latest_news (
                news_id      SERIAL PRIMARY KEY,
                title        TEXT NOT NULL,
                description  TEXT,
                image_url    TEXT,
                source_url   TEXT UNIQUE NOT NULL,
                source_name  VARCHAR(200),
                api_summary  TEXT,
                published_at TEXT,
                open_count   INTEGER DEFAULT 0,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. analytics
        cur.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                analytics_id   SERIAL PRIMARY KEY,
                user_id        INTEGER UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                total_summaries INTEGER DEFAULT 0,
                english_count   INTEGER DEFAULT 0,
                hindi_count     INTEGER DEFAULT 0,
                gujarati_count  INTEGER DEFAULT 0,
                positive_count  INTEGER DEFAULT 0,
                negative_count  INTEGER DEFAULT 0,
                updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 6. sentiment_analysis
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sentiment_analysis (
                sentiment_id     SERIAL PRIMARY KEY,
                summary_id       INTEGER NOT NULL REFERENCES news_summary(summary_id) ON DELETE CASCADE,
                sentiment_type   VARCHAR(50),
                confidence_score FLOAT,
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 7. translation
        cur.execute("""
            CREATE TABLE IF NOT EXISTS translation (
                translation_id   SERIAL PRIMARY KEY,
                summary_id       INTEGER REFERENCES news_summary(summary_id) ON DELETE CASCADE,
                source_language  VARCHAR(10),
                target_language  VARCHAR(10),
                translated_text  TEXT,
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 8. bookmarks
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                bookmark_id SERIAL PRIMARY KEY,
                user_id     INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                title       TEXT,
                url         TEXT NOT NULL,
                image_url   TEXT,
                source_name TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, url)
            )
        """)

        # 9. ratings
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                rating_id  SERIAL PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                summary_id INTEGER NOT NULL REFERENCES news_summary(summary_id) ON DELETE CASCADE,
                rating     INTEGER CHECK(rating >= 1 AND rating <= 5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, summary_id)
            )
        """)

        # 10. email_preferences
        cur.execute("""
            CREATE TABLE IF NOT EXISTS email_preferences (
                pref_id    SERIAL PRIMARY KEY,
                user_id    INTEGER NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
                preference VARCHAR(20) DEFAULT 'off',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        cur.close()
        conn.close()
        print("✅ All PostgreSQL tables initialized on Cloud Database!")
    except Exception as e:
        print(f"❌ Error initializing Cloud Database: {e}")
        raise e

if __name__ == "__main__":
    init_postgres_db()
