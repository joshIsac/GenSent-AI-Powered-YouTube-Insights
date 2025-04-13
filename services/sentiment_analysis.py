import re
from flask import jsonify, request
from . import youtube
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from googleapiclient.errors import HttpError
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import nltk
import torch
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)


sia = SentimentIntensityAnalyzer()

# Initialize BERT for 5-class sentiment (pre-trained, not fine-tuned)
tokenizer = AutoTokenizer.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")
model = AutoModelForSequenceClassification.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

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


def predict_bert_sentiment(text):
    """Predict 5-class sentiment using pre-trained BERT model."""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    logits = outputs.logits
    pred = torch.argmax(logits, dim=1).cpu().item()
    sentiment_map = {0: "very negative", 1: "negative", 2: "neutral", 3: "positive", 4: "very positive"}
    return sentiment_map[pred], pred

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
        sentiment_distribution = {
            'very negative': 0, 'negative': 0, 'neutral': 0, 'positive': 0, 'very positive': 0
        }

        
        for item in comments_response['items']:
            comment_text = item['snippet']['topLevelComment']['snippet']['textDisplay']
            
            # Clean comment text
            cleaned_text = re.sub(r'[^a-zA-Z\s]', '', comment_text.lower())

            # Analyze sentiment
            sentiment_scores = sia.polarity_scores(cleaned_text)
            compound_score = sentiment_scores['compound']

            # BERT sentiment analysis
            bert_sentiment, bert_pred = predict_bert_sentiment(cleaned_text)

            # Hybrid sentiment logic
            if compound_score <= -0.5 and bert_pred <= 1:  # Strong negative from both
                final_sentiment = "very negative"
            elif compound_score <= -0.05 and bert_pred <= 2:  # Moderate negative
                final_sentiment = "negative"
            elif compound_score >= 0.5 and bert_pred >= 3:  # Strong positive from both
                final_sentiment = "very positive"
            elif compound_score >= 0.05 and bert_pred >= 2:  # Moderate positive
                final_sentiment = "positive"
            else:  # Default to neutral if mixed signals
                final_sentiment = "neutral"

            sentiment_distribution[final_sentiment] += 1

            comments_analysis.append({
                'text': comment_text,
                'sentiment': final_sentiment,
                'vader_score': compound_score,
                'bert_sentiment': bert_sentiment
            })

        return jsonify({
            'sentiment_distribution': sentiment_distribution,
            'comments_analysis': comments_analysis
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500