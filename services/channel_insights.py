# Standard library imports
import logging
import re
import statistics
from collections import Counter
from datetime import datetime

# Third-party imports
import pytz
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
from textblob import TextBlob

# Local imports
from database.channel_db import (
    get_previous_video_stats,
    calculate_spike_percentage,
    store_spike_data
)
from services import youtube


# Ensure consistent language detection
DetectorFactory.seed = 0

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_channel_insights(channel_name):
    """Fetch comprehensive channel insights including stats, videos, competitors, and demographics."""
    try:
        # Search for channel
        search_response = youtube.search().list(
            q=channel_name,
            type='channel',
            part='snippet',
            maxResults=1
        ).execute()

        if not search_response.get('items'):
            return {'error': 'Channel not found'}

        channel_id = search_response['items'][0]['id']['channelId']

        # Get channel statistics
        channel_response = youtube.channels().list(
            part='snippet,statistics,contentDetails,topicDetails',
            id=channel_id
        ).execute()

        channel_stats = channel_response['items'][0]['statistics']
        uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        channel_title = channel_response['items'][0]['snippet']['title']
        topics = channel_response['items'][0].get('topicDetails', {}).get('topicCategories', [])

        # Fetch recent videos
        video_response = youtube.playlistItems().list(
            part='snippet,contentDetails',
            playlistId=uploads_playlist_id,
            maxResults=15
        ).execute()

        videos_data = []
        for item in video_response.get('items', []):
            video_id = item['contentDetails']['videoId']
            video_stats = youtube.videos().list(
                part='statistics',
                id=video_id
            ).execute()

            if video_stats.get('items'):
                stats = video_stats['items'][0]['statistics']
                video_data = {
                    'title': item['snippet']['title'],
                    'views': int(stats.get('viewCount', 0)),
                    'likes': int(stats.get('likeCount', 0)),
                    'comments': int(stats.get('commentCount', 0)),
                    'publishedAt': item['snippet']['publishedAt'],
                    'contentDetails': {'videoId': video_id}
                }
                previous_stats = get_previous_video_stats(video_data['title'])
                video_data['spike_percentage'] = calculate_spike_percentage(
                    video_data['views'],
                    previous_stats.get('views', 0)
                )
                store_spike_data(
                    channel_id,
                    video_data['title'],
                    video_data['views'],
                    video_data['likes'],
                    video_data['comments'],
                    video_data['spike_percentage']
                )
                videos_data.append(video_data)

        # Competitor Benchmarking
        competitor_data = analyze_competitors(channel_name, channel_id, topics)

        # User Demographics & Interest Analysis
        demographics_data = analyze_demographics_and_interests(channel_id, videos_data, topics)

        # Calculate Channel Health Score (HCS = W1*E + W2*G + W3*V) using real API data
        total_views = sum(v['views'] for v in videos_data)
        total_likes = sum(v['likes'] for v in videos_data)
        total_comments = sum(v['comments'] for v in videos_data)
        total_subscribers = int(channel_stats.get('subscriberCount', 0))
        total_videos = int(channel_stats.get('videoCount', 0))

        # 1. Engagement Score (E) = (Likes + Comments) / Views * 100
        # Scale up to make it more impactful
        e_score = (
            (total_likes + total_comments) / total_views * 1000
            if total_views > 0 else 0
        )
        e_score = min(100, e_score)  # Cap at 100

        # 2. Growth Score (G) = (Subscribers / Total Videos) * Scaling Factor
        # Increase scaling factor to 1.0 for better balance
        g_score = (
            total_subscribers / total_videos * 1.0
            if total_videos > 0 else 0
        )
        g_score = min(100, g_score)  # Cap at 100

        # 3. Video Performance Score (V) = Avg Views per Recent Video / Max Possible Views * 100
        # Lower max_possible_views to 100,000 for more realistic scoring
        avg_views_per_video = total_views / len(videos_data) if videos_data else 0
        max_possible_views = 100000  # Adjusted for smaller channels
        v_score = (
            avg_views_per_video / max_possible_views * 100
            if max_possible_views > 0 else 0
        )
        v_score = min(100, v_score)  # Cap at 100

        # Weights (sum to 1.0)
        w1, w2, w3 = 0.4, 0.3, 0.3  # Engagement: 40%, Growth: 30%, Video Performance: 30%

        # Calculate HCS
        health_score = min(100, max(0, int(w1 * e_score + w2 * g_score + w3 * v_score)))

        # Calculate Content Consistency Index (Coefficient of Variation for Views)
        if videos_data:
            view_counts = [v['views'] for v in videos_data]
            mean_views = statistics.mean(view_counts)
            std_dev_views = statistics.stdev(view_counts) if len(view_counts) > 1 else 0
            cv_views = (std_dev_views / mean_views * 100) if mean_views > 0 else 0  # Coefficient of Variation (%)
            consistency_index = min(100, max(0, int(100 - cv_views)))  # Invert: higher consistency = higher score
        else:
            consistency_index = 0  # Default if no videos

        return {
            'channel_stats': {
                'title': channel_title,
                'subscribers': channel_stats.get('subscriberCount', '0'),
                'total_views': channel_stats.get('viewCount', '0'),
                'total_videos': channel_stats.get('videoCount', '0'),
                'recent_videos': videos_data,
                'health_score': health_score,  # Updated field
                'consistency_index': consistency_index  # Existing field
            },
            'competitor_benchmarking': competitor_data,
            'user_demographics': demographics_data
        }

    except Exception as e:
        return {'error': str(e)}


