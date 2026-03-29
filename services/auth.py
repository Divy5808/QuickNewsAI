import uuid, hashlib, random, os, requests
from email.mime.text import MIMEText
from werkzeug.security import generate_password_hash, check_password_hash
from services.db import get_connection


def hash_password(password):
    """Securely hash a password using PBKDF2."""
    return generate_password_hash(password)

def verify_password(hashed_password, password):
    """Verify a hashed password (supports Werkzeug hashes and old SHA-256)."""
    if not hashed_password or not password:
        return False
        
    hashed_password = hashed_password.strip()
    
    # Modern Werkzeug hash check
    if ":" in hashed_password:
        try:
            return check_password_hash(hashed_password, password)
        except Exception:
            return False
            
    # SHA-256 fallback (legacy)
    try:
        legacy_hash = hashlib.sha256(password.encode()).hexdigest()
        if hashed_password == legacy_hash:
            return True
    except Exception:
        pass
        
    # Plain text fallback (VERY legacy/transition)
    return hashed_password == password


def create_users_table():
    """Create the users table if it doesn't exist."""
    conn = get_connection()
    cur = conn.cursor()
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
    
    # ✅ CREATE MASTER ADMIN (admin / admin)
    try:
        cur.execute("SELECT 1 FROM users WHERE name = 'admin'")
        if not cur.fetchone():
            from werkzeug.security import generate_password_hash
            cur.execute("""
                INSERT INTO users (name, email, password, role, is_verified)
                VALUES ('admin', 'admin@gmail.com', %s, 'admin', TRUE)
            """, (generate_password_hash("admin"),))
    except Exception as e:
        print(f"Master admin skip: {e}", flush=True)

    conn.commit()
    cur.close()
    conn.close()

def create_otp_table():
    """Create the unified otp_codes table if it doesn't exist."""
    conn = get_connection()
    cur = conn.cursor()
    # 🛑 First, drop the redundant 'otp_verification' table to merge it
    cur.execute("DROP TABLE IF EXISTS otp_verification")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS otp_codes (
            id SERIAL PRIMARY KEY,
            email VARCHAR(200) NOT NULL,
            otp VARCHAR(10) NOT NULL,
            is_used BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def login_user(name_or_email, password):
    """
    Attempt login.
    Returns user dict on success, or None on failure.
    Raises ValueError if email is not verified or user is blocked.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, name, password, is_verified, role, is_blocked
        FROM users
        WHERE (LOWER(name) = LOWER(%s) OR LOWER(email) = LOWER(%s))
    """, (name_or_email, name_or_email))

    row = cur.fetchone()
    cur.close()

    if row:
        user_id, name, hashed_password, is_verified, role, is_blocked = row
        
        if is_blocked:
            conn.close()
            raise ValueError("Your account has been blocked by an administrator.")
            
        if verify_password(hashed_password, password):
            if not is_verified:
                conn.close()
                raise ValueError("Email not verified. Please check your inbox.")
            
            # ✅ Update last_login (Failsafe for missing columns)
            try:
                cur = conn.cursor()
                cur.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP, last_active = CURRENT_TIMESTAMP WHERE user_id = %s", (user_id,))
                conn.commit()
                cur.close()
            except Exception as e:
                print(f"Skipping activity update: {e}")
            
            conn.close()

            return {"user_id": user_id, "name": name, "role": role}
    
    conn.close()
    return None

def get_all_users():
    """Fetch all users with their activity count for the admin panel."""
    conn = get_connection()
    cur = conn.cursor()
    # Join with news_summary to get activity count
    try:
        # ✅ TRY with new columns
        cur.execute("""
            SELECT u.user_id, u.name, u.email, u.role, u.is_blocked, u.is_verified, u.created_at,
                   u.last_login, u.last_active,
                   COUNT(h.summary_id) as activity_count
            FROM users u
            LEFT JOIN news_summary h ON u.user_id = h.user_id
            GROUP BY u.user_id, u.name, u.email, u.role, u.is_blocked, u.is_verified, u.created_at, u.last_login, u.last_active
            ORDER BY u.created_at DESC
        """)
    except Exception as e:
        # ⚠️ FALLBACK if columns missing
        conn.rollback()
        cur.execute("""
            SELECT u.user_id, u.name, u.email, u.role, u.is_blocked, u.is_verified, u.created_at,
                   NULL as last_login, NULL as last_active,
                   COUNT(h.summary_id) as activity_count
            FROM users u
            LEFT JOIN news_summary h ON u.user_id = h.user_id
            GROUP BY u.user_id, u.name, u.email, u.role, u.is_blocked, u.is_verified, u.created_at
            ORDER BY u.created_at DESC
        """)

    columns = [desc[0] for desc in cur.description]
    users = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return users

