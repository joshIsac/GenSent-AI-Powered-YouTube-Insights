import re
from nltk.corpus import stopwords
from spellchecker import SpellChecker
import string


def process_input(user_input,genre=None):
    """
    A utility function that processes the input (e.g., cleans text, formats it for the model).
    This helps improve the quality of input and ensures it's in a good format.
    """
    # Step 1: Clean the input - remove unwanted characters, special symbols, etc.
    cleaned_input = clean_text(user_input)
    
    # Step 2: Add any context or information to the input that may improve model performance
    formatted_input = format_input_for_model(cleaned_input, genre)
    
    return formatted_input

def clean_text(text):
    """
    Clean the input text by removing special characters, extra spaces, stopwords, and performing spelling corrections.
    """
    text = ' '.join(text.split())  # Remove extra spaces
    text = text.translate(str.maketrans('', '', string.punctuation))  # Remove punctuation
    text = text.lower()  # Convert to lowercase for uniformity
    text = remove_stopwords(text)  # Remove stopwords
    text = correct_spelling(text)  # Correct spelling
    
    return text

def remove_stopwords(text):
    """
    Remove stopwords from the text to ensure only meaningful words are processed.
    """
    try:
        stop_words = set(stopwords.words('english'))
    except LookupError:
        import nltk
        nltk.download('stopwords')
        stop_words = set(stopwords.words('english'))
    
    words = text.split()
    filtered_words = [word for word in words if word not in stop_words]
    return ' '.join(filtered_words)

def correct_spelling(text):
    """
    Correct any spelling mistakes in the input text using a spell checker.
    """
    spell = SpellChecker()
    words = text.split()
    corrected_words = [spell.correction(word) if spell.correction(word) else word for word in words]
    return ' '.join(corrected_words)

def format_input_for_model(text, genre):
    """
    Add any context or special formatting needed for the model to better understand the input.
    The genre context helps the model better understand the context of the conversation.
    """
    genre_context = genre.lower() if genre else "general"
    formatted_input = f"User is a content creator in the {genre_context} genre. The user asks: {text}"
    
    return formatted_input

def post_process_response(response, genre=None):
    """
    Post-process the model's response to make it more user-friendly.
    This can involve formatting, removing extraneous information, etc.
    """
    response = response.strip()  # Trim unnecessary spaces
    response = ensure_genre_relevance(response, genre)  # Ensure relevance
    
    return response

def ensure_genre_relevance(response, genre=None):
    """
    Ensure that the response is relevant to the user's genre/context.
    """
    genre_context = genre.lower() if genre else "general"
    if genre_context not in response.lower():
        response += f" - Related to {genre_context} content creation."
    return response

def generate_follow_up_question(user_input, genre):
    """
    Generate follow-up questions to engage the user further based on the initial input.
    This helps create a more interactive experience.
    """
    intent = analyze_user_intent(user_input)  # Identify user intent
    return generate_follow_up_based_on_genre(genre, intent)

def analyze_user_intent(user_input):
    """
    Analyzes the user's input to infer their intent.
    """
    user_input = user_input.lower()

    if "growth" in user_input or "subscribers" in user_input:
        return "growth"
    elif "algorithm" in user_input:
        return "algorithm"
    elif "content" in user_input or "video ideas" in user_input:
        return "content_creation"
    elif "streaming" in user_input:
        return "streaming"
    elif "monetization" in user_input:
        return "monetization"
    
    return "general_inquiry"

def format_suggestions_for_user(suggestions):
    """
    Format a list of suggestions in a user-friendly way.
    """
    formatted_suggestions = "\n".join([f"- {suggestion}" for suggestion in suggestions])
    return f"Here are some suggestions for you:\n{formatted_suggestions}"

def handle_follow_up(user_input, intent):
    """
    Handle generating follow-up questions or actions based on the user's input intent.
    """
    follow_ups = {
        "growth": "Have you tried collaborating with other creators to grow your audience?",
        "algorithm": "Would you like tips on optimizing your video titles and descriptions for better reach?",
        "content_creation": "Would you like to discuss SEO strategies for your videos?",
        "streaming": "Have you considered doing live streaming for increased engagement?",
        "monetization": "Would you like advice on how to monetize your content?",
        "general_inquiry": "Would you like more suggestions on this topic?"
    }
    
    return follow_ups.get(intent, "Would you like more suggestions on this topic?")

def generate_follow_up_based_on_genre(genre, intent):
    """
    Generate follow-up questions based on both the genre and the intent.
    """
    genre_follow_ups = {
        "gaming": {
            "growth": "Have you tried gaming tournaments or events to boost your growth?",
            "content_creation": "Would you like tips on creating engaging gaming thumbnails?",
            "streaming": "Have you set up a regular streaming schedule to boost your viewership?",
        },
        "music": {
            "growth": "Have you considered collaborating with other musicians or doing remixes?",
            "content_creation": "Do you want tips on making high-quality music videos?",
            "streaming": "Have you thought about live streaming concerts on YouTube?",
        },
        "tech": {
            "growth": "Have you tried reviewing trending gadgets to gain more views?",
            "content_creation": "Would you like help with scripting engaging tech reviews?",
            "streaming": "Have you considered doing live product demos?",
        }
    }
    
    if genre in genre_follow_ups and intent in genre_follow_ups[genre]:
        return genre_follow_ups[genre][intent]
    
    return handle_follow_up("", intent)



