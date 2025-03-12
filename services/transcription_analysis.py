import sys
from youtube_transcript_api import YouTubeTranscriptApi
from services import youtube  # Import from __init__.py
from textblob import TextBlob
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk import FreqDist
import re
import json
from spellchecker import SpellChecker
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

class TranscriptionAnalyzer:
    def __init__(self,channel_name,video_title):
        self.channel_name = channel_name
        self.video_title = video_title
        self.video_id =None
        self.video_info =None
        self.transcript =None
        self.timestamps=None
        self.spell_checker =SpellChecker()
        self.sentiment_analyzer = SentimentIntensityAnalyzer()

    def search_video(self):
        """Search for a video based on channel name and title."""
        try:
            search_response = youtube.search().list(
                q=f"{self.channel_name} {self.video_title}",
                part='id,snippet',
                maxResults=1,
                type='video'
            ).execute()

            if not search_response['items']:
                raise ValueError("Video not found")  
              
            self.video_id = search_response['items'][0]['id']['videoId']
            self.video_info = search_response['items'][0]['snippet']
            return True
        except Exception as e:
            print(f"Error searching video: {e}")
            return False
        
    def fetch_transcript(self):
        """Fetch the transcript of the video."""
        if not self.video_id:
            return False
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(self.video_id)
            self.transcript = " ".join([line['text'] for line in transcript_list])
            self.transcript = self.clean_transcript(self.transcript)
            self.timestamps = [{'time': line['start'], 'text': line['text']} for line in transcript_list]
            return True
        except Exception as e:
            print(f"Error fetching transcript: {e}")
            return False
        

    def clean_transcript(self,text):
        text = re.sub(r'([a-z])\s([A-Z])', r'\1. \2', text)
        text = re.sub(r'\s+', ' ', text).strip()

        words = word_tokenize(text)
        corrected_words = [self.spell_checker.correction(word) if self.spell_checker.correction(word) else word for word in words]
        return " ".join(corrected_words)
        


    def analyze_transcript(self):
        """Analyze the sentiment of the video transcript."""
        if not self.transcript or not self.timestamps:
            return None
        
        # Basic statistics
        words = word_tokenize(self.transcript.lower())
        stop_words = set(stopwords.words('english'))
        filtered_words = [w for w in words if w not in stop_words and w.isalnum()]

        total_words = len(filtered_words)
        video_duration = float(self.timestamps[-1]['time'])
        words_per_minute = total_words / (video_duration/60) if video_duration > 0 else 0

        #Sentiment analysis
        blob = TextBlob(self.transcript)
        sentiment_score=blob.sentiment.polarity
        overall_sentiment = "Positive" if sentiment_score > 0 else "Negative" if sentiment_score < 0 else "Neutral"
        sentiment_timeline=[{'time': t['time'], 'sentiment': TextBlob(t['text']).sentiment.polarity} for t in self.timestamps]

        # Keyword extraction
        word_freq = FreqDist(filtered_words)
        keywords = [{'word': word, 'count': count} for word, count in word_freq.most_common(15)]

        # Key moments (based on sentiment changes)
        key_moments = []
        for i in range(1,len(self.timestamps)):
            previous_text=self.timestamps[i-1]['text']
            current_text=self.timestamps[i]['text']
            if TextBlob(previous_text).sentiment.polarity != TextBlob(current_text).sentiment.polarity:
               key_moments.append({
                    'time': self.format_time(self.timestamps[i]['time']),
                    'content': current_text[:25] + '...'
                }) 
               
        #Ai generated insights
        insights = [
            {'type': 'Engagement', 'text': f'Word count suggests {words_per_minute:.0f} WPM pace'},
            {'type': 'Sentiment', 'text': f'Dominant sentiment: {overall_sentiment}'},
            {'type': 'Content', 'text': f'Top keywords: {", ".join([k["word"] for k in keywords[:3]])}'}
        ]

        return {
            'transcript': self.transcript,
            'thumbnail': self.video_info['thumbnails']['high']['url'],
            'stats': {
                'total_words': total_words,
                'video_length': self.format_time(video_duration),
                'wpm': round(words_per_minute),
                'retention': 'N/A' # Retention not included due to privacy restrictions
            },
            'sentiment': {
                'overall': overall_sentiment,
                'score': round(sentiment_score, 2),
                'timeline': sentiment_timeline
            },
            'keywords': keywords,
            'key_moments': key_moments[:15],  # Limit to 5
            'insights': insights
        }
    
    def highlight_keywords(self, keywords=None):
        """Highlight keywords in the transcript."""
        if not self.transcript:
            return "No Transcript Available"
        
        text = self.transcript
        if not keywords:
            keywords = ['analytics', 'engagement', 'audience', 'content', 'strategy']
        
        for keyword in keywords:
            regex = re.compile(r'\b' + keyword + r'\b', re.IGNORECASE)
            text = regex.sub(f'**{keyword}**', text)
        return text
    

    def highlight_sentiment(self):  
        """Highlight all sentiment-bearing words using VADER."""
        if not self.transcript:
            return "No Transcript Available"
        
        words = word_tokenize(self.transcript)
        highlighted_text = []
        
        for word in words:
            sentiment_score = self.sentiment_analyzer.polarity_scores(word)
            if sentiment_score['compound'] > 0.05:
                highlighted_text.append(f'<span class="positive">{word}</span>')  # Positive
            elif sentiment_score['compound'] < -0.05:
                highlighted_text.append(f'<span class="negative">{word}</span>')  # Negative
            else:
                highlighted_text.append(word)  # Neutral or no sentiment
        
        return ' '.join(highlighted_text)
    
    def save_transcripts(self, filename="transcript.csv"):
        """Save the transcript to a file."""
        if not self.transcript:
            print("No transcript available")
            return False
        
        try:
            with open(filename, 'w',encoding='utf-8') as file:
                file.write(self.transcript)
            print(f"Transcript saved to {filename}")
            return True
        except Exception as e:
            print(f"Error saving transcript: {e}")
            return False
        
    @staticmethod
    def format_time(seconds):
            """Format seconds as MM:SS."""
            mins, secs = divmod(int(seconds), 60)
            return f"{mins:02d}:{secs:02d}"
        
    def run_analysis(self):
        """Run the full analysis pipeline."""
        if not self.search_video():
            return None
        if not self.fetch_transcript():
             return None
            
        results = self.analyze_transcript()
        if results:
            print("\n=== Transcript ===")
        print(results['transcript'][:200] + "..." if len(results['transcript']) > 200 else results['transcript'])
            
        print("\n=== Highlighted Keywords ===")
        print(self.highlight_keywords([k['word'] for k in results['keywords']][:5])[:200] + "...")
            
        print("\n=== Highlighted Sentiment ===")
        print(self.highlight_sentiment()[:200] + "...")
            
        print("\n=== Key Moments ===")
        for moment in results['key_moments']:
             print(f"{moment['time']} - {moment['content']}")
            
        print("\n=== Speech Analytics ===")
        print(f"Total Words: {results['stats']['total_words']}")
        print(f"Video Length: {results['stats']['video_length']}")
        print(f"Words per Minute: {results['stats']['wpm']}")
            
        print("\n=== Sentiment Analysis ===")
        print(f"Overall Sentiment: {results['sentiment']['overall']}")
        print(f"Sentiment Score: {results['sentiment']['score']}")
        print("Sentiment Timeline (sample):", results['sentiment']['timeline'][:3])

        print("\n===Keywords ===")
        for keyword in results['keywords']:
            print(f"{keyword['word']}: {keyword['count']}")

            print("\n=== AI-Generated Insights ===")
            for insight in results['insights']:
                print(f"{insight['type']}: {insight['text']}")

            self.save_transcripts()
            return results
        return None
    
def main():
    if len(sys.arv) != 3:
        print("Usage: python transcription_analysis.py 'channel_name' 'video_title'")
        sys.exit(1)

    channel_name = sys.argv[1]
    video_title = sys.argv[2]
    analyzer = TranscriptionAnalyzer(channel_name, video_title)
    results=analyzer.run_analysis()



    if results:
        with open('analysis_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print("\nFull analysis saved to analysis_results.json")

if __name__ == "__main__":
    main()