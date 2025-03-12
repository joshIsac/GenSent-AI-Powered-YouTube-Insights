import re
from flask import jsonify, request
from . import youtube
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from googleapiclient.errors import HttpError
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

nltk.download('vader_lexicon')
nltk.download('punkt')
nltk.download('stopwords')

sia = SentimentIntensityAnalyzer()

def search_video(channel_name, video_title):
    """Search for a YouTube video using channel name and video title."""
    search_response = youtube.search().list(
        q=f"{channel_name} {video_title}",
        type="video",
        part="id,snippet",
        maxResults=1
    ).execute()

    if "items" in search_response and search_response["items"]:
        return search_response["items"][0]["id"]["videoId"]
    return None

def get_latest_video_by_channel(channel_name):
    """Fetch the latest video uploaded by a YouTube channel."""
    search_response = youtube.search().list(
        part="snippet",
        q=channel_name,
        type="channel",
        maxResults=1
    ).execute()

    if not search_response.get("items"):
        return None

    channel_id = search_response["items"][0]["id"]["channelId"]

    videos_response = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        order="date",
        type="video",
        maxResults=1
    ).execute()

    if not videos_response.get("items"):
        return None

    return videos_response["items"][0]["id"]["videoId"]


def analyze_sentiment():
    try:
        data = request.get_json()
        channel_name = data.get('channel_name', '').strip()
        video_title = data.get('video_title', '').strip()

        if not channel_name:
            return jsonify({'error': 'Please provide a Channel Name first'}), 400

        if not video_title:
            return jsonify({'error': 'Please provide a Video Title from the selected channel'}), 400

        # Search for video in the provided channel
        video_id = search_video(channel_name, video_title)

        if not video_id:
            return jsonify({'error': f'No matching video found for "{video_title}" in "{channel_name}". Please enter a video from the selected channel.'}), 404

        # Fetch video comments
        comments_response = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            textFormat='plainText',
            maxResults=100,
            order='time'
        ).execute()

        if 'items' not in comments_response:
            return jsonify({'error': 'No comments found'}), 404

        comments_analysis = []
        sentiment_distribution = {'positive': 0, 'neutral': 0, 'negative': 0}

        for item in comments_response['items']:
            comment_text = item['snippet']['topLevelComment']['snippet']['textDisplay']
            
            # Clean comment text
            cleaned_text = re.sub(r'[^a-zA-Z\s]', '', comment_text.lower())

            # Analyze sentiment
            sentiment_scores = sia.polarity_scores(cleaned_text)
            compound_score = sentiment_scores['compound']

            # Determine sentiment category
            if compound_score >= 0.05:
                sentiment = 'positive'
            elif compound_score <= -0.05:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
                
            sentiment_distribution[sentiment] += 1

            comments_analysis.append({
                'text': comment_text,
                'sentiment': sentiment,
                'score': compound_score
            })

        return jsonify({
            'sentiment_distribution': sentiment_distribution,
            'comments_analysis': comments_analysis
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

