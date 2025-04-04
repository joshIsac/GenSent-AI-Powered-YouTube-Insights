import random
import difflib
import string
from services.youtube_analysis import (
    search_channel,
    get_channel_data,
    fetch_videos_from_channel,
    fetch_video_details
)

class YouTubeChatbot:
    def __init__(self, model):
        self.model = model  # AI Model for text generation (if needed)
        self.genre_specific_tips = {
            "gaming": [
                "🎮 Cover new game releases with in-depth reviews.",
                "🏆 Create challenge-based gameplay videos.",
                "🔥 Experiment with live streaming for engagement.",
                "👥 Collaborate with other gaming YouTubers."
            ],
            "technology": [
                "📱 Compare the latest smartphones in a battle format.",
                "💡 Break down complex tech concepts simply.",
                "🔍 Create 'Best Tech Under $X' guides.",
                "📊 Analyze trends in AI and emerging technology."
            ],
            "education": [
                "📚 Create interactive quizzes to boost engagement.",
                "✏️ Break down difficult topics with animations.",
                "🎯 Share productivity hacks for students.",
                "💭 Make explainer videos on trending academic topics."
            ],
            # Add more genres as needed
        }

    def preprocess_input(self, user_input):
        """Cleans and preprocesses user input for better intent matching."""
        user_input = user_input.lower().translate(str.maketrans('', '', string.punctuation))
        return ' '.join(user_input.split())

    def generate_response(self, user_input, channel_name=None, genre=None, tone='neutral'):
        """Processes user input with improved intent detection."""
        cleaned_input = self.preprocess_input(user_input)

        # Expanded intents with more variations
        intents = {
            "channel_insights": [
                "how is my channel doing", "channel insights", "performance analysis",
                "how's my channel performing", "give me channel stats", "what's my subscriber count"
            ],
            "video_analysis": [
                "analyze recent videos", "video insights", "engagement metrics",
                "how are my videos doing", "video performance"
            ],
            "content_ideas": [
                "what videos should i make", "content ideas", "next video suggestions",
                "suggest video topics", "what should i make next", "ideas for my channel"
            ],
            "sentiment_analysis": [
                "analyze comments", "viewer sentiment", "audience reaction",
                "what do viewers think", "comment analysis"
            ]
        }

        # Detect intent using fuzzy matching
        detected_intent = None
        for intent, phrases in intents.items():
            if any(difflib.get_close_matches(cleaned_input, [self.preprocess_input(p) for p in phrases], cutoff=0.6)):
                detected_intent = intent
                break

        # Fallback to keyword matching if fuzzy matching fails
        if not detected_intent:
            keywords = {
                "channel_insights": ["channel", "subscriber", "growth", "stats"],
                "video_analysis": ["video", "views", "likes", "comments", "engagement"],
                "content_ideas": ["ideas", "topics", "suggestions", "make", "post"],
                "sentiment_analysis": ["comments", "sentiment", "audience", "reaction"]
            }
            for intent, kw_list in keywords.items():
                if any(kw in cleaned_input for kw in kw_list):
                    detected_intent = intent
                    break

        # Call the appropriate method based on detected intent
        if detected_intent == "channel_insights":
            return self.get_channel_insights(channel_name, tone)
        elif detected_intent == "video_analysis":
            return self.analyze_recent_videos(channel_name, tone)
        elif detected_intent == "content_ideas":
            return self.suggest_content_ideas(channel_name, genre, tone)
        elif detected_intent == "sentiment_analysis":
            return self.analyze_comment_sentiment(channel_name, tone)
        
        return self.default_response(genre, tone)

    def get_channel_insights(self, channel_name, tone='neutral'):
        """Fetches enhanced channel statistics."""
        if not channel_name:
            return "⚠️ Please enter a channel name first."

        try:
            channel_id = search_channel(channel_name)
            subscriber_count, title = get_channel_data(channel_id)
            # Note: Additional metrics like total_views and video_count require new functions
            response = (
                f"📊 **{title}** Insights:\n"
                f"• Subscribers: {subscriber_count:,}\n"
                f"💡 Tip: Consistent uploads can boost subscriber growth!"
            )

            if tone == 'positive':
                response += "\n🌟 Your channel is on a great path—keep it up!"
            elif tone == 'negative':
                response += "\n⚠️ Consider optimizing your content strategy for better growth."

            return response
        except Exception as e:
            return f"⚠️ Error fetching channel insights: {str(e)}. Please check the channel name."

    def analyze_recent_videos(self, channel_name, tone='neutral'):
        """Analyzes recent videos with added trend insights."""
        if not channel_name:
            return "⚠️ Please enter a channel name first."

        try:
            videos = fetch_videos_from_channel(channel_name)
            if not videos:
                return "⚠️ No recent videos found. Try uploading content to get started!"

            total_views = sum(video["view_count"] for video in videos)
            total_likes = sum(video["like_count"] for video in videos)
            total_comments = sum(video["comment_count"] for video in videos)
            avg_views = total_views / len(videos)
            avg_likes = total_likes / len(videos)
            avg_comments = total_comments / len(videos)

            # Basic trend analysis
            trend_message = (
                "• View Trend: Not enough data" if len(videos) <= 1 else
                f"• View Trend: {'upward 📈' if videos[0]['view_count'] > videos[-1]['view_count'] else 'downward 📉'}"
            )

            response = (
                f"📊 **Recent Video Analysis**:\n"
                f"• Average Views: {avg_views:,.0f}\n"
                f"• Average Likes: {avg_likes:,.0f}\n"
                f"• Average Comments: {avg_comments:,.0f}\n"
                f"• Engagement Rate: {(avg_likes + avg_comments) / avg_views * 100:.1f}%\n"
                f"{trend_message}\n"
                f"💡 Tip: Engage with comments to boost interaction!"
            )

            if tone == 'positive':
                response += "\n🚀 Your videos are gaining traction—keep it up!"
            elif tone == 'negative':
                response += "\n⚠️ Consider tweaking your content to improve engagement."

            return response
        except Exception as e:
            return f"⚠️ Error analyzing recent videos: {str(e)}. Please check the channel name."

    def analyze_comment_sentiment(self, channel_name, tone='neutral'):
        """Performs sentiment analysis on recent video comments."""
        if not channel_name:
            return "⚠️ Please enter a channel name first."

        try:
            comments = fetch_video_details(channel_name, analysis_type="sentiment")
            if not comments:
                return "⚠️ No comments found for sentiment analysis."

            positive = sum(1 for c in comments if c["sentiment"] == "positive")
            negative = sum(1 for c in comments if c["sentiment"] == "negative")
            neutral = sum(1 for c in comments if c["sentiment"] == "neutral")
            total = positive + negative + neutral

            response = (
                f"🗣 **Audience Sentiment Analysis**:\n"
                f"• Positive: {positive/total*100:.1f}% 😊\n"
                f"• Neutral: {neutral/total*100:.1f}% 😐\n"
                f"• Negative: {negative/total*100:.1f}% 😡\n"
                f"💡 Tip: Address negative feedback constructively!"
            )

            if tone == 'positive':
                response += "\n💬 Your audience loves you—keep engaging!"
            elif tone == 'negative':
                response += "\n⚠️ Focus on improving based on feedback."

            return response
        except Exception as e:
            return f"⚠️ Error analyzing comment sentiment: {str(e)}. Please check the channel name."

    def suggest_content_ideas(self, channel_name, genre=None, tone='neutral'):
        """Suggests personalized content ideas."""
        if not channel_name:
            return "⚠️ Please enter a channel name first."

        try:
            videos = fetch_videos_from_channel(channel_name)
            if not videos:
                response = (
                    "⚠️ No videos found yet!\n"
                    "• Start with an intro video.\n"
                    "• Explore trending topics in your genre."
                )
                return response

            best_video = max(videos, key=lambda v: v["view_count"])
            suggestions = [
                f"🔥 Your video '{best_video['title']}' did well—make a follow-up!",
                "📈 Try trending topics in your genre.",
                "🎥 Experiment with Shorts for quick engagement."
            ]

            if genre and genre.lower() in self.genre_specific_tips:
                suggestions.extend(random.sample(self.genre_specific_tips[genre.lower()], 2))

            if tone == 'positive':
                suggestions.append("🎉 You're on fire! Keep those creative juices flowing! 🔥")
            elif tone == 'negative':
                suggestions.append("⚠️ Try exploring new ideas to gain traction.")

            return "🎬 **Content Ideas**:\n" + "\n".join(random.sample(suggestions, 3))
        except Exception as e:
            return f"⚠️ Error suggesting ideas: {str(e)}. Please check the channel name."

    def default_response(self, genre=None, tone='neutral'):
        """Provides a helpful fallback response."""
        base_response = (
            "🤖 I'm here to help! You can ask me about:\n"
            "• 📊 Channel insights\n"
            "• 🎥 Recent video analysis\n"
            "• 🧠 Content ideas\n"
            "• 🗣 Audience sentiment\n"
        )

        if genre and genre.lower() in self.genre_specific_tips:
            base_response += f"\n\nI specialize in **{genre}** content—ask me anything!"

        if tone == 'positive':
            base_response += "\n🎉 Keep up the great work! 🚀"
        elif tone == 'negative':
            base_response += "\n⚠️ Don’t get discouraged—there’s always room to grow!"

        return base_response