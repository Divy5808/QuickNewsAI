from services.db import get_connection
from services.logger import logger

# ================= HELPER: UPDATE ANALYTICS TABLE =================
def update_analytics_table(conn, user_id, language, sentiment):
    cur = conn.cursor()

    # Check if analytics row exists for this user
    cur.execute("SELECT analytics_id FROM analytics WHERE user_id = %s", (user_id,))
    row = cur.fetchone()

    # Build column increments
    lang_col = {
        "en": "english_count",
        "hi": "hindi_count",
        "gu": "gujarati_count"
    }.get(language, "english_count")

    sent_col = "positive_count" if (sentiment or "").lower() == "positive" else "negative_count"

    if row:
        # UPDATE existing row
        cur.execute(f"""
            UPDATE analytics
            SET total_summaries = total_summaries + 1,
                {lang_col} = {lang_col} + 1,
                {sent_col} = {sent_col} + 1
            WHERE user_id = %s
        """, (user_id,))
    else:
        # INSERT new row with defaults
        lang_vals = {
            "english_count": 0,
            "hindi_count": 0,
            "gujarati_count": 0
        }
        lang_vals[lang_col] = 1

        sent_vals = {"positive_count": 0, "negative_count": 0}
        sent_vals[sent_col] = 1

        cur.execute("""
            INSERT INTO analytics
            (user_id, total_summaries, english_count, hindi_count, gujarati_count, positive_count, negative_count)
            VALUES (%s, 1, %s, %s, %s, %s, %s)
        """, (
            user_id,
            lang_vals["english_count"],
            lang_vals["hindi_count"],
            lang_vals["gujarati_count"],
            sent_vals["positive_count"],
            sent_vals["negative_count"]
        ))

    cur.close()

# ================= SAVE NEWS =================
def save_news_safe(user_id, title, url, full_news, summary, language, summary_length, sentiment, sentiment_score=0.0):

    conn = get_connection()
    cur = conn.cursor()

    # Insert into news_summary and get the new summary_id
    cur.execute("""
        INSERT INTO news_summary
        (user_id, article_title, news_url, full_news, summary_text,
         language, summary_length, sentiment_result)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING summary_id
    """,(
        user_id,
        title,
        url,
        full_news,
        summary,
        language,
        summary_length,
        sentiment
    ))

    new_summary_id = cur.fetchone()[0]
    conn.commit()

    # ✅ Insert into sentiment_analysis table
    try:
        sentiment_type = sentiment if isinstance(sentiment, str) else "Neutral"
        cur.execute("""
            INSERT INTO sentiment_analysis (summary_id, sentiment_type, confidence_score)
            VALUES (%s, %s, %s)
        """, (new_summary_id, sentiment_type, sentiment_score))
        conn.commit()
    except Exception as e:
        print("Sentiment analysis insert error:", e)

    # ✅ Also update analytics table
    try:
        update_analytics_table(conn, user_id, language, sentiment)
        conn.commit()
    except Exception as e:
        print("Analytics update error:", e)

    # ✅ Update last_active for user (Failsafe)
    try:
        cur.execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = %s", (user_id,))
        conn.commit()
    except Exception as e:
        print(f"Skipping activity update (history): {e}")

    cur.close()
    conn.close()

