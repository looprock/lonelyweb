#!/usr/bin/env python

import sqlite3
import time
import os
import argparse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import random
import datetime # For more advanced query generation if needed

# Database path (relative to this script's location)
# Assumes db_setup.py created the 'data' directory and the DB file within it.
DATABASE_DIR = os.path.join(os.path.dirname(__file__), 'data')
DATABASE_PATH = os.path.join(DATABASE_DIR, 'youtube_videos.db')

# YouTube API settings
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

# Target number of videos to collect (now a command-line argument, see below)
# TARGET_VIDEO_COUNT = 50000
MAX_VIEWS = 49 # Videos with less than 50 views

# --- Database Functions ---

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row # Access columns by name
    return conn

def insert_video(conn, video_id, url, title, channel_title, view_count):
    """Inserts a video into the database."""
    try:
        with conn: # context manager handles commit/rollback
            conn.execute(
                """
                INSERT INTO videos (video_id, url, title, channel_title, view_count)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(video_id) DO NOTHING
                """, # ON CONFLICT ensures we don't try to insert duplicates
                (video_id, url, title, channel_title, view_count)
            )
        return True
    except sqlite3.IntegrityError:
        # This can happen if somehow a duplicate URL is found for a different video_id,
        # or if video_id conflict happens despite ON CONFLICT (should be handled by ON CONFLICT)
        # print(f"Integrity error for video_id {video_id}, likely already exists or URL unique constraint.")
        return False # Already exists or other integrity issue
    except sqlite3.Error as e:
        print(f"Database error inserting video {video_id}: {e}")
        return False

