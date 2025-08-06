import pytest
import tempfile
import os
from datetime import datetime, timedelta

from src.storage.database import DatabaseManager
from src.storage.models import Article, Source

class TestDatabaseManager:
    def setup_method(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_manager = DatabaseManager(self.temp_db.name)
    
    def teardown_method(self):
        os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            assert 'sources' in tables
            assert 'articles' in tables
    
    def test_add_and_get_sources(self):
        source = Source(
            name="Test Source",
            base_url="https://example.com",
            scraping_config="{}",
            is_active=True
        )
        
        source_id = self.db_manager.add_source(source)
        assert source_id is not None
        
        sources = self.db_manager.get_sources()
        assert len(sources) == 1
        assert sources[0].name == "Test Source"
        assert sources[0].base_url == "https://example.com"
        assert sources[0].is_active == True
    
    def test_add_and_get_articles(self):
        article = Article(
            title="Test Article",
            content="This is test content for the article.",
            summary="Test summary",
            url="https://example.com/article1",
            source="Test Source",
            published_date=datetime.now(),
            sentiment_score=0.5,
            sentiment_label="positive",
            category="test",
            keywords="test, article",
            author="Test Author"
        )
        
        article_id = self.db_manager.add_article(article)
        assert article_id is not None
        
        articles = self.db_manager.get_articles(limit=10)
        assert len(articles) == 1
        assert articles[0].title == "Test Article"
        assert articles[0].content == "This is test content for the article."
        assert articles[0].sentiment_label == "positive"
    
    def test_get_article_by_id(self):
        article = Article(
            title="Test Article",
            content="This is test content.",
            url="https://example.com/article1",
            source="Test Source"
        )
        
        article_id = self.db_manager.add_article(article)
        retrieved_article = self.db_manager.get_article_by_id(article_id)
        
        assert retrieved_article is not None
        assert retrieved_article.title == "Test Article"
        assert retrieved_article.content == "This is test content."
    
    def test_search_articles(self):
        article1 = Article(
            title="Machine Learning Article",
            content="This article discusses machine learning algorithms.",
            url="https://example.com/ml",
            source="Test Source"
        )
        
        article2 = Article(
            title="Python Programming",
            content="This article is about Python programming language.",
            url="https://example.com/python",
            source="Test Source"
        )
        
        self.db_manager.add_article(article1)
        self.db_manager.add_article(article2)
        
        ml_results = self.db_manager.search_articles("machine learning")
        python_results = self.db_manager.search_articles("Python")
        
        assert len(ml_results) == 1
        assert ml_results[0].title == "Machine Learning Article"
        
        assert len(python_results) == 1
        assert python_results[0].title == "Python Programming"
    
    def test_duplicate_article_handling(self):
        article1 = Article(
            title="Test Article",
            content="Test content",
            url="https://example.com/same",
            source="Test Source"
        )
        
        article2 = Article(
            title="Different Title",
            content="Different content",
            url="https://example.com/same",  # Same URL
            source="Test Source"
        )
        
        id1 = self.db_manager.add_article(article1)
        id2 = self.db_manager.add_article(article2)  # Should fail due to duplicate URL
        
        assert id1 is not None
        assert id2 is None  # Should be None because of duplicate URL
        
        articles = self.db_manager.get_articles()
        assert len(articles) == 1
    
    def test_update_source_stats(self):
        source = Source(
            name="Test Source",
            base_url="https://example.com",
            is_active=True
        )
        
        self.db_manager.add_source(source)
        
        self.db_manager.update_source_stats("Test Source", success=True)
        self.db_manager.update_source_stats("Test Source", success=False)
        
        sources = self.db_manager.get_sources()
        assert len(sources) == 1
        assert sources[0].success_count == 1
        assert sources[0].error_count == 1
    
    def test_cleanup_old_articles(self):
        old_article = Article(
            title="Old Article",
            content="Old content",
            url="https://example.com/old",
            source="Test Source"
        )
        
        new_article = Article(
            title="New Article",
            content="New content",
            url="https://example.com/new",
            source="Test Source"
        )
        
        self.db_manager.add_article(old_article)
        self.db_manager.add_article(new_article)
        
        # Manually update the old article's date to be older
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            old_date = datetime.now() - timedelta(days=35)
            cursor.execute(
                "UPDATE articles SET scraped_date = ? WHERE title = ?",
                (old_date, "Old Article")
            )
            conn.commit()
        
        deleted_count = self.db_manager.cleanup_old_articles(retention_days=30)
        
        assert deleted_count == 1
        
        remaining_articles = self.db_manager.get_articles()
        assert len(remaining_articles) == 1
        assert remaining_articles[0].title == "New Article"
    
    def test_get_article_count(self):
        assert self.db_manager.get_article_count() == 0
        
        article = Article(
            title="Test Article",
            content="Test content",
            url="https://example.com/test",
            source="Test Source"
        )
        
        self.db_manager.add_article(article)
        assert self.db_manager.get_article_count() == 1
    
    def test_get_sentiment_distribution(self):
        articles = [
            Article(title="Positive", content="Good news", url="https://example.com/1", 
                   source="Test", sentiment_label="positive"),
            Article(title="Negative", content="Bad news", url="https://example.com/2", 
                   source="Test", sentiment_label="negative"),
            Article(title="Positive2", content="More good news", url="https://example.com/3", 
                   source="Test", sentiment_label="positive"),
        ]
        
        for article in articles:
            self.db_manager.add_article(article)
        
        distribution = self.db_manager.get_sentiment_distribution()
        
        assert distribution["positive"] == 2
        assert distribution["negative"] == 1