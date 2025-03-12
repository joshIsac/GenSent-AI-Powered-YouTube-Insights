import sqlite3
from datetime import datetime
import bcrypt

# Function to hash passwords
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# Function to verify passwords
def verify_password(password, hashed_password):
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

# Function to establish database connection
def get_db_connection():
    return sqlite3.connect("users.db", check_same_thread=False)

# Function to initialize the database
def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    # User sessions table (tracks login/logout times)
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        login_time TEXT,
        logout_time TEXT,
        session_duration REAL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()

# Function to authenticate user
def authenticate(username, password):
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    user = c.fetchone()

    if user and verify_password(password, user[1]):
        login_time = datetime.now()

        # Log login time
        c.execute("INSERT INTO user_sessions (user_id, login_time) VALUES (?, ?)",
                  (user[0], login_time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return {"authenticated": True, "user_id": user[0], "login_time": login_time}
    
    conn.close()
    return {"authenticated": False}

# Function to log out user
def logout_user(user_id, login_time):
    if user_id and login_time:
        conn = get_db_connection()
        c = conn.cursor()

        logout_time = datetime.now()
        session_duration = (logout_time - login_time).total_seconds() / 60  # in minutes

        # Update session record
        c.execute("""
        UPDATE user_sessions 
        SET logout_time = ?, session_duration = ? 
        WHERE user_id = ? AND logout_time IS NULL
        """, (logout_time.strftime("%Y-%m-%d %H:%M:%S"), session_duration, user_id))

        conn.commit()
        conn.close()
        return True
    return False

# Function to register new user
def register_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    if c.fetchone():
        conn.close()
        return False  # Username already exists
    else:
        hashed_password = hash_password(password)
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        conn.close()
        return True
