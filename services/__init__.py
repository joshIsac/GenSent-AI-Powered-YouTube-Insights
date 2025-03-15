from googleapiclient.discovery import build
import os 
from dotenv import load_dotenv

load_dotenv()

# YouTube API setup (replace with your actual API key)
API_KEY = os.getenv("YOUTUBE_API_KEY")

# Initialize the YouTube API client
youtube = build('youtube', 'v3', developerKey=API_KEY)

# This makes the youtube client available when importing the package
__all__ = ['youtube']