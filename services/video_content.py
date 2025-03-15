import os
from dotenv import load_dotenv
from groq import Groq
from services import youtube  # Import the YouTube client from __init__.py
import re

load_dotenv()

# Initialize Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)



class VideoContentService:
    """
    Service class for generating video titles and scripts using Groq AI and YouTube API.
    """

    def __init__(self):
        self.max_title_length = 70  # YouTube title length limit

    def _get_trending_keywords(self, query: str, region_code: str = "US") -> list:
        """
        Fetch trending keywords related to the query using YouTube API.
        """
        try:
            search_response = youtube.search().list(
                q=query,
                part="snippet",
                type="video",
                regionCode=region_code,
                maxResults=10
            ).execute()

            # Extract keywords from video titles and descriptions
            keywords = []
            for item in search_response.get("items", []):
                title = item["snippet"]["title"]
                description = item["snippet"]["description"]
                # Simple keyword extraction (can be enhanced with NLP)
                title_words = re.findall(r'\w+', title.lower())
                description_words = re.findall(r'\w+', description.lower())
                keywords.extend([word for word in title_words + description_words if len(word) > 3])

            # Remove duplicates and limit to top 10 keywords
            keywords = list(set(keywords))[:10]
            return keywords
        except Exception as e:
            print(f"Error fetching trending keywords: {e}")
            return []

    def generate_titles(self, video_description: str, num_titles: int = 5) -> list:
        """
        Generate SEO-friendly video titles using Groq AI and YouTube trending keywords.
        """
        # Step 1: Extract key topics from description for keyword search
        prompt = f"Extract key topics from the following video description for SEO purposes:\n\n{video_description}"
        key_topics_response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",  # Fast and efficient model
            max_tokens=100,
            temperature=0.7
        )
        key_topics = key_topics_response.choices[0].message.content.strip()

        # Step 2: Fetch trending keywords from YouTube API
        trending_keywords = self._get_trending_keywords(key_topics)

        # Step 3: Generate titles using Groq AI, incorporating trending keywords
        prompt = (
            f"Generate {num_titles} SEO-friendly YouTube video titles based on the following description:\n\n"
            f"{video_description}\n\n"
            f"Incorporate these trending keywords where relevant: {', '.join(trending_keywords)}\n\n"
            f"Each title should be under {self.max_title_length} characters, engaging, and optimized for click-through rates."
        )
        title_response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            max_tokens=500,
            temperature=0.7
        )

        # Parse and clean titles
        titles = title_response.choices[0].message.content.strip().split("\n")
        titles = [title.strip("- ").strip() for title in titles if title.strip()]
        titles = [title for title in titles if len(title) <= self.max_title_length]

        # Ensure we return the requested number of titles (or fewer if not enough)
        return titles[:num_titles]

    def generate_script(self, content_idea: str, video_length: int = 5, tone: str = "casual") -> str:
        """
        Generate a detailed video script using Groq AI, tailored to user input.
        """
        # Calculate approximate segment lengths based on video length (in minutes)
        intro_length = min(0.5, video_length * 0.1)  # Intro: ~10% of video
        outro_length = min(0.5, video_length * 0.1)  # Outro: ~10% of video
        main_content_length = video_length - intro_length - outro_length

        # Define tone-specific instructions
        tone_instructions = {
            "casual": "Use a friendly, conversational tone with simple language.",
            "professional": "Use a formal, authoritative tone with precise language.",
            "energetic": "Use an enthusiastic, high-energy tone with dynamic language."
        }

        # Create prompt for script generation
        prompt = (
            f"Generate a detailed YouTube video script based on the following content idea:\n\n"
            f"{content_idea}\n\n"
            f"Video length: {video_length} minutes\n"
            f"Tone: {tone} ({tone_instructions.get(tone, 'Use a casual tone.')})\n\n"
            f"Structure the script into three sections:\n"
            f"1. Intro ({intro_length} minutes): Start with a hook, introduce the topic, and preview key points.\n"
            f"2. Main Content ({main_content_length} minutes): Cover the main points with examples and explanations.\n"
            f"3. Outro ({outro_length} minutes): Summarize key points, include a call-to-action (e.g., like, subscribe), and encourage engagement.\n\n"
            f"Include approximate timestamps for each section and ensure the script is engaging and optimized for viewer retention."
        )

        script_response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            max_tokens=2000,  # Longer output for detailed scripts
            temperature=0.7
        )

        return script_response.choices[0].message.content.strip()
    

    def suggest_keywords(self, description: str) -> list:
        """
        Suggest SEO-friendly keywords based on the video description using Groq AI.
        """
        try:
            if not description:
                raise ValueError("Description is required.")
            prompt = f"Generate 5 SEO-friendly keywords based on this video description: {description}"
            response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",  # Updated model
                max_tokens=50,
                temperature=0.7
            )
            keywords = response.choices[0].message.content.strip().split('\n')
            # Clean up keywords (remove numbering, extra whitespace, etc.)
            keywords = [keyword.strip('1234567890. -').strip() for keyword in keywords if keyword.strip()]
            return keywords[:5]  # Ensure exactly 5 keywords (or fewer if response is short)
        except Exception as e:
            print(f"Error suggesting keywords: {str(e)}")
            return []