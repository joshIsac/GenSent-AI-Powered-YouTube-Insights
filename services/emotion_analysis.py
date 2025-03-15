import torch
import pandas as pd
import numpy as np
from services import youtube  # Absolute import from services package
from dotenv import load_dotenv
from transformers import AutoTokenizer
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import re
import os

class EmotionAnalyzer:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        try:
            with open('services/model/tfidf_vectorizer.pkl', 'rb') as f:
                self.vectorizer = pickle.load(f)
        except FileNotFoundError:
            raise Exception("TF-IDF vectorizer not found. Please save it during training.")
        
        try:
            with open('services/model/emotion_labels.pkl', 'rb') as f:
                self.emotion_labels = pickle.load(f)
        except FileNotFoundError:
            raise Exception("Emotion labels not found. Please save them during training.")
        
        # Define MLP model architecture (must match training)
        class EmotionMLP(torch.nn.Module):
            def __init__(self, input_size, hidden_size, output_size):
                super(EmotionMLP, self).__init__()
                self.fc1 = torch.nn.Linear(input_size, hidden_size)
                self.relu = torch.nn.ReLU()
                self.fc2 = torch.nn.Linear(hidden_size, output_size)

            def forward(self, x):
                x = self.fc1(x)
                x = self.relu(x)
                x = self.fc2(x)
                return x

        # Initialize model
        input_size = len(self.vectorizer.get_feature_names_out())
        hidden_size = 512  # Must match training
        output_size = len(self.emotion_labels)
        self.model = EmotionMLP(input_size, hidden_size, output_size).to(self.device)

        # Load saved model weights
        try:
            self.model.load_state_dict(torch.load('services/model/emotion_mlp_model.pth'))
            self.model.eval()
        except FileNotFoundError:
            raise Exception("Trained model not found. Please train the model first.")
        
    def preprocess_text(self, text):
        """Preprocess the text (same as training)"""
        text = text.lower()
        text = re.sub(r"http\S+|www\S+|https\S+", '', text)
        text = re.sub(r'\W', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def get_video_comments(self, video_id, max_results=100):
        """Fetch comments from a YouTube video using the API"""
        comments = []
        try:
            request = youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=max_results,
                textFormat='plainText'
            )
            response = request.execute()

            for item in response['items']:
                comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
                comments.append(comment)

            while 'nextPageToken' in response:
                request = youtube.commentThreads().list(
                    part='snippet',
                    videoId=video_id,
                    maxResults=max_results,
                    textFormat='plainText',
                    pageToken=response['nextPageToken']
                )
                response = request.execute()
                for item in response['items']:
                    comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
                    comments.append(comment)

            return comments
        except Exception as e:
            print(f"Error fetching comments: {str(e)}")
            return []
    
    def predict_emotions(self, comments):
        """Predict emotions for a list of comments"""
        if not comments:
            return []

        clean_comments = [self.preprocess_text(comment) for comment in comments]
        comments_tfidf = self.vectorizer.transform(clean_comments).toarray()
        inputs = torch.tensor(comments_tfidf, dtype=torch.float32).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(inputs)
            predictions = torch.argmax(outputs, dim=1).cpu().numpy()
        
        predicted_emotions = self.emotion_labels[predictions]
        return list(zip(comments, predicted_emotions))

    def analyze_video_emotions(self, video_id, max_results=100):
        """Analyze emotions for all comments in a video"""
        comments = self.get_video_comments(video_id, max_results)
        
        if not comments:
            return {
                'video_id': video_id,
                'total_comments': 0,
                'predictions': [],
                'emotion_summary': {}
            }

        predictions = self.predict_emotions(comments)
        emotion_counts = pd.Series([pred[1] for pred in predictions]).value_counts().to_dict()
        
        return {
            'video_id': video_id,
            'total_comments': len(comments),
            'predictions': predictions,
            'emotion_summary': emotion_counts
        }