# ================= SAVE TRANSLATION =================
def save_translation(summary_id, source_language, target_language, translated_text):
    """Save a translation record into the translation table."""
    if not translated_text:
        return

    # summary_id can be None for latest news (no linked summary)
    sid = summary_id if summary_id else None

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO translation (summary_id, source_language, target_language, translated_text)
            VALUES (%s, %s, %s, %s)
        """, (sid, source_language, target_language, translated_text))
        conn.commit()
        print(f"[DB] Translation saved: {source_language} -> {target_language}, summary_id={sid}")
    except Exception as e:
        print("Translation save error:", e)
    finally:
        cur.close()
        conn.close()


# ================= SAVE LATEST NEWS =================
def save_latest_news_bulk(articles):
    """Save a list of news articles from the News API into the latest_news table."""
    if not articles:
        return

    conn = get_connection()
    cur = conn.cursor()

    saved = 0
    for a in articles:
        title       = (a.get("title") or "")[:500]
        description = a.get("description") or ""
        image_url   = a.get("urlToImage") or ""
        source_url  = a.get("url") or ""
        source_name = (a.get("source", {}).get("name") or "")[:200]
        api_summary = a.get("content") or description  # NewsAPI 'content' field
        published_at = a.get("publishedAt") or None

        if not source_url or not title:
            continue

        try:
            cur.execute("""
                INSERT INTO latest_news
                    (title, description, image_url, source_url, source_name, api_summary, published_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_url) DO NOTHING
            """, (title, description, image_url, source_url, source_name, api_summary, published_at))
            saved += 1
        except Exception as e:
            print(f"latest_news insert error: {e}")

    conn.commit()
    print(f"[DB] {saved} latest news articles saved.")
    cur.close()
    conn.close()


def get_all_history(user_id):


    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT summary_id,
               article_title,
               news_url,
               summary_text,
               full_news,
               language,
               summary_length,
               created_at
        FROM news_summary
        WHERE user_id = %s
        ORDER BY created_at DESC
    """,(user_id,))

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

# ================= GET HISTORY =================
def get_history_by_id(news_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT article_title,
               summary_text,
               full_news,
               news_url
        FROM news_summary
        WHERE summary_id = %s
    """,(news_id,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    return row


# ================= DELETE =================
def delete_history_by_id(news_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM news_summary
        WHERE summary_id = %s
    """,(news_id,))

    conn.commit()
    cur.close()
    conn.close()
# ================= LANGUAGE STATS =================
def get_language_stats(user_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT language, COUNT(*)
        FROM news_summary
        WHERE user_id = %s
        GROUP BY language
    """,(user_id,))

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data


# ================= LENGTH STATS =================
def get_length_stats(user_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT summary_length, COUNT(*)
        FROM news_summary
        WHERE user_id = %s
        GROUP BY summary_length
    """,(user_id,))

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data


# ================= SENTIMENT STATS =================
def get_sentiment_stats(user_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT sentiment_result, COUNT(*)
        FROM news_summary
        WHERE user_id = %s
        GROUP BY sentiment_result
    """,(user_id,))

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data


# ================= ACTIVITY STATS =================
def get_activity_stats(user_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DATE(created_at), COUNT(*)
        FROM news_summary
        WHERE user_id = %s
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at)
    """,(user_id,))

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

