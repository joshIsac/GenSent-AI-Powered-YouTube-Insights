import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from chatbot.chatbot_logic import YouTubeChatbot

load_dotenv()

class ChatbotModel:
    def __init__(self):
        """Initialize the chatbot with optimized settings for Groq API and YouTube integration."""
        if "GROQ_API_KEY" not in os.environ:
            raise ValueError("GROQ_API_KEY is not set in environment variables.")
        
        self.groq_api = ChatGroq(
            model="llama3-8b-8192",
            temperature=0,
            max_tokens=2000,
            top_p=0.8,
            frequency_penalty=0.2,
            model_kwargs={"presence_penalty": 0.3}
        )
        
        # Intent classification prompt
        self.intent_prompt = ChatPromptTemplate.from_messages([
            ("system", 
             """Classify the user's query into one of these intents: channel_insights, video_analysis, content_ideas, sentiment_analysis, or unknown. Respond with only the intent name."""),
            ("user", "{user_input}")
        ])
        self.intent_chain = self.intent_prompt | self.groq_api | StrOutputParser()

        # Fallback response prompt
        self.fallback_prompt = ChatPromptTemplate.from_messages([
            ("system", 
             """You are EngageBot X, a YouTube analytics assistant. The user's query didn't match a specific intent, but you must provide a helpful, context-aware response.
Based on:
- Channel Name: {channel_name}
- Genre: {genre}
- User Query: {user_input}
- Tone: {tone}

Respond clearly with bullet points, use emojis where appropriate, and offer actionable advice or ask for clarification if needed. If the user greets you, greet them back naturally. Avoid generic responses and tailor the answer to the query."""),
            ("user", "{user_input}")
        ])
        self.fallback_chain = self.fallback_prompt | self.groq_api | StrOutputParser()

        # Main response prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", 
             """You are EngageBot X, an expert YouTube analytics assistant specializing in content optimization.
Based on:
- Channel Name: {channel_name}
- Genre: {genre}
- Channel Insights: {channel_insights}
- Recent Video Analysis: {recent_analysis}
- Content Suggestions: {content_suggestions}
- User Query: {user_input}
- Tone: {tone}

Respond clearly with bullet points, use emojis where appropriate, and provide actionable advice. If the user greets you, greet them back naturally. If data is missing, acknowledge it and offer general advice."""),
            ("user", "{user_input}")
        ])
        self.output_parser = StrOutputParser()
        self.chain = self.prompt | self.groq_api | self.output_parser
        
        # Initialize YouTube chatbot with this model
        self.youtube_chatbot = YouTubeChatbot(self)

    def classify_intent(self, user_input):
        """Classify the user's intent using the Groq model."""
        try:
            intent = self.intent_chain.invoke({"user_input": user_input}).strip().lower()
            return intent if intent in ["channel_insights", "video_analysis", "content_ideas", "sentiment_analysis", "unknown"] else "unknown"
        except Exception:
            return "unknown"

    def generate_fallback_response(self, user_input, channel_name=None, genre=None, tone='neutral'):
        """Generate a contextual response for unclear intents using Groq."""
        try:
            return self.fallback_chain.invoke({
                "user_input": user_input,
                "channel_name": channel_name or "Not specified",
                "genre": genre or "Not specified",
                "tone": tone
            }).strip()
        except Exception:
            return "⚠️ I'm having trouble understanding. Could you clarify what you're asking about?"

    def generate_response(self, user_input, channel_name=None, genre=None, tone='neutral'):
        """Generate a response using YouTube analytics and Groq API."""
        try:
            youtube_response = self.youtube_chatbot.generate_response(user_input, channel_name, genre, tone)
            if "⚠️" in youtube_response:
                # Handle errors with a Groq-generated response
                channel_insights = self.youtube_chatbot.get_channel_insights(channel_name) if channel_name else "No channel data available."
                recent_analysis = self.youtube_chatbot.analyze_recent_videos(channel_name) if channel_name else "No video data available."
                content_suggestions = self.youtube_chatbot.suggest_content_ideas(channel_name, genre) if channel_name else "No suggestions available."
                groq_response = self.chain.invoke({
                    "user_input": user_input,
                    "channel_name": channel_name or "Not specified",
                    "genre": genre or "Not specified",
                    "channel_insights": channel_insights,
                    "recent_analysis": recent_analysis,
                    "content_suggestions": content_suggestions,
                    "tone": tone
                })
                return groq_response.strip()
            return youtube_response
        except ValueError as ve:
            return f"Error: {str(ve)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def analyze_channel(self, channel_name, genre):
        """Analyze channel and provide comprehensive insights."""
        try:
            if not channel_name or not genre:
                return {"error": "Channel name and genre must be provided.", "status": 400}
            
            basic_stats = self.youtube_chatbot.get_channel_insights(channel_name)
            recent_analysis = self.youtube_chatbot.analyze_recent_videos(channel_name)
            content_suggestions = self.youtube_chatbot.suggest_content_ideas(channel_name, genre)
            
            results = []
            subscribers = "-"
            total_views = "-"
            video_count = "-"
            top_content = "No data available"
            recommendations = []

            if not basic_stats.startswith("⚠️"):
                results.append(basic_stats)
                subscribers = basic_stats.split("Subscribers: ")[1].split("\n")[0]
            if not recent_analysis.startswith("⚠️"):
                results.append(recent_analysis)
                video_count = str(len(self.youtube_chatbot.fetch_videos_from_channel(channel_name)))
                total_views = recent_analysis.split("Average Views: ")[1].split("\n")[0]
            if not content_suggestions.startswith("⚠️"):
                results.append(content_suggestions)
                recommendations = [line[2:] for line in content_suggestions.split("\n") if line.startswith("• ")]

            if not results:
                return {"error": "Could not analyze channel", "status": 404}

            return {
                "status": 200,
                "data": {
                    "subscribers": subscribers,
                    "total_views": total_views,
                    "video_count": video_count,
                    "top_content": top_content,
                    "recommendations": recommendations,
                    "insights": "\n\n".join(results),
                    "genre": genre
                }
            }
        except Exception as e:
            return {"error": str(e), "status": 500}

# Create chatbot instance
chatbot = ChatbotModel()