def delete_user(target_user_id):
    """Permanently delete a user and all their associated data."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Check if user is an admin
        cur.execute("SELECT role FROM users WHERE user_id = %s", (target_user_id,))
        row = cur.fetchone()
        if row and row[0] == 'admin':
            # Count remaining admins
            cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            admin_count = cur.fetchone()[0]
            if admin_count <= 1:
                raise ValueError("Cannot delete the last administrator.")

        # news_summary and other tables should have ON DELETE CASCADE if possible,
        # but we'll do it manually to be safe if not.
        cur.execute("DELETE FROM news_summary WHERE user_id = %s", (target_user_id,))
        cur.execute("DELETE FROM otp_codes WHERE email = (SELECT email FROM users WHERE user_id = %s)", (target_user_id,))
        cur.execute("DELETE FROM users WHERE user_id = %s", (target_user_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def update_user_role(target_user_id, new_role):
    """Update a user's role (admin/user)."""
    conn = get_connection()
    cur = conn.cursor()
    
    # If demoting an admin, check if they are the last one
    if new_role == 'user':
        cur.execute("SELECT role FROM users WHERE user_id = %s", (target_user_id,))
        row = cur.fetchone()
        if row and row[0] == 'admin':
            cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            admin_count = cur.fetchone()[0]
            if admin_count <= 1:
                cur.close()
                conn.close()
                raise ValueError("Cannot demote the last administrator.")

    cur.execute("UPDATE users SET role = %s WHERE user_id = %s", (new_role, target_user_id))
    conn.commit()
    cur.close()
    conn.close()

def toggle_user_status(target_user_id):
    """Toggle a user's blocked status."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_blocked = NOT is_blocked WHERE user_id = %s", (target_user_id,))
    conn.commit()
    cur.close()
    conn.close()


def register_user(username, email, password):
    """Register a new user (is_verified defaults to FALSE)."""
    hashed = hash_password(password)
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO users (name, email, password, is_verified)
            VALUES (%s, %s, %s, FALSE)
        """, (username, email, hashed))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        err = str(e)
        if "unique" in err.lower() or "duplicate" in err.lower():
            if "name" in err.lower():
                raise ValueError("Username already exists.")
            elif "email" in err.lower():
                raise ValueError("Email already registered.")
        raise ValueError("Registration failed. Please try again.")
    finally:
        cur.close()
        conn.close()

