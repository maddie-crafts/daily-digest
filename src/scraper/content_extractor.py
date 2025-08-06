import re
from typing import List, Set
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class ContentExtractor:
    def __init__(self, duplicate_threshold: float = 0.8):
        self.duplicate_threshold = duplicate_threshold
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> str:
        text = self.clean_text(text)
        words = text.split()
        
        if len(words) < 10:
            return ""
        
        try:
            tfidf_matrix = self.vectorizer.fit_transform([text])
            feature_names = self.vectorizer.get_feature_names_out()
            tfidf_scores = tfidf_matrix.toarray()[0]
            
            keyword_scores = list(zip(feature_names, tfidf_scores))
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            
            keywords = [kw[0] for kw in keyword_scores[:max_keywords] if kw[1] > 0]
            return ", ".join(keywords)
        except Exception:
            return self._extract_keywords_fallback(text, max_keywords)
    
    def _extract_keywords_fallback(self, text: str, max_keywords: int) -> str:
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        
        stop_words = {
            'this', 'that', 'with', 'have', 'will', 'from', 'they', 'been', 
            'were', 'said', 'each', 'which', 'their', 'time', 'would', 'there',
            'could', 'other', 'more', 'very', 'what', 'know', 'just', 'first',
            'get', 'over', 'think', 'also', 'back', 'after', 'use', 'two',
            'how', 'our', 'work', 'life', 'only', 'can', 'still', 'should',
            'must', 'want', 'need', 'make', 'take', 'come', 'year', 'years'
        }
        
        filtered_words = [word for word in words if word not in stop_words]
        
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word[0] for word in sorted_words[:max_keywords]]
        
        return ", ".join(keywords)
    
    def clean_text(self, text: str) -> str:
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text
    
    def detect_duplicates(self, articles: List[str]) -> List[Set[int]]:
        if len(articles) < 2:
            return []
        
        try:
            tfidf_matrix = self.vectorizer.fit_transform(articles)
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            duplicates = []
            processed = set()
            
            for i in range(len(articles)):
                if i in processed:
                    continue
                
                duplicate_group = {i}
                for j in range(i + 1, len(articles)):
                    if j in processed:
                        continue
                    
                    if similarity_matrix[i][j] >= self.duplicate_threshold:
                        duplicate_group.add(j)
                        processed.add(j)
                
                if len(duplicate_group) > 1:
                    duplicates.append(duplicate_group)
                    processed.update(duplicate_group)
            
            return duplicates
        except Exception:
            return []
    
    def is_quality_content(self, title: str, content: str, min_length: int = 100) -> bool:
        if not title or not content:
            return False
        
        if len(content) < min_length:
            return False
        
        title_words = len(title.split())
        if title_words < 3 or title_words > 20:
            return False
        
        spam_indicators = [
            'click here', 'buy now', 'limited time', 'act now',
            'free trial', 'sign up now', 'subscribe', 'download now'
        ]
        
        content_lower = content.lower()
        spam_count = sum(1 for indicator in spam_indicators if indicator in content_lower)
        if spam_count > 2:
            return False
        
        sentence_count = len(re.findall(r'[.!?]+', content))
        if sentence_count < 3:
            return False
        
        return True