def get_collected_video_count(conn):
    """Gets the current number of videos in the database."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(video_id) FROM videos")
        count = cursor.fetchone()[0]
        return count
    except sqlite3.Error as e:
        print(f"Database error getting video count: {e}")
        return 0

# --- YouTube API Functions ---

def get_youtube_service(api_key):
    """Initializes and returns the YouTube API service client."""
    try:
        return build(API_SERVICE_NAME, API_VERSION, developerKey=api_key)
    except Exception as e:
        print(f"Error building YouTube service: {e}")
        return None

# --- Main Collection Logic ---

def generate_random_search_query():
    """
    Generates somewhat random search queries. This is a CRITICAL part
    for effectively finding very low-view-count videos and needs careful tuning.
    """
    # Strategies:
    # 1. Obscure terms / "garbage" strings: "asdflkjh", "qwertyuiop"
    # 2. Common words combined randomly: "new test video", "my cat upload"
    # 3. Highly specific niche terms (user might need to supply a list)
    # 4. Filter by recent upload date (e.g., `publishedAfter`, `publishedBefore` in search_videos)
    #    This requires converting datetime to RFC 3339 format (e.g., 'YYYY-MM-DDTHH:MM:SSZ').

    common_words = [
        "my", "first", "video", "test", "upload", "game", "vlog", "cat", "dog", "trip",
        "project", "school", "class", "tutorial", "review", "demo", "unboxing",
        "family", "holiday", "birthday", "drone", "gopro", "footage", "random",
        "clip", "short", "experiment", "new", "daily", "raw"
    ]

    # Mix of strategies
    strategy = random.choice(["garbage", "common_combo", "single_common_permuted"])

    if strategy == "garbage":
        return "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=random.randint(5, 10)))
    elif strategy == "common_combo":
        num_words = random.randint(1, 3)
        return " ".join(random.sample(common_words, num_words))
    elif strategy == "single_common_permuted":
        base_word = random.choice(common_words)
        # Add some random chars to common words
        if random.random() < 0.5:
            return base_word + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=random.randint(1,3)))
        return base_word

    # Default fallback (should be covered by above)
    return "video"


def search_videos(youtube, query, page_token=None, published_after=None, published_before=None):
    """Searches for videos on YouTube."""
    try:
        request_params = {
            'q': query,
            'part': 'id,snippet', # snippet includes title, channelTitle
            'type': 'video',
            'maxResults': 50,  # Max allowed
            'pageToken': page_token,
            'order': 'date', # Prioritize recently uploaded videos
            # 'videoEmbeddable': 'true', # Optional
            # 'videoSyndicated': 'true' # Optional
        }
        if published_after:
            request_params['publishedAfter'] = published_after
        if published_before:
            request_params['publishedBefore'] = published_before

        search_response = youtube.search().list(**request_params).execute()
        return search_response
    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred during search: {e.content.decode()}")
        if e.resp.status == 403: # Quota likely exceeded
            print("Quota likely exceeded (search). Please check your YouTube API quota.")
            raise # Reraise to stop execution or handle upstream
        return None
    except Exception as e:
        print(f"An error occurred during search: {e}")
        return None

def get_video_details(youtube, video_ids_str):
    """Fetches details (including view count) for a list of video IDs."""
    try:
        video_response = youtube.videos().list(
            part='snippet,statistics', # snippet for title, statistics for viewCount
            id=video_ids_str # Comma-separated string of video IDs
        ).execute()
        return video_response
    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred fetching video details: {e.content.decode()}")
        if e.resp.status == 403: # Quota likely exceeded
            print("Quota likely exceeded (details). Please check your YouTube API quota.")
            raise # Reraise
        return None
    except Exception as e:
        print(f"An error occurred fetching video details: {e}")
        return None

def main(api_key, target_videos_to_collect):
    print("Starting YouTube video collection...")
    print(f"IMPORTANT: This script uses the YouTube Data API. Each search costs 100 units,")
    print(f"and fetching details for up to 50 videos costs 1 unit (for statistics part).")
    print(f"The default daily quota is 10,000 units. Collecting {target_videos_to_collect} videos")
    print(f"with less than {MAX_VIEWS+1} views will likely take a very long time and exceed")
    print(f"daily quotas multiple times. Be patient and monitor your API usage.")
    print("Consider refining search queries (generate_random_search_query function) for better efficiency.\n")

    conn = get_db_connection()
    if not conn:
        print("Failed to connect to the database. Exiting.")
        return

    youtube = get_youtube_service(api_key)
    if not youtube:
        print("Failed to initialize YouTube service. Exiting.")
        conn.close()
        return

    collected_count = get_collected_video_count(conn)
    print(f"Initially found {collected_count} videos in the database.")

    search_page_token = None
    consecutive_empty_batches = 0 # How many times in a row we found 0 matching videos
    MAX_CONSECUTIVE_EMPTY_BATCHES = 50 # Stop if too many batches yield nothing

    try:
        while collected_count < target_videos_to_collect:
            current_query = generate_random_search_query()
            # Optional: Define a time window for 'publishedAfter'/'publishedBefore'
            # e.g., search videos from the last few hours/days to increase chances of low views
            # published_after_dt = datetime.datetime.utcnow() - datetime.timedelta(days=1)
            # published_after_str = published_after_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            # published_before_str = None (or specific end time)

            print(f"\nSearching with query: '{current_query}' (Page token: {search_page_token if search_page_token else 'None'})")

            try:
                search_result = search_videos(youtube, current_query, page_token=search_page_token) #, published_after=published_after_str)
            except HttpError:
                print("Stopping due to API quota error during search.")
                break

            if not search_result or not search_result.get('items'):
                print("No search results or API error. Trying next query.")
                search_page_token = None # Reset page token for new query
                consecutive_empty_batches +=1
                if consecutive_empty_batches > MAX_CONSECUTIVE_EMPTY_BATCHES / 2: # Be more aggressive if stuck on one query
                    print(f"Many empty results on this query type, trying a new query type after delay.")
                    time.sleep(random.uniform(5,10))
                else:
                    time.sleep(random.uniform(1,3))
                continue

            video_ids = [item['id']['videoId'] for item in search_result['items'] if item['id'].get('videoId')]

            if not video_ids:
                print("No video IDs found in search result items. Advancing search page or query.")
                search_page_token = search_result.get('nextPageToken')
                if not search_page_token:
                    search_page_token = None
                    time.sleep(random.uniform(2,4)) # Pause before new query
                else:
                    time.sleep(random.uniform(0.5,1.5)) # Pause before next page
                continue

            # print(f"Found {len(video_ids)} video IDs from search. Fetching details...")
            video_ids_str = ','.join(video_ids)

            try:
                details_result = get_video_details(youtube, video_ids_str)
            except HttpError:
                print("Stopping due to API quota error during video details fetch.")
                break

            if not details_result or not details_result.get('items'):
                print("No video details found or API error. Advancing search page or query.")
                search_page_token = search_result.get('nextPageToken')
                if not search_page_token:
                    search_page_token = None
                    time.sleep(random.uniform(2,4))
                else:
                    time.sleep(random.uniform(0.5,1.5))
                continue

            videos_added_this_batch = 0
            for video_item in details_result['items']:
                video_id = video_item['id']
                title = video_item['snippet']['title']
                channel_title = video_item['snippet']['channelTitle']
                view_count_str = video_item.get('statistics', {}).get('viewCount')

                if view_count_str is None:
                    continue

                try:
                    view_count = int(view_count_str)
                except ValueError:
                    # print(f"Could not parse view count '{view_count_str}' for video {video_id}. Skipping.")
                    continue

                if view_count <= MAX_VIEWS:
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    if insert_video(conn, video_id, video_url, title, channel_title, view_count):
                        # print(f"  Stored: {video_id} (Views: {view_count}) - \"{title[:50]}...\"")
                        videos_added_this_batch += 1
                        collected_count += 1
                        if collected_count % 10 == 0 or videos_added_this_batch == 1: # Print progress periodically
                             print(f"Progress: {collected_count}/{target_videos_to_collect} videos collected.")
                        if collected_count >= target_videos_to_collect:
                            break

            if videos_added_this_batch > 0:
                print(f"Added {videos_added_this_batch} new videos in this batch. Total collected: {collected_count}/{target_videos_to_collect}")
                consecutive_empty_batches = 0 # Reset counter
            else:
                # print("No videos matching criteria in this batch.")
                consecutive_empty_batches += 1


            if collected_count >= target_videos_to_collect:
                print(f"\nTarget of {target_videos_to_collect} videos reached!")
                break

            if consecutive_empty_batches >= MAX_CONSECUTIVE_EMPTY_BATCHES:
                print(f"Stopped after {MAX_CONSECUTIVE_EMPTY_BATCHES} consecutive empty batches. Consider revising search strategy.")
                break

            search_page_token = search_result.get('nextPageToken')
            if not search_page_token:
                # print("No more pages for current query. Moving to new query.")
                search_page_token = None
                time.sleep(random.uniform(2, 5))
            else:
                time.sleep(random.uniform(0.5, 1.5))

    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"An unexpected error occurred in main loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        current_db_count = get_collected_video_count(conn) # Get final count before closing
        if conn:
            conn.close()
        print(f"Finished. Total videos in database: {current_db_count}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Collect YouTube video URLs with low view counts.")
    parser.add_argument("api_key", help="Your YouTube Data API v3 key.")
    parser.add_argument("-n", "--num_videos", type=int, default=50000,
                        help="Target number of videos to collect (default: 50000).")

    args = parser.parse_args()

    if not os.path.exists(DATABASE_PATH):
        print(f"Database file not found at {DATABASE_PATH}")
        print(f"Please run lonelyweb/youtube_collector/db_setup.py first to initialize the database.")
        print("Example: python lonelyweb/youtube_collector/db_setup.py")
        exit(1)

    main(args.api_key, args.num_videos)
