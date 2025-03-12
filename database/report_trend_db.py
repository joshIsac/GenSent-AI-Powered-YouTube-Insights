import sqlite3
from datetime import datetime

# Use the same database as trend_db.py
DB_NAME = "trends.db"

# Create reports table if it doesn't exist
def create_reports_table():
    """Ensure the weekly_reports table exists in the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weekly_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_text TEXT NOT NULL,
        region TEXT,
        generated_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

# Fetch trending data for the past 7 days

def get_weekly_trending_data(region=None):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        query = """
        SELECT title, views, likes, comments, region 
        FROM trending_videos 
        WHERE trending_date > DATE('now', '-7 days')
        """
        if region:
            query += " AND region = ?"
            cursor.execute(query, (region,))
        else:
            cursor.execute(query)

        data = cursor.fetchall()
        if not data:
            return "No trending data available for the past week."

        formatted_data = "\n".join([f"Title: {row[0]}, Views: {row[1]}, Likes: {row[2]}, Comments: {row[3]}, Region: {row[4]}" for row in data])
        return formatted_data
    except Exception as e:
        print("Error fetching trending data:", e)
        return None
    finally:
        conn.close()



# Save AI-generated report
def save_report(report, region=None):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO weekly_reports (report_text, region, generated_at) 
        VALUES (?, ?, ?)
        """, (report, region, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception as e:
        print("Error saving report:", e)
    finally:
        conn.close()

# Ensure the reports table is created
create_reports_table()