def analyze_competitors(channel_name, channel_id, topics):
    """Fetch and compare competitor channels with accurate engagement and upload frequency."""
    try:
        search_terms = channel_name.split()[0]
        if topics:
            topic_keyword = topics[0].split('/')[-1].lower()
            search_terms += f" {topic_keyword}"

        competitor_search = youtube.search().list(
            q=search_terms,
            type='channel',
            part='snippet',
            maxResults=5,
            order='relevance'
        ).execute()

        competitors = []
        for item in competitor_search.get('items', []):
            if item['id']['channelId'] == channel_id:
                continue
            comp_id = item['id']['channelId']
            comp_response = youtube.channels().list(
                part='snippet,statistics,contentDetails',
                id=comp_id
            ).execute()

            if not comp_response.get('items'):
                continue

            comp_stats = comp_response['items'][0]['statistics']
            comp_uploads_id = comp_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            comp_videos = youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=comp_uploads_id,
                maxResults=10
            ).execute()

            total_views = int(comp_stats.get('viewCount', 0))
            video_count = int(comp_stats.get('videoCount', 0))
            recent_videos = comp_videos.get('items', [])
            avg_views = total_views / video_count if video_count > 0 else 0

            # Calculate engagement rate for recent videos
            recent_views_sum = 0
            engagement_sum = 0
            for v in recent_videos:
                v_stats = youtube.videos().list(
                    part='statistics',
                    id=v['contentDetails']['videoId']
                ).execute()
                if v_stats.get('items'):
                    stats = v_stats['items'][0]['statistics']
                    views = int(stats.get('viewCount', 0))
                    recent_views_sum += views
                    engagement_sum += int(stats.get('likeCount', 0)) + int(stats.get('commentCount', 0))
            engagement_rate = (engagement_sum / recent_views_sum * 100) if recent_views_sum > 0 else 0

            # Calculate upload frequency (Method 2: Monthly Average)
            if recent_videos:
                publish_dates = [
                    datetime.strptime(v['snippet']['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')
                    for v in recent_videos
                ]
                if publish_dates:
                    min_date = min(publish_dates)
                    max_date = max(publish_dates)
                    months_span = (
                        (max_date.year - min_date.year) * 12 +
                        max_date.month - min_date.month + 1
                    )  # Months between min and max
                    upload_freq = len(recent_videos) / months_span if months_span > 0 else len(recent_videos)
                else:
                    upload_freq = 0
            else:
                upload_freq = 0

            competitors.append({
                'title': comp_response['items'][0]['snippet']['title'],
                'total_views': total_views,
                'avg_views': round(avg_views, 2),
                'engagement_rate': round(engagement_rate, 2),
                'upload_frequency': round(upload_freq, 2),
                'growth_trend': "N/A"
            })

        return competitors[:3]

    except Exception as e:
        return {'error': f"Competitor analysis failed: {str(e)}"}


def analyze_demographics_and_interests(channel_id, videos_data, topics=None):
    """Estimate audience demographics and interests for any channel using public data."""
    try:
        logger.info(f"Analyzing demographics for channel {channel_id}")

        # Fetch comments, descriptions, and tags from recent videos
        comments = []
        descriptions = []
        tags = []
        for video in videos_data[:10]:  # Increase to 10 videos for more data
            video_id = video.get('contentDetails', {}).get('videoId')
            if not video_id:
                continue
            # Fetch comments
            try:
                comment_response = youtube.commentThreads().list(
                    part='snippet',
                    videoId=video_id,
                    maxResults=50,  # Increase to 50 for richer sample
                    textFormat='plainText'
                ).execute()
                comments.extend([
                    item['snippet']['topLevelComment']['snippet']['textDisplay']
                    for item in comment_response.get('items', [])
                ])
            except Exception as e:
                logger.warning(f"Comments unavailable for {video_id}: {str(e)}")

            # Fetch video details (description, tags)
            try:
                video_response = youtube.videos().list(
                    part='snippet',
                    id=video_id
                ).execute()
                if video_response.get('items'):
                    video_item = video_response['items'][0]['snippet']
                    descriptions.append(video_item.get('description', '').lower())
                    tags.extend([tag.lower() for tag in video_item.get('tags', [])])
            except Exception as e:
                logger.warning(f"Video details unavailable for {video_id}: {str(e)}")

        logger.info(f"Collected {len(comments)} comments, {len(descriptions)} descriptions, {len(tags)} tags")

        # Interests
        interests = [topic.split('/')[-1].lower().replace('_', ' ') for topic in topics or []]
        stop_words = {'this', 'that', 'with', 'your', 'video', 'great', 'like', 'love', 'please', 'thanks'}
        if comments or descriptions or tags:
            all_text = ' '.join(comments + descriptions + tags).lower()
            words = all_text.split()
            common_words = Counter([
                w for w in words if w not in stop_words and len(w) > 3
            ]).most_common(10)
            interests.extend([
                word for word, _ in common_words if word not in interests
            ])
        else:
            interests.append("No sufficient data")
        interests = interests[:5]  # Limit to top 5
        logger.info(f"Interests: {interests}")

        # Age Range
        youthful_topics = {'gaming', 'music', 'entertainment', 'lifestyle', 'vlog', 'comedy'}
        mature_topics = {'news', 'politics', 'education', 'finance', 'society'}
        is_youthful = (
            any(t.split('/')[-1].lower() in youthful_topics for t in topics or []) or
            any(tag in youthful_topics for tag in tags)
        )
        is_mature = (
            any(t.split('/')[-1].lower() in mature_topics for t in topics or []) or
            any(tag in mature_topics for tag in tags)
        )

        if comments:
            sentiments = [TextBlob(comment).sentiment.polarity for comment in comments]
            positive_ratio = len([s for s in sentiments if s > 0]) / len(sentiments)
            if positive_ratio > 0.7 and is_youthful:
                age_range = "13-24"
            elif positive_ratio > 0.3 or (is_youthful and not is_mature):
                age_range = "18-34"
            elif is_mature:
                age_range = "25-44"
            else:
                age_range = "25-34"  # Neutral default
        else:
            age_range = "18-34" if is_youthful else "25-44" if is_mature else "Unknown"
        logger.info(f"Estimated age range: {age_range}")

        # Geographic Distribution
        country_mentions = Counter()
        country_codes = {
            'us': 'United States', 'usa': 'United States', 'uk': 'United Kingdom',
            'in': 'India', 'ca': 'Canada', 'au': 'Australia', 'de': 'Germany',
            'fr': 'France', 'jp': 'Japan', 'br': 'Brazil', 'mx': 'Mexico',
            'es': 'Spain', 'it': 'Italy', 'cn': 'China'
        }
        all_text = comments + descriptions + [v['title'].lower() for v in videos_data]
        for text in all_text:
            for code, country in country_codes.items():
                if re.search(rf'\b{code}\b|\b{country.lower()}\b', text):
                    country_mentions[country] += 1
        if not country_mentions:
            country_mentions.update({'United States': 1, 'United Kingdom': 1, 'India': 1})
        total = sum(country_mentions.values())
        geographic_distribution = [
            {'country': country, 'percentage': round((count / total) * 100, 2)}
            for country, count in country_mentions.most_common(5)
        ]
        logger.info(f"Geographic distribution: {geographic_distribution}")

        # Simulated age groups per country
        age_weights = (
            {'13-24': 0.3, '18-34': 0.5, '25-44': 0.2} if is_youthful else
            {'13-24': 0.2, '18-34': 0.4, '25-44': 0.4}
        )
        age_groups_per_country = {
            country: {
                age: round(perc * weight, 1) for age, weight in age_weights.items()
            }
            for country, perc in [
                (d['country'], d['percentage']) for d in geographic_distribution
            ]
        }
        logger.info(f"Age groups per country: {age_groups_per_country}")

        return {
            'estimated_age_range': age_range,
            'top_locations': [item['country'] for item in geographic_distribution],
            'geographic_distribution': geographic_distribution,
            'interests': interests,
            'age_groups_per_country': age_groups_per_country
        }

    except Exception as e:
        logger.error(f"Demographics analysis failed: {str(e)}")
        return {'error': f"Analysis failed: {str(e)}"}