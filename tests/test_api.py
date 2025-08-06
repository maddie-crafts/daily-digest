import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import patch, Mock

from src.web.app import app, get_db
from src.storage.models import Article, Source
from datetime import datetime

@pytest.fixture(scope="function")
def mock_db():
    return Mock()

@pytest.fixture(scope="function")
async def client(mock_db):
    from httpx import ASGITransport
    
    # Override the dependency
    app.dependency_overrides[get_db] = lambda: mock_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    # Clean up after test
    app.dependency_overrides.clear()

class TestAPI:
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_get_articles_endpoint(self, client, mock_db):
        mock_article = Article(
            id=1,
            title="Test Article",
            summary="Test summary",
            url="https://example.com/test",
            source="Test Source",
            published_date=datetime.now(),
            scraped_date=datetime.now(),
            sentiment_score=0.5,
            sentiment_label="positive",
            category="test",
            keywords="test, keywords",
            author="Test Author"
        )
        mock_db.get_articles.return_value = [mock_article]
        
        response = await client.get("/api/articles")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Article"
        assert data[0]["source"] == "Test Source"
        assert data[0]["sentiment_label"] == "positive"
    
    @pytest.mark.asyncio
    async def test_get_article_by_id_endpoint(self, client, mock_db):
        mock_article = Article(
            id=1,
            title="Test Article",
            content="Test content",
            summary="Test summary",
            url="https://example.com/test",
            source="Test Source",
            published_date=datetime.now(),
            scraped_date=datetime.now(),
            sentiment_score=0.5,
            sentiment_label="positive",
            category="test",
            keywords="test, keywords",
            author="Test Author"
        )
        mock_db.get_article_by_id.return_value = mock_article
        
        response = await client.get("/api/articles/1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == 1
        assert data["title"] == "Test Article"
        assert data["content"] == "Test content"
    
    @pytest.mark.asyncio
    async def test_get_article_not_found(self, client, mock_db):
        mock_db.get_article_by_id.return_value = None
        
        response = await client.get("/api/articles/999")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Article not found"
    
    @pytest.mark.asyncio
    async def test_get_sources_endpoint(self, client, mock_db):
        mock_source = Source(
            id=1,
            name="Test Source",
            base_url="https://example.com",
            last_scraped=datetime.now(),
            is_active=True,
            success_count=10,
            error_count=2
        )
        mock_db.get_sources.return_value = [mock_source]
        
        response = await client.get("/api/sources")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Source"
        assert data[0]["is_active"] == True
        assert data[0]["success_count"] == 10
    
    @pytest.mark.asyncio
    async def test_search_articles_endpoint(self, client, mock_db):
        mock_article = Article(
            id=1,
            title="Test Article about Python",
            summary="Test summary",
            url="https://example.com/python",
            source="Test Source",
            published_date=datetime.now(),
            sentiment_score=0.5,
            sentiment_label="positive",
            keywords="python, programming"
        )
        mock_db.search_articles.return_value = [mock_article]
        
        response = await client.get("/api/search?q=python")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Article about Python"
        assert "python" in data[0]["keywords"]
    
    @pytest.mark.asyncio
    async def test_get_sentiment_distribution(self, client, mock_db):
        mock_db.get_sentiment_distribution.return_value = {
            "positive": 15,
            "negative": 5,
            "neutral": 10
        }
        mock_db.get_article_count.return_value = 30
        
        response = await client.get("/api/analytics/sentiment")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_articles"] == 30
        assert data["distribution"]["positive"] == 15
        assert data["percentages"]["positive"] == 50.0
    
    @pytest.mark.asyncio
    async def test_get_trending_topics(self, client, mock_db):
        mock_db.get_trending_keywords.return_value = [
            {"keyword": "python", "frequency": 10},
            {"keyword": "machine learning", "frequency": 8}
        ]

        
        response = await client.get("/api/analytics/trends")
        assert response.status_code == 200
        
        data = response.json()
        assert "trending_keywords" in data
        assert len(data["trending_keywords"]) == 2
        assert data["trending_keywords"][0]["keyword"] == "python"
        assert data["trending_keywords"][0]["frequency"] == 10