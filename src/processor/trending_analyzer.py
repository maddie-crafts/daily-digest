from typing import List, Dict, Any, Tuple
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import re
import logging
from dataclasses import dataclass

from ..storage.database import DatabaseManager

try:
    from nltk.corpus import stopwords
    import nltk
    # Ensure stopwords are downloaded
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords', quiet=True)
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


@dataclass
class TrendingTopic:
    """Represents a trending topic with its metadata"""
    keyword: str
    frequency: int
    articles_count: int
    avg_sentiment: float
    recent_articles: List[Dict[str, Any]]
    trend_score: float


class TrendingAnalyzer:
    """Analyzes articles to identify trending topics"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger('trending_analyzer')
        
        # Initialize stopwords
        if NLTK_AVAILABLE:
            try:
                # Use NLTK's comprehensive English stopwords
                english_stopwords = set(stopwords.words('english'))
                
                # Add some additional domain-specific stopwords for news analysis
                additional_stopwords = {
                    'said', 'says', 'according', 'news', 'report', 'reports', 'reported',
                    'story', 'article', 'website', 'online', 'today', 'yesterday', 
                    'tomorrow', 'week', 'month', 'year', 'day', 'time', 'people',
                    'person', 'man', 'woman', 'men', 'women', 'group', 'company',
                    'government', 'state', 'country', 'world', 'new', 'first', 'last',
                    'number', 'way', 'may', 'also', 'one', 'two', 'three', 'many',
                    'much', 'well', 'good', 'back', 'still', 'even', 'now', 'made',
                    'make', 'take', 'come', 'get', 'go', 'see', 'know', 'think',
                    'look', 'use', 'find', 'give', 'tell', 'work', 'call', 'try',
                    'ask', 'need', 'feel', 'become', 'leave', 'put', 'mean', 'help',
                    'move', 'right', 'left', 'show', 'turn', 'start', 'might', 'could',
                    'since', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday',
                    'sunday', 'like', 'years', 'model'
                }
                
                self.stopwords = english_stopwords.union(additional_stopwords)
                self.logger.info(f"Using NLTK stopwords: {len(self.stopwords)} words")
                
            except Exception as e:
                self.logger.warning(f"Failed to load NLTK stopwords: {e}, using fallback")
                self.stopwords = self._get_fallback_stopwords()
        else:
            self.logger.warning("NLTK not available, using fallback stopwords")
            self.stopwords = self._get_fallback_stopwords()
    
    def _get_fallback_stopwords(self) -> set:
        """Fallback stopwords if NLTK is not available"""
        return {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'down', 'out', 'off', 'over',
            'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when',
            'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
            'same', 'so', 'than', 'too', 'very', 'can', 'will', 'just', 'should',
            'now', 'is', 'are', 'was', 'were', 'been', 'be', 'have', 'has', 'had',
            'do', 'does', 'did', 'say', 'says', 'said', 'get', 'got', 'make', 'made',
            'go', 'went', 'come', 'came', 'take', 'took', 'see', 'saw', 'know', 'knew',
            'think', 'thought', 'look', 'looked', 'use', 'used', 'find', 'found',
            'give', 'gave', 'tell', 'told', 'work', 'worked', 'call', 'called',
            'try', 'tried', 'ask', 'asked', 'need', 'needed', 'feel', 'felt',
            'become', 'became', 'leave', 'left', 'put', 'i', 'me', 'my', 'myself',
            'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours', 'yourself',
            'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers',
            'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs',
            'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 'these',
            'those', 'am', 'being', 'having', 'doing', 'would', 'could', 'should',
            'may', 'might', 'must', 'shall', 'one', 'two', 'also', 'back', 'even',
            'still', 'well', 'much', 'many', 'new', 'first', 'last', 'good', 'way'
        }
    
    def get_trending_topics(self, hours_back: int = 24, min_articles: int = 3, 
                          max_topics: int = 10) -> List[TrendingTopic]:
        """
        Identify trending topics from recent articles
        
        Args:
            hours_back: How many hours back to look for articles
            min_articles: Minimum number of articles for a topic to be trending
            max_topics: Maximum number of trending topics to return
            
        Returns:
            List of TrendingTopic objects sorted by trend score
        """
        try:
            # Get recent articles
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            articles = self._get_recent_articles(cutoff_time)
            
            if len(articles) < min_articles:
                self.logger.warning(f"Not enough recent articles ({len(articles)}) to detect trends")
                return []
            
            # Extract and score keywords
            keyword_data = self._extract_keywords_from_articles(articles)
            
            # Filter and score trending topics
            trending_topics = []
            for keyword, data in keyword_data.items():
                if data['count'] >= min_articles:
                    trend_score = self._calculate_trend_score(
                        data['count'], 
                        data['total_articles'],
                        data['avg_sentiment'],
                        data['recency_score']
                    )
                    
                    topic = TrendingTopic(
                        keyword=keyword,
                        frequency=data['count'],
                        articles_count=len(data['articles']),
                        avg_sentiment=data['avg_sentiment'],
                        recent_articles=data['articles'][:5],  # Top 5 most recent
                        trend_score=trend_score
                    )
                    trending_topics.append(topic)
            
            # Sort by trend score and return top topics
            trending_topics.sort(key=lambda x: x.trend_score, reverse=True)
            return trending_topics[:max_topics]
            
        except Exception as e:
            self.logger.error(f"Error getting trending topics: {e}")
            return []
    
    def _get_recent_articles(self, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Get articles published after cutoff_time"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, content, source, published_date, scraped_date,
                       sentiment_score, sentiment_label, keywords
                FROM articles 
                WHERE scraped_date >= ? 
                ORDER BY scraped_date DESC
            ''', (cutoff_time,))
            
            articles = []
            for row in cursor.fetchall():
                articles.append({
                    'id': row['id'],
                    'title': row['title'],
                    'content': row['content'],
                    'source': row['source'],
                    'published_date': row['published_date'],
                    'scraped_date': row['scraped_date'],
                    'sentiment_score': row['sentiment_score'] or 0,
                    'sentiment_label': row['sentiment_label'] or 'neutral',
                    'keywords': row['keywords'] or ''
                })
            
            return articles
    
    def _extract_keywords_from_articles(self, articles: List[Dict[str, Any]]) -> Dict[str, Dict]:
        """Extract and analyze keywords from articles"""
        keyword_data = defaultdict(lambda: {
            'count': 0,
            'articles': [],
            'sentiments': [],
            'timestamps': []
        })
        
        for article in articles:
            # Extract keywords from title (weighted more heavily)
            title_keywords = self._extract_keywords(article['title'], weight=2)
            content_keywords = self._extract_keywords(article['content'][:500])  # First 500 chars
            
            # Combine keywords
            all_keywords = title_keywords + content_keywords
            
            # Update keyword data
            for keyword in set(all_keywords):  # Remove duplicates within article
                keyword_data[keyword]['count'] += all_keywords.count(keyword)
                keyword_data[keyword]['articles'].append({
                    'id': article['id'],
                    'title': article['title'],
                    'source': article['source'],
                    'sentiment': article['sentiment_label'],
                    'scraped_date': article['scraped_date']
                })
                keyword_data[keyword]['sentiments'].append(article['sentiment_score'])
                keyword_data[keyword]['timestamps'].append(article['scraped_date'])
        
        # Calculate aggregated metrics
        for keyword, data in keyword_data.items():
            data['total_articles'] = len(set(a['id'] for a in data['articles']))
            data['avg_sentiment'] = sum(data['sentiments']) / len(data['sentiments']) if data['sentiments'] else 0
            data['recency_score'] = self._calculate_recency_score(data['timestamps'])
            
            # Sort articles by recency
            data['articles'].sort(key=lambda x: x['scraped_date'], reverse=True)
        
        return dict(keyword_data)
    
    def _extract_keywords(self, text: str, weight: int = 1) -> List[str]:
        """Extract meaningful keywords from text"""
        if not text:
            return []
        
        # Clean and tokenize
        text = text.lower()
        # Remove URLs, email addresses, and other non-meaningful patterns
        text = re.sub(r'http[s]?://\S+|www\.\S+', '', text)  # URLs
        text = re.sub(r'\S+@\S+', '', text)  # Email addresses
        text = re.sub(r'[^\w\s-]', ' ', text)  # Keep hyphens for compound words
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single space
        words = text.split()
        
        # Filter keywords with enhanced criteria
        keywords = []
        for word in words:
            # Remove hyphens for stopword checking but keep them in the final word
            word_for_stopword_check = word.replace('-', '')
            
            if (len(word) >= 3 and  # Minimum 3 characters
                len(word) <= 50 and  # Maximum 50 characters (avoid very long strings)
                word_for_stopword_check not in self.stopwords and 
                not word.isdigit() and  # Not pure numbers
                not word_for_stopword_check.isdigit() and  # Not pure numbers after removing hyphens
                word.replace('-', '').isalpha() and  # Only letters (and hyphens)
                not word.startswith('-') and  # Don't start with hyphen
                not word.endswith('-')):  # Don't end with hyphen
                
                keywords.extend([word] * weight)
        
        return keywords
    
    def _calculate_recency_score(self, timestamps: List[str]) -> float:
        """Calculate a recency score based on when articles were published"""
        if not timestamps:
            return 0
        
        now = datetime.now()
        scores = []
        
        for timestamp_str in timestamps:
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
                hours_ago = (now - timestamp).total_seconds() / 3600
                # Score decreases exponentially with time (higher score = more recent)
                score = max(0, 1 - (hours_ago / 24))  # 1.0 for very recent, 0.0 for 24h+ old
                scores.append(score)
            except (ValueError, TypeError):
                scores.append(0)
        
        return sum(scores) / len(scores) if scores else 0
    
    def _calculate_trend_score(self, frequency: int, article_count: int, 
                             avg_sentiment: float, recency_score: float) -> float:
        """
        Calculate overall trend score for a topic
        
        Factors:
        - Frequency: How often the keyword appears
        - Article spread: How many different articles mention it
        - Sentiment: Absolute sentiment (controversial topics score higher)
        - Recency: How recent the mentions are
        """
        # Normalize frequency (log scale to prevent single dominant keywords)
        freq_score = min(1.0, frequency / 20.0)  # Cap at 20 mentions
        
        # Article spread score (prefer topics mentioned across multiple articles)
        spread_score = min(1.0, article_count / 10.0)  # Cap at 10 articles
        
        # Sentiment score (both very positive and very negative are interesting)
        sentiment_score = abs(avg_sentiment)  # 0-1 range
        
        # Weighted combination
        trend_score = (
            freq_score * 0.3 +
            spread_score * 0.3 + 
            sentiment_score * 0.2 +
            recency_score * 0.2
        )
        
        return round(trend_score, 3)
    
    def get_trending_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get a summary of trending topics for email notifications"""
        trending_topics = self.get_trending_topics(hours_back=hours_back)
        
        if not trending_topics:
            return {
                'has_trends': False,
                'message': f'No significant trending topics found in the last {hours_back} hours.',
                'topics': []
            }
        
        # Format topics for email
        formatted_topics = []
        for topic in trending_topics:
            formatted_topics.append({
                'keyword': topic.keyword.title(),
                'frequency': topic.frequency,
                'articles_count': topic.articles_count,
                'sentiment_label': self._sentiment_to_label(topic.avg_sentiment),
                'top_articles': [
                    {
                        'title': article['title'][:100] + '...' if len(article['title']) > 100 else article['title'],
                        'source': article['source']
                    }
                    for article in topic.recent_articles[:3]
                ]
            })
        
        return {
            'has_trends': True,
            'total_topics': len(trending_topics),
            'time_period': f'{hours_back} hours',
            'topics': formatted_topics
        }
    
    def _sentiment_to_label(self, sentiment_score: float) -> str:
        """Convert sentiment score to readable label"""
        if sentiment_score > 0.1:
            return 'Positive'
        elif sentiment_score < -0.1:
            return 'Negative'
        else:
            return 'Neutral'