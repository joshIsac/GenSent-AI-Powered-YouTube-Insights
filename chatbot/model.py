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
            model="llama3-70b-8192",
            temperature=0.8,
            max_tokens=2000,
            top_p=0.8,
            frequency_penalty=0.2,
            model_kwargs={"presence_penalty": 0.3}
        )
        
        # Enhanced prompt template with genre context
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", 
            """You are EngageBot X an expert in YouTube analytics assistant specializing in gaming content and a recommender system that provides an clean response and provide tips to improving channels and other issues related to the channel.
Your goal is to assist content creators by providing clear, actionable advice based on their queries.
Provide structured, easy-to-read insights for content creators.
Your response should include:
Use the following Example to respond:
- Channel: PewDiePie
- Genre: Gaming
- Channel Insights: High subscriber count, consistent uploads, strong audience engagement.
- Recent Video Analysis: Recent videos show a slight dip in viewership compared to average.
- Content Suggestions: Explore trending games, collaborate with other creators.
- and other personalized recommendations
- Follow-up Questions: Prompt the user with a relevant follow-up to keep the conversation going.

Respond clearly and concisely with bullet points line by line not like paragraph and emojis wherever required and also ensure it should'nt be clumped up and also provide the response like a normal chatbot appropriately and ensure whenever any content creators greet you also greet.
your main instructions are given below
- Respond to the user’s query directly and concisely.
- Use bullet points for clarity and readability.
- Include relevant data from the context when applicable.
- Offer practical suggestions or insights tailored to the query.
- If the user greets you, greet them back naturally.
- If data is missing or incomplete, acknowledge it and provide general advice.
"""),

            ("user", "{user_input}")
        ])
        
        self.output_parser = StrOutputParser()
        self.chain = self.prompt | self.groq_api | self.output_parser
        
        # Initialize YouTube chatbot with this model
        self.youtube_chatbot = YouTubeChatbot(self)

    def generate_response(self, user_input, channel_name=None, genre=None):
        """Generate a response using both Groq API and YouTube analytics."""
        try:
            # Fetch data first (insights, recent videos, content suggestions)
            youtube_response = self.youtube_chatbot.generate_response(user_input, channel_name, genre)
        

            if "⚠️" in youtube_response or youtube_response.startswith("🤖"):


                # Fetch relevant data (e.g., recent video insights, audience trends)
                channel_insights = self.youtube_chatbot.get_channel_insights(channel_name)
                recent_analysis = self.youtube_chatbot.analyze_recent_videos(channel_name)
                content_suggestions = self.youtube_chatbot.suggest_content_ideas(channel_name, genre)
                
                # Incorporate this data into the model prompt for Groq
                groq_response = self.chain.invoke({
                    "user_input": user_input,
                    "channel_name": channel_name or "Not specified",
                    "genre": genre or "Not specified",
                    "channel_insights": channel_insights,
                    "recent_analysis": recent_analysis,
                    "content_suggestions": content_suggestions
                })
                
                # Combine responses properly
                if "⚠️" in youtube_response:
                    return groq_response.strip()  # Fall back to Groq if no insights
                else:
                    return f"{youtube_response}\n\nAdditional Insights:\n{groq_response.strip()}"
        


        except ValueError as ve:
            return f"Error: {str(ve)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"
        

    
    def analyze_channel(self, channel_name, genre):
        """Analyze channel and provide comprehensive insights."""
        try:
            # Check if necessary parameters are provided
            if not channel_name or not genre:
                return {"error": "Channel name and genre must be provided.", "status": 400}
            
            # Get analysis from YouTube chatbot
            basic_stats = self.youtube_chatbot.get_channel_insights(channel_name)
            recent_analysis = self.youtube_chatbot.analyze_recent_videos(channel_name)
            content_suggestions = self.youtube_chatbot.suggest_content_ideas(channel_name, genre)
            
            # Remove any error messages
            results = []
            subscribers = "-"
            total_views = "-"
            video_count = "-"
            top_content = "No data available"
            recommendations = []


            if not basic_stats.startswith("⚠️"):
                results.append(basic_stats)
                subscribers = basic_stats.split("Subscribers: ")[1].split("\n")[0]  # Extract subscriber count
            if not recent_analysis.startswith("⚠️"):
                results.append(recent_analysis)
                video_count = str(len(self.youtube_chatbot.fetch_videos_from_channel(channel_name)))  # Assumes video list available
                total_views = recent_analysis.split("Average Views: ")[1].split("\n")[0]  # Approximate total views
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
                    "top_content": top_content,  # Placeholder, requires actual top video data
                    "recommendations": recommendations,
                    "insights": "\n\n".join(results),
                    "genre": genre
                }
            }
            
        except Exception as e:
            return {"error": str(e), "status": 500}
# Create chatbot instance
chatbot = ChatbotModel()
