from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
import pandas as pd
from datetime import datetime
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import re
import sqlite3
from googleapiclient.errors import HttpError





# #Chatbot
from chatbot.model import chatbot
from chatbot.chatbot_logic import YouTubeChatbot
from services.youtube_analysis import search_channel, get_channel_data, fetch_videos_from_channel
from chatbot.model import ChatbotModel
from chatbot.utils import generate_follow_up_question



# Create instances of the necessary components
chatbot_model = ChatbotModel()
chatbot_logic = YouTubeChatbot(chatbot_model)


#databases and services
from database.trend_db import insert_trending_video
from database.report_trend_db import get_weekly_trending_data,save_report
from services.report_generation_trend import generate_groq_response
from services.transcription_analysis import TranscriptionAnalyzer
from services.channel_insights import get_channel_insights
from database.channel_db import calculate_spike_percentage , get_previous_video_stats, store_spike_data
from services.sentiment_analysis import analyze_sentiment
from services.emotion_analysis import EmotionAnalyzer


app = Flask(__name__)
app.secret_key = os.urandom(24)

# Load environment variables
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

# Initialize YouTube API
youtube = build("youtube", "v3", developerKey=API_KEY)

# # Initialize NLTK components
# nltk.download('vader_lexicon')
# nltk.download('punkt')
# nltk.download('stopwords')
# sia = SentimentIntensityAnalyzer()

# Main routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/channel-insights')
def channel_insights():
    return render_template('channel_insights.html')

@app.route('/video-analytics')
def video_analytics():
    return render_template('video_analytics.html')

@app.route('/sentiment-analysis')
def sentiment_analysis():
    return render_template('sentiment_analysis.html')

@app.route('/trending-videos')
def trending_videos():
    return render_template('trending_videos.html')

@app.route('/personalized-recommendations')
def personalized_recommendations():
    return render_template('personalized_recommendation.html')

@app.route('/thumbnail-generation')
def thumbnail_generation():
    return render_template("thumbnail_generator.html")

@app.route('/transcription-analysis')
def transcription_analysis():
    return render_template('transcription_analysis.html')

@app.route("/content-moderation-agent")
def content_moderation():
    return render_template("content_moderation_agent.html")

@app.route("/video-content-creator")
def video_creation():
    return render_template("video_content_creator.html")



#Flask route to Features 
# Channel Insights Analysis
@app.route('/api/analyze-channel', methods=['POST'])
def analyze_channel():
    try:
        data = request.get_json()
        channel_name = data.get('channel_name')

        if not channel_name:
            return jsonify({'error': 'Channel name is required'}), 400

        # Delegate all analysis to services/channel_insights.py
        result = get_channel_insights(channel_name)

        if 'error' in result:
            return jsonify({'error': result['error']}), 404 if result['error'] == 'Channel not found' else 500

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    



# Video Analytics for searched channel and searched video 

def save_to_csv(video_data, file_name="video_insights.csv"):
    """
    Save video data to a CSV file.
    """
    df = pd.DataFrame(video_data)
    df.to_csv(file_name, index=False)
    print(f"Video data saved to {file_name}")


def calculate_engagement_rate(dislikes, views, comments, likes):
    """
    Calculate engagement rate.
    """
    total_engagement = likes + comments  # Dislikes are optional
    return (total_engagement / views * 100) if views > 0 else 0


def fetch_video_metadata(youtube, channel_name, video_title=None, max_videos=15):
    """
    Fetch video metadata based on a channel name and optional video title.
    """
    try:
        # Search for the channel ID by channel name
        search_response = youtube.search().list(
            q=channel_name, part="snippet", type="channel", maxResults=1
        ).execute()

        if not search_response or "items" not in search_response or not search_response["items"]:
            return {"error": "Channel not found!"}

        channel_id = search_response["items"][0]["id"]["channelId"]

        # Search for videos in the channel
        video_search_response = youtube.search().list(
            q=video_title if video_title else "",
            part="snippet",
            type="video",
            channelId=channel_id,
            maxResults=max_videos,
        ).execute()

        if not video_search_response or "items" not in video_search_response or not video_search_response["items"]:
            return {"error": f"No videos found in channel '{channel_name}'!"}

        video_data_list = []
        for video_item in video_search_response["items"]:
            video_id = video_item["id"].get("videoId")
            if not video_id:
                continue  # Skip if videoId is missing

            # Fetch video details (views, likes, comments, etc.)
            video_details = youtube.videos().list(
                part="snippet,statistics", id=video_id
            ).execute()

            if not video_details or "items" not in video_details or not video_details["items"]:
                continue  # Skip if no details are found

            video_info = video_details["items"][0]
            snippet = video_info.get("snippet", {})
            statistics = video_info.get("statistics", {})

            # Get video metrics safely
            views = int(statistics.get("viewCount", 0))
            likes = int(statistics.get("likeCount", 0))
            comments = int(statistics.get("commentCount", 0))

             # Get video description (handle missing descriptions)
            description = snippet.get("description", "No description available")

            # Calculate engagement rate
            engagement_rate = calculate_engagement_rate(0, views, comments, likes)

            # Prepare video metadata
            video_data = {
                "Video Title": snippet.get("title", "N/A"),
                "Video ID": video_id,
                "Published Date": snippet.get("publishedAt", "N/A"),
                "Views": views,
                "Likes": likes,
                "Comments": comments,
                "Engagement Rate (%)": round(engagement_rate, 2),
                "Description": description,
            }
            video_data_list.append(video_data)

        if not video_data_list:
            return {"error": f"No valid videos found for channel '{channel_name}'!"}

        # Save all video data to CSV
        save_to_csv(video_data_list, "video_insights.csv")
        return video_data_list

    except Exception as e:
        return {"error": f"Error fetching video metadata: {str(e)}"}



