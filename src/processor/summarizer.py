from typing import List, Dict
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from .text_processor import TextProcessor

class TextSummarizer:
    def __init__(self, summary_sentences: int = 3):
        self.summary_sentences = summary_sentences
        self.text_processor = TextProcessor()
    
    def summarize(self, text: str, max_sentences: int = None) -> str:
        if max_sentences is None:
            max_sentences = self.summary_sentences
        
        sentences = self.text_processor.tokenize_sentences(text)
        
        if len(sentences) <= max_sentences:
            return text
        
        try:
            return self._extractive_summarization(sentences, max_sentences)
        except Exception:
            return self._simple_summarization(sentences, max_sentences)
    
    def _extractive_summarization(self, sentences: List[str], max_sentences: int) -> str:
        if len(sentences) <= max_sentences:
            return ' '.join(sentences)
        
        sentence_scores = self._calculate_sentence_scores(sentences)
        
        top_sentences = sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:max_sentences]
        
        top_indices = [item[0] for item in top_sentences]
        top_indices.sort()
        
        summary_sentences = [sentences[i] for i in top_indices]
        return ' '.join(summary_sentences)
    
    def _calculate_sentence_scores(self, sentences: List[str]) -> Dict[int, float]:
        try:
            vectorizer = TfidfVectorizer(stop_words='english', max_features=100)
            tfidf_matrix = vectorizer.fit_transform(sentences)
            
            sentence_scores = {}
            for i, sentence in enumerate(sentences):
                sentence_scores[i] = np.sum(tfidf_matrix[i].toarray())
            
            return sentence_scores
        except Exception:
            return self._fallback_sentence_scoring(sentences)
    
    def _fallback_sentence_scoring(self, sentences: List[str]) -> Dict[int, float]:
        word_freq = self._get_word_frequency(sentences)
        
        sentence_scores = {}
        for i, sentence in enumerate(sentences):
            words = self.text_processor.tokenize_words(sentence)
            score = sum(word_freq.get(word, 0) for word in words)
            sentence_scores[i] = score / len(words) if words else 0
        
        return sentence_scores
    
    def _get_word_frequency(self, sentences: List[str]) -> Dict[str, int]:
        all_words = []
        for sentence in sentences:
            words = self.text_processor.tokenize_words(sentence)
            all_words.extend(words)
        
        word_freq = Counter(all_words)
        max_freq = max(word_freq.values()) if word_freq else 1
        
        normalized_freq = {}
        for word, freq in word_freq.items():
            normalized_freq[word] = freq / max_freq
        
        return normalized_freq
    
    def _simple_summarization(self, sentences: List[str], max_sentences: int) -> str:
        if len(sentences) <= max_sentences:
            return ' '.join(sentences)
        
        sentence_lengths = [len(sentence.split()) for sentence in sentences]
        avg_length = sum(sentence_lengths) / len(sentence_lengths)
        
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            score = 0
            
            if i == 0:
                score += 2
            
            if sentence_lengths[i] > avg_length * 0.8:
                score += 1
            
            if any(keyword in sentence.lower() for keyword in ['important', 'significant', 'major', 'key']):
                score += 1
            
            scored_sentences.append((i, score, sentence))
        
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        selected_indices = [item[0] for item in scored_sentences[:max_sentences]]
        selected_indices.sort()
        
        summary_sentences = [sentences[i] for i in selected_indices]
        return ' '.join(summary_sentences)
    
    def get_key_phrases(self, text: str, max_phrases: int = 5) -> List[str]:
        sentences = self.text_processor.tokenize_sentences(text)
        
        phrases = []
        for sentence in sentences:
            words = sentence.split()
            for i in range(len(words) - 1):
                phrase = ' '.join(words[i:i+2])
                if len(phrase) > 5 and phrase.lower() not in ['the', 'and', 'but', 'for']:
                    phrases.append(phrase)
        
        phrase_freq = Counter(phrases)
        top_phrases = [phrase for phrase, count in phrase_freq.most_common(max_phrases)]
        
        return top_phrases