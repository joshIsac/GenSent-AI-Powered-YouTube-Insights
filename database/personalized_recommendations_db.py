import sqlite3
from datetime import datetime

DB_NAME = "personalized_dataset.db"

def connect_db():
    """Establish a connection to the SQLite database."""
    return sqlite3.connect(DB_NAME)

def create_tables():
    """Create tables for storing video data if they do not exist."""
    conn = connect_db()
    cursor = conn.cursor()
    
    # Creating the video_dataset table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_dataset (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT UNIQUE,
            channel_id TEXT,
            title TEXT,
            description TEXT,
            tags TEXT,
            category_id TEXT,
            publish_date TEXT,
            thumbnail_url TEXT,
            view_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            subscriber_count INTEGER,
            fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database tables created successfully.")

def store_video_data(video_data, channel_id, subscriber_count):
    """Store video data in the database, ensuring no duplicate entries."""
    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT OR IGNORE INTO video_dataset (
                video_id, channel_id, title, description, tags, category_id, publish_date,
                thumbnail_url, view_count, like_count, comment_count, subscriber_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            video_data["video_id"],
            channel_id,
            video_data["title"],
            video_data["description"],
            video_data["tags"],
            video_data["category_id"],
            video_data["publish_date"],
            video_data["thumbnail_url"],
            video_data["view_count"],
            video_data["like_count"],
            video_data["comment_count"],
            subscriber_count
        ))

        conn.commit()
        print(f"Stored video ID: {video_data['video_id']}")
    except Exception as e:
        print(f"Database error while storing video data: {e}")
    finally:
        conn.close()

def get_videos_by_genre(genre, limit=25):
    """Retrieve recommended videos based on a genre from the dataset."""
    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT title, thumbnail_url, view_count, like_count, comment_count
            FROM video_dataset
            WHERE tags LIKE ?
            ORDER BY view_count DESC
            LIMIT ?
        """, (f"%{genre}%", limit))

        results = cursor.fetchall()
        print(f"Found {len(results)} videos for genre: {genre}")
    except Exception as e:
        print(f"Database error while fetching videos: {e}")
        results = []
    finally:
        conn.close()

    return results

# Initialize the database and create tables
create_tables()