# Video Analytics API and video analytics with report generation 
@app.route("/api/analyze-video", methods=["POST"])
def analyze_video():
    """
    Fetch video analytics by searching based on the channel name.
    Optionally, fetch analytics for a specific video title.
    """
    try:
        data = request.get_json()
        channel_name = data.get("channel_name")
        video_title = data.get("video_title", None)  # Optional

        if not channel_name:
            return jsonify({"error": "Channel name is required!"})

        # Fetch video metadata
        video_metadata = fetch_video_metadata(youtube, channel_name, video_title)

        if "error" in video_metadata:
            return jsonify(video_metadata)

        return jsonify(video_metadata)

    except Exception as e:
        return jsonify({"error": str(e)})




#Analyze Sentiment and Emotions 
# Initialize the emotion analyzer
try:
    emotion_analyzer = EmotionAnalyzer()
except Exception as e:
    logging.error(f"EmotionAnalyzer init failed: {str(e)}")
    raise



@app.route('/api/analyze-sentiment', methods=['POST'])
def analyze_sentiment_route():
    return analyze_sentiment()

@app.route('/api/analyze-emotions', methods=['POST'])
def analyze_emotions():
    logging.debug("Emotions route called")
    try:
        data = request.get_json()
        if not data or 'channel_name' not in data or 'video_title' not in data:
            return jsonify({'error': 'Missing channel_name or video_title'}), 400

        channel_name = data['channel_name'].strip()
        video_title = data['video_title'].strip()
        max_results = data.get('max_results', 100)

        if not channel_name or not video_title:
            return jsonify({'error': 'Please provide both Channel Name and Video Title'}), 400

        from services.sentiment_analysis import search_video  # Absolute import
        video_id = search_video(channel_name, video_title)
        logging.debug(f"Video ID: {video_id}")

        if not video_id:
            return jsonify({'error': f'No video found for "{video_title}" in "{channel_name}"'}), 404

        results = emotion_analyzer.analyze_video_emotions(video_id, max_results)
        logging.debug(f"Emotion results: {results}")

        response = {
            'status': 'success',
            'video_id': results['video_id'],
            'emotion_summary': results['emotion_summary'],
            'comments_analysis': [
                {'text': comment, 'emotion': emotion} for comment, emotion in results['predictions']
            ]
        }
        return jsonify(response), 200

    except HttpError as e:
        logging.error(f"YouTube API error: {str(e)}")
        return jsonify({'error': f'YouTube API error: {str(e)}'}), 500
    except Exception as e:
        logging.error(f"Emotion analysis error: {str(e)}")
        return jsonify({'error': f'Error analyzing emotions: {str(e)}'}), 500


# Trending Videos Analysis
@app.route('/api/analyze-trending', methods=['POST'])
def analyze_trending():
    try:
        data = request.get_json()
        region_code = data.get('region_code', 'US')
        
        # Get trending videos
        trending_response = youtube.videos().list(
            part='snippet,statistics',
            chart='mostPopular',
            regionCode=region_code,
            maxResults=10
        ).execute()

        trending_videos = []
        categories = {}
        
        for video in trending_response.get('items', []):
            snippet = video['snippet']
            stats = video['statistics']
            video_id = video['id']
            
            # Get category name
            category_id = snippet['categoryId']
            if category_id not in categories:
                category_response = youtube.videoCategories().list(
                    part='snippet',
                    id=category_id
                ).execute()
                categories[category_id] = category_response['items'][0]['snippet']['title']
            
            # Calculate engagement rate
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            comments = int(stats.get('commentCount', 0))
            engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0
            
            video_data={
                "video_id": video_id,
                'title': snippet['title'],
                "region": region_code,
                'channel': snippet['channelTitle'],
                'category': categories[category_id],
                'views': views,
                'likes': likes,
                'comments': comments,
                'engagement_rate': round(engagement_rate, 2),
                'publish_date': snippet['publishedAt']
            }

            # Save to database
            insert_trending_video(video_data)

            trending_videos.append(video_data)


        # Calculate category distribution
        category_distribution = {}
        for video in trending_videos:
            category = video['category']
            category_distribution[category] = category_distribution.get(category, 0) + 1

        return jsonify({
            'trending_videos': trending_videos,
            'category_distribution': category_distribution
        })


    except Exception as e:
        return jsonify({'error': str(e)})
    



