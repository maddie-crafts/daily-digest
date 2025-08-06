import pytest
from src.processor.text_processor import TextProcessor
from src.processor.sentiment_analyzer import SentimentAnalyzer
from src.processor.summarizer import TextSummarizer

class TestTextProcessor:
    def setup_method(self):
        self.processor = TextProcessor()
    
    def test_clean_text(self):
        text = "<p>This is a test</p>\n\nwith HTML tags and   extra   spaces."
        cleaned = self.processor.clean_text(text)
        
        assert "<p>" not in cleaned
        assert "</p>" not in cleaned
        assert "This is a test with HTML tags and extra spaces." in cleaned
    
    def test_tokenize_sentences(self):
        text = "This is the first sentence. This is the second sentence! Is this a question?"
        sentences = self.processor.tokenize_sentences(text)
        
        assert len(sentences) == 3
        assert "This is the first sentence." in sentences[0]
        assert "This is the second sentence!" in sentences[1]
        assert "Is this a question?" in sentences[2]
    
    def test_tokenize_words(self):
        text = "This is a test sentence with some common words."
        words = self.processor.tokenize_words(text)
        
        assert isinstance(words, list)
        assert len(words) > 0
        assert "this" not in words  # Should be filtered out as stopword
        assert "test" in words
        assert "sentence" in words
    
    def test_extract_entities(self):
        text = "John Smith works for Apple Inc in New York. The company made $1.2 billion on January 15, 2024."
        entities = self.processor.extract_entities(text)
        
        assert "people" in entities
        assert "organizations" in entities
        assert "locations" in entities
        assert "money" in entities
        assert "dates" in entities
        
        assert len(entities["people"]) > 0
        assert len(entities["money"]) > 0
    
    def test_calculate_readability_score(self):
        simple_text = "This is simple. Very easy to read."
        complex_text = "The implementation of sophisticated algorithms requires comprehensive understanding of computational complexity theory and mathematical foundations."
        
        simple_score = self.processor.calculate_readability_score(simple_text)
        complex_score = self.processor.calculate_readability_score(complex_text)
        
        assert isinstance(simple_score, float)
        assert isinstance(complex_score, float)
        assert 0 <= simple_score <= 100
        assert 0 <= complex_score <= 100
    
    def test_get_word_frequency(self):
        text = "test word test another word test"
        freq = self.processor.get_word_frequency(text, top_n=5)
        
        assert isinstance(freq, dict)
        assert "test" in freq
        assert freq["test"] == 3
        assert freq["word"] == 2
    
    def test_calculate_text_similarity(self):
        text1 = "This is about machine learning and AI"
        text2 = "This discusses machine learning and artificial intelligence"
        text3 = "Completely different topic about cooking recipes"
        
        similarity_high = self.processor.calculate_text_similarity(text1, text2)
        similarity_low = self.processor.calculate_text_similarity(text1, text3)
        
        assert isinstance(similarity_high, float)
        assert isinstance(similarity_low, float)
        assert 0 <= similarity_high <= 1
        assert 0 <= similarity_low <= 1
        assert similarity_high > similarity_low

class TestSentimentAnalyzer:
    def setup_method(self):
        self.analyzer = SentimentAnalyzer()
    
    def test_analyze_sentiment_positive(self):
        positive_text = "This is wonderful news! I'm so happy and excited about this amazing development."
        result = self.analyzer.analyze_sentiment(positive_text)
        
        assert isinstance(result, dict)
        assert "score" in result
        assert "label" in result
        assert result["label"] in ["positive", "negative", "neutral"]
        assert -1 <= result["score"] <= 1
    
    def test_analyze_sentiment_negative(self):
        negative_text = "This is terrible news. I'm very disappointed and angry about this awful situation."
        result = self.analyzer.analyze_sentiment(negative_text)
        
        assert isinstance(result, dict)
        assert "score" in result
        assert "label" in result
        assert result["label"] in ["positive", "negative", "neutral"]
    
    def test_analyze_sentiment_neutral(self):
        neutral_text = "The weather report indicates partly cloudy conditions with temperatures around 20 degrees."
        result = self.analyzer.analyze_sentiment(neutral_text)
        
        assert isinstance(result, dict)
        assert "score" in result
        assert "label" in result
        assert result["label"] in ["positive", "negative", "neutral"]
    
    def test_analyze_sentiment_simple(self):
        text = "This is a good day."
        score, label = self.analyzer.analyze_sentiment_simple(text)
        
        assert isinstance(score, float)
        assert isinstance(label, str)
        assert -1 <= score <= 1
        assert label in ["positive", "negative", "neutral"]
    
    def test_batch_analyze_sentiment(self):
        texts = [
            "Great news!",
            "Terrible situation.",
            "Regular update."
        ]
        results = self.analyzer.batch_analyze_sentiment(texts)
        
        assert isinstance(results, list)
        assert len(results) == 3
        assert all("score" in result and "label" in result for result in results)

class TestTextSummarizer:
    def setup_method(self):
        self.summarizer = TextSummarizer(summary_sentences=2)
    
    def test_summarize_short_text(self):
        short_text = "This is a short text. It only has two sentences."
        summary = self.summarizer.summarize(short_text, max_sentences=3)
        
        assert summary == short_text
    
    def test_summarize_long_text(self):
        long_text = """
        This is the first sentence of a longer article. This is the second sentence with important information.
        This is the third sentence with more details. This is the fourth sentence with additional context.
        This is the fifth sentence with concluding remarks. This is the sixth sentence with final thoughts.
        """
        summary = self.summarizer.summarize(long_text.strip(), max_sentences=2)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert len(summary) < len(long_text)
    
    def test_get_key_phrases(self):
        text = "Machine learning algorithms are important for data science. Natural language processing is also important for data science."
        phrases = self.summarizer.get_key_phrases(text, max_phrases=3)
        
        assert isinstance(phrases, list)
        assert len(phrases) <= 3
        assert all(isinstance(phrase, str) for phrase in phrases)