def send_otp(email):
    """Generate and send OTP via smtplib."""
    otp = str(random.randint(100000, 999999))
    conn = get_connection()
    cur = conn.cursor()

    # Delete old OTPs for this email to keep it clean
    cur.execute("DELETE FROM otp_codes WHERE email=%s", (email,))
    
    # Insert new OTP (is_used is FALSE by default)
    cur.execute("INSERT INTO otp_codes (email, otp) VALUES (%s, %s)", (email, otp))

    conn.commit()
    cur.close()
    conn.close()

    # Email content
    msg = MIMEText(f"Your QuickNewsAI OTP is: {otp}\nValid for 5 minutes.")
    msg["Subject"] = "QuickNewsAI Email Verification OTP"
    
    # --- BREVO API (Preferred on Cloud/Hugging Face) ---
    brevo_key = os.environ.get("BREVO_API_KEY")
    is_cloud = os.environ.get("SPACE_ID") or os.environ.get("HF_TOKEN")

    if brevo_key and is_cloud:
        try:
            print(f"🔄 Sending OTP via Brevo API to {email}...", flush=True)
            res = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": brevo_key, "Content-Type": "application/json"},
                json={
                    "sender": {"name": "QuickNewsAI", "email": "dalwadidev23@gmail.com"},
                    "to": [{"email": email}],
                    "subject": "QuickNewsAI Email Verification OTP",
                    "textContent": f"Your QuickNewsAI OTP is: {otp}\nValid for 5 minutes."
                },
                timeout=15
            )
            if res.status_code in [200, 201, 202]:
                print(f"✅ OTP sent via Brevo!", flush=True)
                return
        except Exception as e:
            print(f"❌ Brevo Error: {e}", flush=True)

    # --- FALLBACK: Gmail SMTP (Preferred on Local PC) ---
    smtp_user = os.environ.get("SMTP_USER", "dalwadidev23@gmail.com")
    smtp_pass = os.environ.get("SMTP_PASS", "hjlkjalemslxdiiw")
    try:
        import smtplib
        print(f"🏠 Local/Fallback Mode: Sending via Gmail SMTP...", flush=True)
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        print(f"✅ OTP sent via Gmail!", flush=True)
        return
    except Exception as e:
        print(f"❌ SMTP Error: {e}", flush=True)

    # Final debug log for devs
    print(f"MOCK OTP: {otp}", flush=True)
    resend_key = os.environ.get("RESEND_API_KEY")
    if resend_key:
        try:
            print(f"🔄 Attempting to send OTP via Resend API to {email}...", flush=True)
            res = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": "QuickNewsAI <onboarding@resend.dev>",
                    "to": [email],
                    "subject": "QuickNewsAI Email Verification OTP",
                    "text": f"Your QuickNewsAI OTP is: {otp}\nValid for 5 minutes."
                },
                timeout=15
            )
            if res.status_code in [200, 201]:
                print(f"✅ OTP sent to {email} via Resend!", flush=True)
                return
            else:
                print(f"⚠️ Resend Failure ({res.status_code}): {res.text}", flush=True)
        except Exception as e:
            print(f"❌ Resend API Error: {e}", flush=True)

    # --- FALLBACK: Mock/Debug log ---
    print(f"MOCK OTP (FAILED REAL): {otp}", flush=True)

def verify_email_otp(email, otp, delete_after=True):
    """Verify an OTP from the database."""
    conn = get_connection()
    cur = conn.cursor()

    # Look for a valid, unused OTP for this email
    cur.execute("SELECT otp FROM otp_codes WHERE email=%s AND otp=%s AND is_used=FALSE", (email, otp))
    row = cur.fetchone()

    if row:
        # Mark user as verified
        cur.execute("UPDATE users SET is_verified=TRUE WHERE email=%s", (email,))
        
        if delete_after:
            # Instead of deleting, we can mark it as used to track it
            cur.execute("UPDATE otp_codes SET is_used=TRUE WHERE email=%s AND otp=%s", (email, otp))
        else:
            # For reset-password flow, we might keep it temporarily
            pass
            
        conn.commit()
        cur.close()
        conn.close()
        return True
    
    cur.close()
    conn.close()
    return False

def generate_reset_token(email):
    """Generate a password reset token for a user."""
    reset_token = str(uuid.uuid4())
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET reset_token = %s WHERE email = %s", (reset_token, email))
    count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return reset_token if count > 0 else None

