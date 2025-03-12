import sqlite3 
from datetime import datetime


# Database connection
DB_NAME = "trends.db"

def create_trends_table():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()


    c.execute("""CREATE TABLE IF NOT EXISTS trending_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT UNIQUE NOT NULL,
            title TEXT,
            channel TEXT,
            category TEXT,
            views INTEGER,
            likes INTEGER,
            comments INTEGER,
            engagement_rate REAL,
            region TEXT,
            trending_date TEXT )""")
    

    conn.commit()
    conn.close()

def insert_trending_video(video_data):
    """Inserts or updates a trending video entry."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO trending_videos (video_id, title, channel, category, views, likes, comments, engagement_rate, region, trending_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(video_id) DO UPDATE SET 
            views = COALESCE(EXCLUDED.views, views),
            likes = COALESCE(EXCLUDED.likes, likes),
            comments = COALESCE(EXCLUDED.comments, comments),
            engagement_rate = COALESCE(EXCLUDED.engagement_rate, engagement_rate),
            trending_date = COALESCE(EXCLUDED.trending_date, trending_date)
    """, (
        video_data["video_id"], video_data["title"], video_data["channel"],
        video_data["category"], video_data["views"], video_data["likes"],
        video_data["comments"], video_data["engagement_rate"], video_data["region"],
        datetime.now().strftime("%Y-%m-%d")
    ))

    conn.commit()
    conn.close()

def fetch_trending_data(region=None, date_range=None):
    """Fetches historical trending data based on region and date range."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    query = "SELECT * FROM trending_videos WHERE 1=1"
    params = []

    if region:
        query += " AND region = ?"
        params.append(region)
    
    if date_range:
        query += " AND trending_date >= ?"
        params.append(date_range)
    
    cursor.execute(query, params)
    data = cursor.fetchall()
    
    conn.close()
    return data


create_trends_table()
print("Database initialized: trends.db")
