import re
import nltk
from typing import List, Dict
from collections import Counter

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords

class TextProcessor:
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.stop_words.update([
            'said', 'says', 'would', 'could', 'should', 'may', 'might',
            'according', 'report', 'reports', 'news', 'article', 'story',
            'clickbait'
        ])
    
    def clean_text(self, text: str) -> str:
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text
    
    def tokenize_sentences(self, text: str) -> List[str]:
        try:
            sentences = sent_tokenize(text)
            return [s.strip() for s in sentences if len(s.strip()) > 10]
        except Exception:
            # Split on sentence endings and preserve them
            parts = re.split(r'([.!?])', text)
            sentences = []
            for i in range(0, len(parts)-1, 2):
                if i+1 < len(parts):
                    sentence = parts[i].strip() + parts[i+1]
                    if len(sentence.strip()) > 10:
                        sentences.append(sentence.strip())
            return sentences
    
    def tokenize_words(self, text: str) -> List[str]:
        try:
            words = word_tokenize(text.lower())
            return [word for word in words if word.isalpha() and word not in self.stop_words]
        except Exception:
            words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
            return [word for word in words if word not in self.stop_words]
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        entities = {
            'people': [],
            'organizations': [],
            'locations': [],
            'money': [],
            'dates': []
        }
        
        people_pattern = r'\b[A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b'
        entities['people'] = list(set(re.findall(people_pattern, text)))
        
        org_keywords = ['Corp', 'Inc', 'Ltd', 'Company', 'Organization', 'University', 'Institute']
        org_pattern = r'\b(?:[A-Z][a-z]*\s*)+(?:' + '|'.join(org_keywords) + r')\b'
        entities['organizations'] = list(set(re.findall(org_pattern, text)))
        
        money_pattern = r'\$[\d,.]+'
        entities['money'] = list(set(re.findall(money_pattern, text)))
        
        date_patterns = [
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b'
        ]
        for pattern in date_patterns:
            entities['dates'].extend(re.findall(pattern, text))
        entities['dates'] = list(set(entities['dates']))
        
        return entities
    
    def calculate_readability_score(self, text: str) -> float:
        sentences = self.tokenize_sentences(text)
        words = self.tokenize_words(text)
        
        if not sentences or not words:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        
        syllable_count = sum(self._count_syllables(word) for word in words)
        avg_syllables_per_word = syllable_count / len(words) if words else 0
        
        flesch_score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
        
        return float(max(0, min(100, flesch_score)))
    
    def _count_syllables(self, word: str) -> int:
        word = word.lower()
        vowels = "aeiouy"
        syllable_count = 0
        prev_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                syllable_count += 1
            prev_was_vowel = is_vowel
        
        if word.endswith('e'):
            syllable_count -= 1
        
        return max(1, syllable_count)
    
    def get_word_frequency(self, text: str, top_n: int = 20) -> Dict[str, int]:
        words = self.tokenize_words(text)
        word_freq = Counter(words)
        return dict(word_freq.most_common(top_n))
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        words1 = set(self.tokenize_words(text1))
        words2 = set(self.tokenize_words(text2))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0