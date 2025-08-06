from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from typing import Dict, Tuple
import logging

class SentimentAnalyzer:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        self.logger = logging.getLogger('sentiment_analyzer')
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        try:
            vader_scores = self._analyze_with_vader(text)
            textblob_scores = self._analyze_with_textblob(text)
            
            combined_score = (vader_scores['compound'] + textblob_scores['polarity']) / 2
            
            sentiment_label = self._get_sentiment_label(combined_score)
            
            return {
                'score': combined_score,
                'label': sentiment_label,
                'vader_compound': vader_scores['compound'],
                'vader_positive': vader_scores['pos'],
                'vader_negative': vader_scores['neg'],
                'vader_neutral': vader_scores['neu'],
                'textblob_polarity': textblob_scores['polarity'],
                'textblob_subjectivity': textblob_scores['subjectivity']
            }
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {e}")
            return {
                'score': 0.0,
                'label': 'neutral',
                'vader_compound': 0.0,
                'vader_positive': 0.0,
                'vader_negative': 0.0,
                'vader_neutral': 1.0,
                'textblob_polarity': 0.0,
                'textblob_subjectivity': 0.0
            }
    
    def _analyze_with_vader(self, text: str) -> Dict[str, float]:
        scores = self.vader.polarity_scores(text)
        return scores
    
    def _analyze_with_textblob(self, text: str) -> Dict[str, float]:
        try:
            blob = TextBlob(text)
            return {
                'polarity': blob.sentiment.polarity,
                'subjectivity': blob.sentiment.subjectivity
            }
        except Exception:
            return {'polarity': 0.0, 'subjectivity': 0.0}
    
    def _get_sentiment_label(self, score: float) -> str:
        if score >= 0.1:
            return 'positive'
        elif score <= -0.1:
            return 'negative'
        else:
            return 'neutral'
    
    def analyze_sentiment_simple(self, text: str) -> Tuple[float, str]:
        result = self.analyze_sentiment(text)
        return result['score'], result['label']
    
    def batch_analyze_sentiment(self, texts: list) -> list:
        results = []
        for text in texts:
            results.append(self.analyze_sentiment(text))
        return results