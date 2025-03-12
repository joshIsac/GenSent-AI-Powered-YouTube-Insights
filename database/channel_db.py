import sqlite3
from datetime import datetime

# Database name
DB_NAME = "channel_trends.db"

def create_channel_table():
    try:
        # Connect to the database (it will create the file if it doesn't exist)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Create table for storing channel spikes (views, likes, etc.)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_spikes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            video_title TEXT NOT NULL,
            views INTEGER,
            likes INTEGER,
            comments INTEGER,
            spike_percentage REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Commit and close connection
        conn.commit()
        conn.close()
        print("Table created successfully.")
    except Exception as e:
        print(f"Error creating table: {e}")

# Function to fetch previous video stats (views, likes, comments)
def get_previous_video_stats(video_title):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT views, likes, comments FROM channel_spikes
            WHERE video_title = ? ORDER BY timestamp DESC LIMIT 1
        """, (video_title,))
        
        result = cursor.fetchone()
        conn.close()

        if result:
            return {'views': result[0], 'likes': result[1], 'comments': result[2]}
        else:
            return {'views': 0, 'likes': 0, 'comments': 0}  # No previous data, assume 0

    except Exception as e:
        print(f"Error fetching previous video stats: {e}")
        return {'views': 0, 'likes': 0, 'comments': 0}
    



# Function to calculate spike percentage
def calculate_spike_percentage(current_value, previous_value, threshold=0.2):
    if previous_value == 0:
        return 0
    change = (current_value - previous_value) / previous_value
    if change >= threshold:
        return change*100
    return 0



# Function to store spike data in the database
def store_spike_data(channel_id, video_title, views, likes, comments, spike_percentage):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO channel_spikes (channel_id, video_title, views, likes, comments, spike_percentage)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (channel_id, video_title, views, likes, comments, spike_percentage))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error storing spike data: {e}")

# Call create_channel_table to initialize the database and table
create_channel_table()