#Route for Report Generation
@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    try:
        print("Starting report generation...") # Debug log
        data = request.get_json() or {}
        selected_region = data.get('region',None)
        
        trending_data = get_weekly_trending_data(selected_region)
        print("Trending data:", trending_data) # Debug log
        
        if not trending_data or trending_data == "No trending data available for the past week.":
            return jsonify({"error": "No trending data available"}), 404
        
        prompt = f"""
        Analyze the following YouTube trending data for the past week and generate a report highlighting:
        - Top 3 most engaging videos and why they performed well.
        - Which categories dominated the trends?
        - Any noticeable shifts or emerging patterns?
        - Also try to give detailed explaination of the report such as to understand where is the flaw in their content that they are making such as to make their content trendy 
        Data:
        {trending_data}
        """

        print("Generated Prompt:", prompt) # Debug log

        ai_report = generate_groq_response(prompt)
        print("AI Response:", ai_report) # Debug log

        if isinstance(ai_report, str) and "Error" in ai_report:
            return jsonify({"error": ai_report}), 500

        if not ai_report:
            return jsonify({"error": "Empty report generated"}), 500

        save_report(ai_report,selected_region)  # Save report to DB

        print("Final response being sent:", {"report": ai_report}) # Debug log
        return jsonify({"report": ai_report})

    except Exception as e:
        print("Exception occurred:", str(e)) # Debug log
        import traceback
        traceback.print_exc()  # Print full stack trace
        return jsonify({"error": str(e)}), 500
    





#personalized_video_recommendation
@app.route('/api/analyze', methods=['POST'])
def analyze_channel_data():
    """Analyze the given YouTube channel and genre."""
    data = request.json
    channel_name = data.get('channel_name')
    genre = data.get('genre')

    if not channel_name or not genre:
        return jsonify({'error': 'Channel name and genre are required'}), 400

    try:
        # Fetch actual channel data (use existing functions like search_channel, get_channel_data)
        print(f"Fetching channel data for: {channel_name}")
        channel_id = search_channel(channel_name)  # Ensure search_channel is defined elsewhere
        if not channel_id:
            return jsonify({'error': 'Channel not found'}), 404
        
        print(f"Fetched channel ID: {channel_id}")
        subscribers, _ = get_channel_data(channel_id)  # Ensure get_channel_data is defined elsewhere
        if subscribers is None:
            return jsonify({'error': 'Failed to fetch channel data'}), 500
        
        print(f"Subscribers: {subscribers}")
        
        # Fetch recent videos for engagement analysis
        print(f"Fetching videos for channel: {channel_name}")
        videos = fetch_videos_from_channel(channel_name)  # Ensure fetch_videos_from_channel is defined elsewhere
        if not videos:
            return jsonify({'error': 'Failed to fetch videos from channel'}), 500
        
        print(f"Fetched {len(videos)} videos")

        # Calculate total views
        total_views = sum(video.get('view_count', 0) for video in videos)

        # Determine top content (can be based on highest views or engagement)
        top_video = max(videos, key=lambda x: x.get('view_count', 0))  # Adjust as needed for engagement
        top_content = top_video.get('title', 'N/A')  # You can also include the view count or engagement here

        # Calculate audience engagement (average likes + comments)
        engagement_scores = [
            (video.get('like_count', 0) + video.get('comment_count', 0)) for video in videos
        ]
        average_engagement = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0
        audience_engagement = "High Engagement" if average_engagement > 1000 else "Low Engagement"  # Adjust the threshold

        # Placeholder recommendations (you can improve this using engagement analysis)
        recommendations = [
            "Try a trending tutorial in your genre",
            "Engage with your audience through Q&A videos",
            "Experiment with shorts and reaction content"
        ]

        analysis_result = {
            "subscribers": f"{subscribers:,}",
            "total_views": f"{total_views:,}",
            "video_count": len(videos),
            "top_content": top_content,  # Top performing content
            "genre_distribution": genre.capitalize(),
            "audience_engagement": audience_engagement,
            "recommendations": recommendations
        }

        return jsonify(analysis_result)

    except Exception as e:
        print(f"Error: {str(e)}")  # Added to help debug
        return jsonify({'error': str(e)}), 500


