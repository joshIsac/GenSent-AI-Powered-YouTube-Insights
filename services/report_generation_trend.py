import requests
import os
from dotenv import load_dotenv

# Load API Key from .env file
load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")

# Ensure API key is loaded
if not API_KEY:
    raise ValueError("Error: GROQ_API_KEY is missing. Check your .env file.")

# Function to call Groq API
def generate_groq_response(prompt):
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "mistral-saba-24b",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }

        # Make API request
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=30
        )

        # Print full response for debugging
        print("Status Code:", response.status_code)
        print("Response Body:", response.text)

        response.raise_for_status()  # Raises an error for bad responses (4xx, 5xx)
        
        response_data = response.json()
        
        # Check if response contains choices
        if "choices" in response_data and response_data["choices"]:
            return response_data["choices"][0]["message"]["content"]
        else:
            return f"API Response Error: {response_data}"

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        return f"HTTP Error: {e.response.text if e.response else 'No response'}"
    
    except requests.exceptions.RequestException as e:
        print(f"API Request Failed: {str(e)}")
        return f"Request Error: {str(e)}"
    
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")
        return f"Unexpected Error: {str(e)}"