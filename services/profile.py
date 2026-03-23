import os

from services.db import get_connection
from services.auth import hash_password

def get_user_profile(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.name, u.email, u.profile_pic, u.created_at,
               COALESCE((SELECT COUNT(*) FROM news_summary WHERE user_id = u.user_id), 0) as total_summaries
        FROM users u
        WHERE u.user_id = %s
    """, (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if row:
        return {
            "name": row[0],
            "email": row[1],
            "profile_pic": row[2] or "default.png",
            "created_at": row[3].strftime("%d %b %Y") if row[3] else "N/A",
            "total_summaries": row[4]
        }
    return None

def update_user_profile(user_id, name, email=None, current_password=None, new_password=None, profile_pic_filename=None):
    """
    Updates the user profile. Raises ValueError on failure.
    Requires current_password to change password.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # 1. Update Profile Fields
        update_query = "UPDATE users SET name = %s"
        params = [name]

        if email:
            update_query += ", email = %s"
            params.append(email)
        
        if profile_pic_filename:
            update_query += ", profile_pic = %s"
            params.append(profile_pic_filename)
        
        # 2. Update Password (if requested)
        if new_password:
            if not current_password:
                raise ValueError("Current password is required to set a new password.")
                
            # Verify current password
            cur.execute("SELECT password FROM users WHERE user_id = %s", (user_id,))
            saved_hash = cur.fetchone()[0]
            if saved_hash != hash_password(current_password):
                raise ValueError("Incorrect current password.")
                
            update_query += ", password = %s"
            params.append(hash_password(new_password))
        
        update_query += " WHERE user_id = %s"
        params.append(user_id)
        
        cur.execute(update_query, tuple(params))
        conn.commit()
        return True
    
    except Exception as e:
        conn.rollback()
        err = str(e)
        if "unique" in err.lower() or "duplicate" in err.lower():
            raise ValueError("Username is already taken.")
        raise ValueError(str(e))
    finally:
        cur.close()
        conn.close()

def delete_user_account(user_id):
    """Delete a user account and all associated data."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Delete related data first
        cur.execute("DELETE FROM news_summary WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM analytics WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error deleting account: {e}")
        return False
    finally:
        cur.close()
        conn.close()