def send_reset_otp(email):
    """Generate and send a 6-digit OTP for password reset."""
    otp = str(random.randint(100000, 999999))
    conn = get_connection()
    cur = conn.cursor()
    # Store in otp_codes table (reusing it)
    cur.execute("DELETE FROM otp_codes WHERE email=%s", (email,))
    cur.execute("INSERT INTO otp_codes (email, otp) VALUES (%s, %s)", (email, otp))
    conn.commit()
    cur.close()
    conn.close()

    msg = MIMEText(f"Your QuickNewsAI Password Reset OTP is: {otp}\nValid for 5 minutes.")
    msg["Subject"] = "QuickNewsAI Password Reset OTP"
    
    # --- BREVO (Preferred on Cloud) ---
    brevo_key = os.environ.get("BREVO_API_KEY")
    is_cloud = os.environ.get("SPACE_ID") or os.environ.get("HF_TOKEN")

    if brevo_key and is_cloud:
        try:
            res = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": brevo_key, "Content-Type": "application/json"},
                json={
                    "sender": {"name": "QuickNewsAI", "email": "dalwadidev23@gmail.com"},
                    "to": [{"email": email}],
                    "subject": "QuickNewsAI Password Reset OTP",
                    "textContent": f"Your QuickNewsAI Password Reset OTP is: {otp}\nValid for 5 minutes."
                },
                timeout=15
            )
            if res.status_code in [200, 201, 202]:
                print(f"✅ Reset OTP sent via Brevo!", flush=True)
                return
        except Exception as e:
            print(f"❌ Brevo Reset Error: {e}", flush=True)

    # --- SMTP (Preferred on Local PC) ---
    smtp_user = os.environ.get("SMTP_USER", "dalwadidev23@gmail.com")
    smtp_pass = os.environ.get("SMTP_PASS", "hjlkjalemslxdiiw")
    try:
        import smtplib
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        print(f"✅ Reset OTP sent via Gmail!", flush=True)
        return
    except Exception:
        pass

    print(f"MOCK RESET OTP: {otp}", flush=True)

def reset_password_with_otp(email, otp, new_password):
    """Verify OTP and reset password."""
    conn = get_connection()
    cur = conn.cursor()
    
    # 1. Verify OTP (without auto-deleting yet)
    cur.execute("SELECT otp FROM otp_codes WHERE email = %s", (email,))
    row = cur.fetchone()
    if not row or row[0] != otp:
        cur.close()
        conn.close()
        return False
        
    # 2. Reset password
    hashed = hash_password(new_password)
    cur.execute("UPDATE users SET password = %s WHERE email = %s", (hashed, email))
    
    # 3. Clean up OTP
    cur.execute("DELETE FROM otp_codes WHERE email=%s", (email,))
    
    conn.commit()
    cur.close()
    conn.close()
    return True

def send_reset_email(email, token):
    """Send password reset link via smtplib."""
    # Use your local IP so mobile links work if on same Wi-Fi
    base_url = "http://192.168.29.26:5000"
    reset_url = f"{base_url}/reset-password/{token}"
    msg = MIMEText(f"To reset your password, visit the following link: {reset_url}\n\nIf you did not make this request, ignore this email.")
    # Use correct sender
    smtp_user = os.environ.get("SMTP_USER", "dalwadidev23@gmail.com")
    smtp_pass = os.environ.get("SMTP_PASS", "hjlkjalemslxdiiw")
    
    msg["Subject"] = "QuickNewsAI Password Reset Request"
    msg["From"] = smtp_user
    msg["To"] = email

    # --- BREVO (Preferred on Cloud) ---
    brevo_key = os.environ.get("BREVO_API_KEY")
    is_cloud = os.environ.get("SPACE_ID") or os.environ.get("HF_TOKEN")

    if brevo_key and is_cloud:
        try:
            res = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": brevo_key, "Content-Type": "application/json"},
                json={
                    "sender": {"name": "QuickNewsAI", "email": "dalwadidev23@gmail.com"},
                    "to": [{"email": email}],
                    "subject": "QuickNewsAI Password Reset Link",
                    "textContent": f"To reset your password, visit the following link: {reset_url}"
                },
                timeout=15
            )
            if res.status_code in [200, 201, 202]:
                print(f"✅ Reset link sent via Brevo!", flush=True)
                return
        except Exception as e:
            print(f"❌ Brevo Link Error: {e}", flush=True)

    # --- SMTP (Preferred on Local PC) ---
    smtp_user = os.environ.get("SMTP_USER", "dalwadidev23@gmail.com")
    smtp_pass = os.environ.get("SMTP_PASS", "hjlkjalemslxdiiw")
    try:
        import smtplib
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        print(f"✅ Reset Link sent via Gmail!", flush=True)
        return
    except Exception:
        pass

    print(f"MOCK RESET LINK: {reset_url}", flush=True)

def reset_password_with_token(token, new_password):
    """Reset password using a reset token."""
    hashed = hash_password(new_password)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password = %s, reset_token = NULL WHERE reset_token = %s", (hashed, token))
    count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return count > 0