# ================= MOST READ NEWS (via latest_news.open_count) =================
def increase_open_count(url, title):
    """Increment open_count in latest_news for the article matching the given URL."""
    if not url:
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE latest_news
        SET open_count = open_count + 1
        WHERE source_url = %s
    """, (url,))

    conn.commit()
    cur.close()
    conn.close()

def get_most_read_news(limit=5):
    """Return top N most-read articles from latest_news ordered by open_count."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT title, source_url, open_count
        FROM latest_news
        WHERE open_count > 0
        ORDER BY open_count DESC
        LIMIT %s
    """, (limit,))

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

# ================= GLOBAL ADMIN STATS =================
def get_global_stats():
    """Fetch global statistics for the admin dashboard."""
    conn = get_connection()
    cur = conn.cursor()
    
    stats = {}
    
    # Total Users
    cur.execute("SELECT COUNT(*) FROM users")
    stats['total_users'] = cur.fetchone()[0]
    
    # Total Summaries
    cur.execute("SELECT COUNT(*) FROM news_summary")
    stats['total_summaries'] = cur.fetchone()[0]
    
    # Total Translations
    cur.execute("SELECT COUNT(*) FROM translation")
    stats['total_translations'] = cur.fetchone()[0]
    
    # Language Distribution
    cur.execute("SELECT language, COUNT(*) FROM news_summary GROUP BY language ORDER BY COUNT(*) DESC")
    stats['languages'] = cur.fetchall()
    
    # New Signups Today
    cur.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE")
    stats['new_users_today'] = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    return stats

def get_admin_news_history(limit=50, offset=0, search=None):
    """Fetch all news summaries with user info for admin management."""
    conn = get_connection()
    cur = conn.cursor()
    
    query = """
        SELECT s.summary_id, s.article_title, s.news_url, s.language, s.created_at, u.name as user_name, u.user_id
        FROM news_summary s
        JOIN users u ON s.user_id = u.user_id
    """
    params = []
    
    if search:
        query += " WHERE s.article_title LIKE %s OR u.name LIKE %s "
        params.extend([f"%{search}%", f"%{search}%"])
        
    query += " ORDER BY s.created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    cur.execute(query, tuple(params))
    columns = [desc[0] for desc in cur.description]
    data = [dict(zip(columns, row)) for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    return data

# ================= USER DASHBOARD STATS =================
def get_user_dashboard_stats(user_id):
    """Get quick stats for user dashboard: total summaries, favorite language, last active."""
    conn = get_connection()
    cur = conn.cursor()
    stats = {}

    # Total summaries
    cur.execute("SELECT COUNT(*) FROM news_summary WHERE user_id = %s", (user_id,))
    stats['total_summaries'] = cur.fetchone()[0]

    # Favorite language
    cur.execute("""
        SELECT language, COUNT(*) as cnt FROM news_summary
        WHERE user_id = %s
        GROUP BY language ORDER BY cnt DESC LIMIT 1
    """, (user_id,))
    fav = cur.fetchone()
    lang_names = {"en": "English", "hi": "Hindi", "gu": "Gujarati"}
    stats['favorite_language'] = lang_names.get(fav[0], fav[0]) if fav else "N/A"

    # Last active (latest summary date)
    cur.execute("SELECT MAX(created_at) FROM news_summary WHERE user_id = %s", (user_id,))
    last = cur.fetchone()[0]
    stats['last_active'] = last.strftime("%d %b %Y, %I:%M %p") if last else "Never"

    cur.close()
    conn.close()
    return stats

# ================= RECENT HISTORY =================
def get_recent_history(user_id, limit=3):
    """Return last N history items for quick-access on dashboard."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT summary_id, article_title, language, created_at
        FROM news_summary
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """, (user_id, limit))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r[0],
            "title": r[1] or "News Article",
            "language": (r[2] or "en").upper(),
            "date": r[3].strftime("%d %b %Y") if r[3] else ""
        })
    return results

# ================= DELETE ALL HISTORY =================
def delete_all_history(user_id):
    """Delete all news summary history for a user."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM news_summary WHERE user_id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()


# ===========================================================
# PHASE 2: BOOKMARKS
# ===========================================================
def _ensure_bookmarks_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            bookmark_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            title       TEXT,
            url         TEXT NOT NULL,
            image_url   TEXT,
            source_name TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, url)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def toggle_bookmark(user_id, url, title=None, image_url=None, source_name=None):
    """Toggle bookmark for an article. Returns True if bookmarked, False if removed."""
    _ensure_bookmarks_table()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT bookmark_id FROM bookmarks WHERE user_id=%s AND url=%s", (user_id, url))
    row = cur.fetchone()
    if row:
        cur.execute("DELETE FROM bookmarks WHERE user_id=%s AND url=%s", (user_id, url))
        conn.commit()
        cur.close()
        conn.close()
        return False   # removed
    else:
        cur.execute("""
            INSERT INTO bookmarks (user_id, url, title, image_url, source_name)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, url, title, image_url, source_name))
        conn.commit()
        cur.close()
        conn.close()
        return True    # added


def is_bookmarked(user_id, url):
    """Check if a URL is already bookmarked by the user."""
    _ensure_bookmarks_table()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM bookmarks WHERE user_id=%s AND url=%s", (user_id, url))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row is not None


def get_bookmarks(user_id):
    """Return all bookmarked articles for a user as a list of dicts."""
    _ensure_bookmarks_table()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT bookmark_id, title, url, image_url, source_name, created_at
        FROM bookmarks WHERE user_id=%s ORDER BY created_at DESC
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {"id": r[0], "title": r[1] or "News Article", "url": r[2],
         "image_url": r[3], "source_name": r[4],
         "date": r[5].strftime("%d %b %Y") if r[5] else ""}
        for r in rows
    ]


# ===========================================================
# PHASE 2: RATINGS
# ===========================================================
def _ensure_ratings_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            rating_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            summary_id INTEGER NOT NULL,
            rating     INTEGER CHECK(rating >= 1 AND rating <= 5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, summary_id)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def save_rating(user_id, summary_id, rating):
    """Upsert a rating (1–5) for a summary."""
    _ensure_ratings_table()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO ratings (user_id, summary_id, rating)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id, summary_id)
        DO UPDATE SET rating = EXCLUDED.rating, created_at = CURRENT_TIMESTAMP
    """, (user_id, summary_id, rating))
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Rating {rating}/5 saved for summary {summary_id} by user {user_id}")


