import pytest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
from datetime import datetime

from src.scraper.base_scraper import BaseScraper
from src.scraper.content_extractor import ContentExtractor
from src.storage.models import Article

class TestBaseScraper:
    def setup_method(self):
        self.source_config = {
            'name': 'Test Source',
            'base_url': 'https://example.com',
            'selectors': {
                'article_links': 'a.article-link',
                'title': 'h1',
                'content': '.content',
                'date': 'time'
            },
            'rate_limit': 1,
            'max_articles': 5
        }
        
        self.scraping_config = {
            'user_agent': 'TestBot/1.0',
            'timeout': 10,
            'retry_attempts': 2,
            'min_content_length': 50
        }
        
        self.scraper = BaseScraper(self.source_config, self.scraping_config)
    
    def test_scraper_initialization(self):
        assert self.scraper.source_name == 'Test Source'
        assert self.scraper.base_url == 'https://example.com'
        assert self.scraper.rate_limit == 1
        assert self.scraper.max_articles == 5
    
    @patch('src.scraper.base_scraper.requests.Session.get')
    def test_fetch_page_success(self, mock_get):
        mock_response = Mock()
        mock_response.content = b'<html><body>Test content</body></html>'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        soup = self.scraper.fetch_page('https://example.com/test')
        
        assert soup is not None
        assert soup.find('body').text == 'Test content'
    
    @patch('src.scraper.base_scraper.requests.Session.get')
    def test_fetch_page_failure(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        
        soup = self.scraper.fetch_page('https://example.com/test')
        
        assert soup is None
    
    def test_extract_article_links(self):
        html = '''
        <html>
            <body>
                <a class="article-link" href="/article1">Article 1</a>
                <a class="article-link" href="/article2">Article 2</a>
                <a href="/other">Other link</a>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        links = self.scraper.extract_article_links(soup)
        
        assert len(links) == 2
        assert 'https://example.com/article1' in links
        assert 'https://example.com/article2' in links
    
    def test_is_valid_article_url(self):
        assert self.scraper._is_valid_article_url('https://example.com/article')
        assert not self.scraper._is_valid_article_url('https://example.com/video/')
        assert not self.scraper._is_valid_article_url('javascript:void(0)')
        assert not self.scraper._is_valid_article_url('mailto:test@example.com')
    
    def test_extract_title(self):
        html = '<html><body><h1>Test Article Title</h1></body></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        title = self.scraper._extract_title(soup)
        
        assert title == 'Test Article Title'
    
    def test_extract_content(self):
        html = '''
        <html>
            <body>
                <div class="content">
                    <p>First paragraph of content.</p>
                    <p>Second paragraph of content.</p>
                </div>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        content = self.scraper._extract_content(soup)
        
        assert 'First paragraph of content.' in content
        assert 'Second paragraph of content.' in content
    
    def test_clean_content(self):
        content = "   This is    a test   with   extra   spaces.   "
        cleaned = self.scraper._clean_content(content)
        
        assert cleaned == "This is a test with extra spaces."
    
    def test_parse_date(self):
        date_str = "2024-01-15T10:30:00Z"
        parsed_date = self.scraper._parse_date(date_str)
        
        assert parsed_date is not None
        assert parsed_date.year == 2024
        assert parsed_date.month == 1
        assert parsed_date.day == 15

class TestContentExtractor:
    def setup_method(self):
        self.extractor = ContentExtractor()
    
    def test_clean_text(self):
        text = "<p>This is <b>bold</b> text with <a href='#'>links</a>.</p>"
        cleaned = self.extractor.clean_text(text)
        
        assert cleaned == "This is bold text with links."
    
    def test_extract_keywords_fallback(self):
        text = "This is a test article about machine learning and artificial intelligence."
        keywords = self.extractor._extract_keywords_fallback(text, 5)
        
        assert isinstance(keywords, str)
        assert len(keywords) > 0
    
    def test_is_quality_content(self):
        good_title = "Breaking News: Important Event Happens"
        good_content = "This is a detailed article about an important event that happened today. " * 5
        
        bad_title = ""
        bad_content = "Short"
        
        assert self.extractor.is_quality_content(good_title, good_content, min_length=50)
        assert not self.extractor.is_quality_content(bad_title, bad_content, min_length=50)
    
    def test_detect_duplicates(self):
        articles = [
            "This is the first article about news",
            "This is the second article about different news",
            "This is the first article about news with minor changes"
        ]
        
        duplicates = self.extractor.detect_duplicates(articles)
        
        assert isinstance(duplicates, list)