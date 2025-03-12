import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from database.personalized_recommendations_db import store_video_data

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=API_KEY)

def search_channel(channel_name):
    """Search for a channel by name and return channel ID."""
    try:
        response = youtube.search().list(
            q=channel_name,
            type="channel",
            part="snippet",
            maxResults=1
        ).execute()
        
        items = response.get("items", [])
        if not items:
            raise ValueError(f"Channel '{channel_name}' not found.")
        
        return items[0]["id"]["channelId"]
    except HttpError as e:
        raise Exception(f"API error searching channel: {str(e)}")

def get_channel_data(channel_id):
    """Fetch channel subscriber count and title."""
    try:
        response = youtube.channels().list(
            id=channel_id,
            part="snippet,statistics"
        ).execute()
        
        if not response.get("items"):
            raise ValueError(f"Channel details not found for ID '{channel_id}'.")
        
        item = response["items"][0]
        return int(item["statistics"].get("subscriberCount", 0)), item["snippet"].get("title", "")
    except HttpError as e:
        raise Exception(f"API error fetching channel data: {str(e)}")

def fetch_video_metadata(video_id):
    """Fetch video metadata and engagement metrics (renamed for clarity)."""
    try:
        response = youtube.videos().list(
            id=video_id,
            part="snippet,statistics"
        ).execute()
        
        if not response.get("items"):
            return None
        
        item = response["items"][0]
        snippet = item["snippet"]
        stats = item["statistics"]

        return {
            "video_id": video_id,
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "tags": ", ".join(snippet.get("tags", [])) if snippet.get("tags") else None,
            "category_id": snippet.get("categoryId"),
            "publish_date": snippet.get("publishedAt"),
            "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
            "comment_count": int(stats.get("commentCount", 0))
        }
    except HttpError as e:
        raise Exception(f"API error fetching video metadata: {str(e)}")

def fetch_videos_from_channel(channel_name):
    """Fetch recent videos for a given channel and store in database."""
    try:
        channel_id = search_channel(channel_name)
        subscriber_count, _ = get_channel_data(channel_id)

        response = youtube.search().list(
            channelId=channel_id,
            part="snippet",
            type="video",
            order="date",
            maxResults=5
        ).execute()

        if 'items' not in response or not response['items']:
            return []  # Empty list signals no videos, handled in chatbot_logic.py

        videos = []
        for item in response["items"]:
            video_id = item["id"]["videoId"]
            video_data = fetch_video_metadata(video_id)
            if video_data:
                videos.append(video_data)
                store_video_data(video_data, channel_id, subscriber_count)

        return videos

    except HttpError as e:
        raise Exception(f"API error fetching videos: {str(e)}")
    except Exception as e:
        raise Exception(f"Error fetching videos: {str(e)}")

def fetch_video_details(channel_name, analysis_type="sentiment"):
    """Fetch video details, including comments for sentiment analysis."""
    try:
        videos = fetch_videos_from_channel(channel_name)
        if not videos:
            return []

        # Use the most recent video for comment analysis
        video_id = videos[0]["video_id"]

        response = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=20,
            textFormat="plainText"
        ).execute()

        comments = []
        for item in response.get("items", []):
            comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            # Basic sentiment heuristic (replace with NLP library if available)
            sentiment = (
                "positive" if any(word in comment.lower() for word in ["good", "great", "love"]) else
                "negative" if any(word in comment.lower() for word in ["bad", "hate", "terrible"]) else
                "neutral"
            )
            comments.append({"text": comment, "sentiment": sentiment})

        return comments

    except HttpError as e:
        raise Exception(f"API error fetching comments: {str(e)}")
    except Exception as e:
        raise Exception(f"Error fetching video details: {str(e)}")