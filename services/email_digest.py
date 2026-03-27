"""
Phase 3: Email Digest Service
Sends daily/weekly email digests to opted-in users.
Reuses SMTP credentials from auth.py.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from services.db import get_connection
from services.logger import logger

SMTP_EMAIL = "dalwadidev23@gmail.com"
SMTP_PASSWORD = "hjlkjalemslxdiiw"


# ================= EMAIL PREFERENCES TABLE =================
def ensure_email_preferences_table():
    """Create email_preferences table if it doesn't exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_preferences (
            pref_id    SERIAL PRIMARY KEY,
            user_id    INTEGER NOT NULL UNIQUE,
            preference VARCHAR(20) DEFAULT 'off',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def save_email_preference(user_id, preference):
    """Save (upsert) a user's email digest preference: 'daily', 'weekly', or 'off'."""
    ensure_email_preferences_table()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO email_preferences (user_id, preference, updated_at)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id)
        DO UPDATE SET preference = EXCLUDED.preference, updated_at = CURRENT_TIMESTAMP
    """, (user_id, preference))
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Email preference saved for user {user_id}: {preference}")


def get_email_preference(user_id):
    """Get the email digest preference for a user."""
    ensure_email_preferences_table()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT preference FROM email_preferences WHERE user_id = %s", (user_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else "off"


def get_digest_subscribers(frequency):
    """Return list of (user_id, name, email) for users subscribed to given frequency."""
    ensure_email_preferences_table()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.user_id, u.name, u.email
        FROM email_preferences ep
        JOIN users u ON ep.user_id = u.user_id
        WHERE ep.preference = %s AND u.is_blocked = FALSE
    """, (frequency,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# ================= FETCH TOP NEWS FOR DIGEST =================
def fetch_top_news_for_digest(limit=5):
    """Fetch recent top news items from the latest_news table."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT title, source_url, description
            FROM latest_news
            ORDER BY published_at DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching news for digest: {e}")
        rows = []
    finally:
        cur.close()
        conn.close()
    return rows


# ================= COMPOSE HTML EMAIL =================
def compose_digest_html(user_name, articles, frequency):
    """Return an HTML string for the digest email."""
    cards = ""
    for title, url, description in articles:
        cards += f"""
        <div style="border:1px solid #e2e8f0; border-radius:12px; padding:16px; margin-bottom:16px;">
            <h3 style="margin:0 0 8px; font-size:1rem; color:#1e3a8a;">
                <a href="{url}" style="text-decoration:none; color:#2563eb;">{title}</a>
            </h3>
            <p style="margin:0; font-size:0.87rem; color:#64748b;">
                {description or 'Read the full article at the link above.'}
            </p>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family:sans-serif; background:#f1f5f9; padding:30px;">
      <div style="max-width:600px; margin:auto; background:#fff; border-radius:20px; padding:32px; box-shadow:0 8px 24px rgba(0,0,0,0.1);">
        <h1 style="color:#2563eb; margin-bottom:4px;">📰 QuickNewsAI</h1>
        <p style="color:#64748b; margin-top:0;">Your {frequency} news digest</p>
        <hr style="border:none; border-top:1px solid #e2e8f0; margin:20px 0;">
        <p>Hello <strong>{user_name}</strong>,</p>
        <p>Here are the top stories from today:</p>
        {cards}
        <hr style="border:none; border-top:1px solid #e2e8f0; margin:24px 0;">
        <p style="font-size:0.8rem; color:#94a3b8; text-align:center;">
          You are receiving this because you opted in to {frequency} digests on QuickNewsAI.<br>
          To unsubscribe, visit your profile settings.
        </p>
      </div>
    </body>
    </html>
    """


# ================= SEND DIGEST =================
def send_digest_to_user(to_email, to_name, frequency):
    """Fetch news and send a digest email to one user."""
    articles = fetch_top_news_for_digest(limit=5)
    if not articles:
        logger.warning("No articles found for digest. Skipping.")
        return False

    html_body = compose_digest_html(to_name, articles, frequency)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📰 Your QuickNewsAI {frequency.capitalize()} Digest"
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"Digest sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Error sending digest to {to_email}: {e}")
        return False


def send_digests(frequency):
    """Send digests to all subscribers of the given frequency."""
    subscribers = get_digest_subscribers(frequency)
    sent = 0
    for user_id, name, email in subscribers:
        if send_digest_to_user(email, name, frequency):
            sent += 1
    logger.info(f"Sent {sent}/{len(subscribers)} {frequency} digests.")
    return sent
