import sqlite3
import os

DATABASE_DIR = os.path.join(os.path.dirname(__file__), 'data')
DATABASE_PATH = os.path.join(DATABASE_DIR, 'youtube_videos.db')

def initialize_database():
    """
    Initializes the SQLite database and creates the 'videos' table if it doesn't exist.
    """
    # Ensure the data directory exists
    os.makedirs(DATABASE_DIR, exist_ok=True)

    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Create table to store video information
        # Storing video_id as primary key to prevent duplicates
        # Storing title and channel_title for context, though not strictly required by the prompt
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                title TEXT,
                channel_title TEXT,
                view_count INTEGER,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        print(f"Database initialized successfully at {DATABASE_PATH}")
        print("Table 'videos' is ready.")
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("Setting up the database...")
    initialize_database()