def get_average_rating(user_id=None):
    """Return average rating (float) across all summaries, optionally filtered by user."""
    _ensure_ratings_table()
    conn = get_connection()
    cur = conn.cursor()
    if user_id:
        cur.execute(
            "SELECT ROUND(AVG(rating), 1) FROM ratings WHERE user_id=%s",
            (user_id,)
        )
    else:
        cur.execute("SELECT ROUND(AVG(rating), 1) FROM ratings")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return float(row[0]) if row and row[0] else 0.0


def get_user_rating(user_id, summary_id):
    """Return the user's rating for a summary, or None."""
    _ensure_ratings_table()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT rating FROM ratings WHERE user_id=%s AND summary_id=%s",
        (user_id, summary_id)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


# ===========================================================
# PHASE 2: CATEGORIES
# ===========================================================
CATEGORY_KEYWORDS = {
    "Technology": ["tech", "software", "ai", "machine learning", "computer", "internet", "cyber",
                   "startup", "app", "digital", "robot", "data", "cloud", "blockchain"],
    "Politics":   ["government", "election", "parliament", "minister", "politics", "vote", "policy",
                   "president", "prime minister", "law", "senate", "congress", "democracy"],
    "Sports":     ["cricket", "football", "soccer", "ipl", "tennis", "match", "player", "team",
                   "tournament", "olympic", "goal", "score", "championship", "stadium"],
    "Business":   ["market", "stock", "economy", "gdp", "finance", "company", "startup", "trade",
                   "investment", "profit", "revenue", "merger", "acquisition", "bank"],
    "Health":     ["health", "hospital", "doctor", "medicine", "covid", "vaccine", "disease",
                   "treatment", "mental health", "fitness", "diet", "surgery", "cancer"],
    "Science":    ["science", "research", "nasa", "space", "discovery", "study", "experiment",
                   "biology", "physics", "chemistry", "climate", "environment"],
    "Entertainment": ["movie", "film", "actor", "actress", "bollywood", "hollywood", "music",
                      "celebrity", "award", "series", "netflix", "entertainment", "concert"],
}


def auto_categorize(text):
    """Return the most likely category string for the given text."""
    if not text:
        return "General"
    text_lower = text.lower()
    scores = {cat: 0 for cat in CATEGORY_KEYWORDS}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[cat] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "General"


def get_history_with_categories(user_id):
    """Return all history rows with an auto-computed category field."""
    rows = get_all_history(user_id)
    results = []
    for r in rows:
        summary_text = r[3] or ""
        category = auto_categorize(summary_text)
        results.append({
            "id": r[0],
            "title": r[1] or "News Article",
            "url": r[2],
            "summary": summary_text[:200],
            "language": r[5],
            "summary_length": r[6],
            "date": r[7],
            "category": category,
        })
    return results


# ===========================================================
# PHASE 3: EMAIL PREFERENCE WRAPPERS
# ===========================================================
def save_email_preference(user_id, preference):
    from services.email_digest import save_email_preference as _save
    _save(user_id, preference)


def get_email_preference(user_id):
    from services.email_digest import get_email_preference as _get
    return _get(user_id)