#Recommendation ChatBot
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/api/chatbot', methods=['POST'])
def chatbot_response():
    """Generate chatbot response based on user input, channel name, and genre."""
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    data = request.json
    user_input = data.get('user_input')
    channel_name = data.get('channel_name')
    genre = data.get('genre')
    
    if not user_input:
        return jsonify({'error': 'User input is required'}), 400
    
    try:
        # Generate response using model
        bot_response = chatbot.generate_response(
            user_input=user_input,
            channel_name=channel_name,
            genre=genre
        )

        # Handle error responses gracefully
        if "⚠️" in bot_response:
            error_msg = bot_response.split("⚠️")[1].strip()
            return jsonify({
                "bot_response": "Sorry, I couldn’t process that request.",
                "error": error_msg,
                "follow_up": "Can you provide more details or try a different question?"
            })

        # Generate follow-up using utils.py for better intent detection
        follow_up = generate_follow_up_question(user_input, genre) if genre else "How can I assist you further?"

        response = {
            "bot_response": bot_response,
            "follow_up": follow_up
        }
        logger.info(f"Chatbot response generated for input: {user_input}")
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error in chatbot_response: {str(e)}")
        return jsonify({
            "bot_response": "Oops, something went wrong!",
            "error": str(e),
            "follow_up": "Please try again or contact support."
        }), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_recommendation():
    """Analyze channel based on name and genre."""
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    data = request.json
    channel_name = data.get('channel_name')
    genre = data.get('genre')
    
    logger.info(f"Analyzing channel: {channel_name}, Genre: {genre}")
    
    if not channel_name or not genre:
        return jsonify({'error': 'Channel name and genre are required'}), 400
    
    try:
        # Use the analyze_channel method
        analysis = chatbot.analyze_channel(channel_name, genre)
        
        # Check for error in analysis response
        if "error" in analysis:
            return jsonify({
                "error": analysis["error"],
                "status": analysis.get("status", 400)
            }), analysis.get("status", 400)
        
        logger.info(f"Analysis completed for {channel_name}")
        return jsonify(analysis)
        
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        error_message = str(e)
        if "API_KEY" in error_message:
            error_message = "API configuration error. Please try again later."
        return jsonify({'error': error_message}), 500


#Transcription  Analysis
@app.route('/api/analyze-transcription', methods=['POST'])
def analyze_transcription():
    """Analyze a YouTube video transcript based on channel name and video title."""
    try:
        data = request.get_json()
        channel_name = data.get('channelName')
        video_title = data.get('videoTitle')

        if not channel_name or not video_title:
            return jsonify({'error': 'Channel name and video title are required'}), 400

        analyzer = TranscriptionAnalyzer(channel_name, video_title)
        results = analyzer.run_analysis()

        if results is None:
            return jsonify({'error': 'Analysis failed. Video might not exist or have no transcript available.'}), 404

        return jsonify(results)

    except Exception as e:
        return jsonify({'error': f"An unexpected error occurred: {str(e)}"}), 500
    



from services.video_content import VideoContentService

video_content_service = VideoContentService()

@app.route("/api/generate-titles", methods=["POST"])
def generate_titles():
    data = request.json
    video_description = data.get("video_description")
    num_titles = data.get("num_titles", 5)
    titles = video_content_service.generate_titles(video_description, num_titles)
    return jsonify({"titles": titles})



from groq import GroqError
@app.route("/api/generate-script", methods=["POST"])
def generate_script():
    try:
        data = request.json
        content_idea = data.get("content_idea")
        video_length = data.get("video_length", 5)
        tone = data.get("tone", "casual")

        if not content_idea:
            return jsonify({"message": "Content idea is required."}), 400
        if not isinstance(video_length, (int, float)) or video_length < 1 or video_length > 30:
            return jsonify({"message": "Video length must be between 1 and 30 minutes."}), 400

        script = video_content_service.generate_script(content_idea, video_length, tone)
        return jsonify({"script": script})
    except GroqError as e:
        return jsonify({"message": f"Groq API error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"message": f"Server error: {str(e)}"}), 500
    
@app.route("/api/suggest-keywords", methods=["POST"])
def suggest_keywords():
    try:
        data = request.json
        description = data.get("description")
        keywords = video_content_service.suggest_keywords(description)
        if not keywords and not description:
            return jsonify({"message": "Description is required."}), 400
        return jsonify({"keywords": keywords})
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)