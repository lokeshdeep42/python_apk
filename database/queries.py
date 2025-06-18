from database.db_connection import get_connection
from datetime import datetime

def start_session(account_id, clock_in_time):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (account_id, clock_in, session_date)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?)
    """, (account_id, clock_in_time, clock_in_time.date()))
    session_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return session_id


def end_session(session_id, clock_out_time):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT event_type, event_time FROM sleep_events
        WHERE session_id = ? ORDER BY event_time
    """, (session_id,))
    rows = cursor.fetchall()

    sleep_minutes = 0
    sleep_start = None
    for event_type, time in rows:
        if event_type == 'sleep':
            sleep_start = time
        elif event_type == 'resume' and sleep_start:
            sleep_minutes += int((time - sleep_start).total_seconds() / 60)
            sleep_start = None

    cursor.execute("SELECT clock_in FROM sessions WHERE id = ?", (session_id,))
    clock_in = cursor.fetchone()[0]
    total_minutes = int((clock_out_time - clock_in).total_seconds() / 60) - sleep_minutes

    cursor.execute("""
        UPDATE sessions
        SET clock_out = ?, total_work_minutes = ?
        WHERE id = ?
    """, (clock_out_time, total_minutes, session_id))
    conn.commit()
    conn.close()
    return total_minutes


def log_sleep_event(account_id, session_id, event_type, source='system'):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sleep_events (account_id, session_id, event_type, event_time, source)
        VALUES (?, ?, ?, ?, ?)
    """, (account_id, session_id, event_type, datetime.now(), source))
    conn.commit()
    conn.close()


def fetch_all_sessions(from_date=None, to_date=None):
    conn = get_connection()
    cursor = conn.cursor()

    base_query = """
        SELECT 
            a.username,
            s.clock_in,
            s.clock_out,
            s.session_date,
            ISNULL(s.total_work_minutes, 0),
            (
                SELECT 
                    SUM(DATEDIFF(MINUTE, se1.event_time, se2.event_time))
                FROM sleep_events se1
                JOIN sleep_events se2 ON se1.session_id = se2.session_id
                    AND se1.event_type = 'sleep' AND se2.event_type = 'resume'
                    AND se2.event_time > se1.event_time
                WHERE se1.session_id = s.id
                    AND NOT EXISTS (
                        SELECT 1 FROM sleep_events seX
                        WHERE seX.session_id = se1.session_id 
                          AND seX.event_time > se1.event_time 
                          AND seX.event_time < se2.event_time 
                          AND seX.event_type = 'sleep'
                    )
            ) AS sleep_minutes,
            s.id
        FROM sessions s
        JOIN accounts a ON s.account_id = a.id
    """

    params = []
    if from_date and to_date:
        base_query += " WHERE s.session_date BETWEEN ? AND ?"
        params.extend([from_date, to_date])

    base_query += " ORDER BY s.session_date DESC, s.clock_in DESC"

    cursor.execute(base_query, params)
    results = cursor.fetchall()
    conn.close()
    return results


def fetch_sessions_by_date_range(from_date, to_date):
    return fetch_all_sessions(from_date, to_date)


def authenticate_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, role FROM accounts WHERE username = ? AND password = ? AND is_active = 1
    """, (username, password))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row.id, row.role
    return None, None


def fetch_all_users():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, role,
                CASE WHEN is_active = 1 THEN 'Active' ELSE 'Disabled' END AS status
            FROM accounts
        """)
        users = cursor.fetchall()
        conn.close()
        return users
    
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []


def create_user(username, password, role):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO accounts (username, password, role, is_active)
        VALUES (?, ?, ?, 0)
    """, (username, password, role))
    conn.commit()
    conn.close()


def toggle_user_status(user_id, new_status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE accounts 
        SET is_active = ? 
        WHERE id = ?
    """, (1 if new_status == 'active' else 0, user_id))
    conn.commit()
    conn.close()
    return True


def delete_user(user_id):
    """
    Delete a user and all associated data.
    This includes sessions, sleep events, and feedback.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Delete sleep events for sessions belonging to this user
        cursor.execute("""
            DELETE FROM sleep_events 
            WHERE session_id IN (
                SELECT id FROM sessions WHERE account_id = ?
            )
        """, (user_id,))
        
        # Delete sessions belonging to this user
        cursor.execute("DELETE FROM sessions WHERE account_id = ?", (user_id,))
        
        # Delete feedback from this user
        cursor.execute("DELETE FROM feedback WHERE account_id = ?", (user_id,))
        
        # Finally, delete the user account
        cursor.execute("DELETE FROM accounts WHERE id = ?", (user_id,))
        
        # Check if user was actually deleted
        if cursor.rowcount == 0:
            raise Exception("User not found or could not be deleted")
        
        # Commit all changes
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        # Rollback on error
        conn.rollback()
        conn.close()
        raise e


def insert_feedback(account_id, mood, comment, anonymous):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO feedback (account_id, mood, comment, is_anonymous)
        VALUES (?, ?, ?, ?)
    """, (account_id, mood, comment, anonymous))
    conn.commit()
    conn.close()


def fetch_all_feedback():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.id, a.username, f.mood, f.comment, 
               CASE WHEN f.is_anonymous = 1 THEN 'Yes' ELSE 'No' END as anonymous,
               f.submitted_at
        FROM feedback f
        LEFT JOIN accounts a ON f.account_id = a.id
        ORDER BY f.submitted_at DESC
    """)
    results = cursor.fetchall()
    conn.close()
    return results


def fetch_filtered_feedback(start_date=None, end_date=None, mood='All', keyword=''):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT f.id, a.username, f.mood, f.comment, 
               CASE WHEN f.is_anonymous = 1 THEN 'Yes' ELSE 'No' END as anonymous,
               f.submitted_at
        FROM feedback f
        LEFT JOIN accounts a ON f.account_id = a.id
        WHERE 1=1
    """
    params = []

    if start_date and end_date:
        query += " AND CAST(f.submitted_at AS DATE) BETWEEN ? AND ?"
        params.extend([start_date, end_date])

    if mood != "All":
        query += " AND f.mood = ?"
        params.append(mood)
        
    if keyword and keyword.strip():
        query += " AND (a.username LIKE ? OR f.comment LIKE ?)"
        keyword_param = f"%{keyword.strip()}%"
        params.extend([keyword_param, keyword_param])

    query += " ORDER BY f.submitted_at DESC"

    try:
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results
    
    except Exception as e:
        conn.close()
        return []