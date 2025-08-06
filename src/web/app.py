from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi import Request
from typing import List, Optional, Dict, Any
import os
from datetime import datetime

from ..storage.database import DatabaseManager
from ..utils.config import get_config
from ..scraper.news_sources import NewsSourceManager
from ..processor.sentiment_analyzer import SentimentAnalyzer
from ..processor.summarizer import TextSummarizer
from ..scraper.content_extractor import ContentExtractor
from ..utils.email_service import EmailNotificationService, EmailConfig, EmailRecipient
from ..utils.export_service import CSVExportService, ExportOptions

app = FastAPI(title="Daily Digest", version="1.0.0")

config = get_config()
db_config = config.get_database_config()
db_manager = DatabaseManager(db_config.get('path', 'data/daily-digest.db'))

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Setup email service
email_service = None
def setup_email_service():
    global email_service
    try:
        email_config = config.get_email_config()
        if email_config and email_config.get('enabled', False):
            email_settings = EmailConfig(
                smtp_server=email_config['smtp_server'],
                smtp_port=email_config['smtp_port'],
                username=email_config['username'],
                password=email_config['password'],
                from_email=email_config['from_email'],
                from_name=email_config['from_name'],
                use_tls=email_config.get('use_tls', True)
            )
            email_service = EmailNotificationService(
                email_config=email_settings,
                db_manager=db_manager,
                templates_dir=templates_dir
            )
            email_service.create_subscribers_table()
            
            # Add default recipients
            for recipient in email_config.get('default_recipients', []):
                email_service.add_recipient(
                    email=recipient['email'],
                    name=recipient.get('name', '')
                )
    except Exception as e:
        print(f"Email service setup failed: {e}")

setup_email_service()

def get_db():
    return db_manager

def get_email_service():
    return email_service

def get_export_service():
    return CSVExportService(db_manager)

def get_news_manager():
    scraping_config = config.get_scraping_config()
    news_manager = NewsSourceManager(scraping_config)
    
    for source_config in config.get_sources():
        news_manager.add_source(source_config)
    
    return news_manager

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: DatabaseManager = Depends(get_db)):
    articles = db.get_articles(limit=20)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "articles": articles,
        "title": "Latest News"
    })

@app.get("/api/articles", response_model=List[Dict[str, Any]])
async def get_articles(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    source: Optional[str] = Query(None),
    db: DatabaseManager = Depends(get_db)
):
    articles = db.get_articles(limit=limit, offset=offset, source=source)
    return [
        {
            "id": article.id,
            "title": article.title,
            "summary": article.summary,
            "url": article.url,
            "source": article.source,
            "published_date": article.published_date.isoformat() if article.published_date else None,
            "scraped_date": article.scraped_date.isoformat() if article.scraped_date else None,
            "sentiment_score": article.sentiment_score,
            "sentiment_label": article.sentiment_label,
            "category": article.category,
            "keywords": article.keywords,
            "author": article.author
        }
        for article in articles
    ]

@app.get("/api/articles/{article_id}")
async def get_article(article_id: int, db: DatabaseManager = Depends(get_db)):
    article = db.get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return {
        "id": article.id,
        "title": article.title,
        "content": article.content,
        "summary": article.summary,
        "url": article.url,
        "source": article.source,
        "published_date": article.published_date.isoformat() if article.published_date else None,
        "scraped_date": article.scraped_date.isoformat() if article.scraped_date else None,
        "sentiment_score": article.sentiment_score,
        "sentiment_label": article.sentiment_label,
        "category": article.category,
        "keywords": article.keywords,
        "author": article.author
    }

@app.get("/api/sources")
async def get_sources(db: DatabaseManager = Depends(get_db)):
    sources = db.get_sources()
    return [
        {
            "id": source.id,
            "name": source.name,
            "base_url": source.base_url,
            "last_scraped": source.last_scraped.isoformat() if source.last_scraped else None,
            "is_active": source.is_active,
            "success_count": source.success_count,
            "error_count": source.error_count
        }
        for source in sources
    ]

@app.get("/api/search")
async def search_articles(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    db: DatabaseManager = Depends(get_db)
):
    articles = db.search_articles(q, limit=limit)
    return [
        {
            "id": article.id,
            "title": article.title,
            "summary": article.summary,
            "url": article.url,
            "source": article.source,
            "published_date": article.published_date.isoformat() if article.published_date else None,
            "sentiment_score": article.sentiment_score,
            "sentiment_label": article.sentiment_label,
            "keywords": article.keywords
        }
        for article in articles
    ]

@app.get("/api/analytics/sentiment")
async def get_sentiment_distribution(db: DatabaseManager = Depends(get_db)):
    distribution = db.get_sentiment_distribution()
    total_articles = db.get_article_count()
    
    return {
        "distribution": distribution,
        "total_articles": total_articles,
        "percentages": {
            label: round((count / total_articles) * 100, 2)
            for label, count in distribution.items()
        } if total_articles > 0 else {}
    }

@app.get("/api/analytics/trends")
async def get_trending_topics(
    limit: int = Query(10, ge=1, le=50),
    db: DatabaseManager = Depends(get_db)
):
    trends = db.get_trending_keywords(limit=limit)
    return {
        "trending_keywords": trends,
        "generated_at": datetime.now().isoformat()
    }

@app.post("/api/scrape")
async def trigger_scraping(
    source: Optional[str] = Query(None),
    news_manager: NewsSourceManager = Depends(get_news_manager),
    db: DatabaseManager = Depends(get_db)
):
    try:
        sentiment_analyzer = SentimentAnalyzer()
        summarizer = TextSummarizer()
        content_extractor = ContentExtractor()
        
        if source:
            articles = news_manager.scrape_source(source)
            results = {source: len(articles)}
        else:
            all_results = news_manager.scrape_all_sources()
            results = {src: len(arts) for src, arts in all_results.items()}
            articles = []
            for source_articles in all_results.values():
                articles.extend(source_articles)
        
        processed_count = 0
        for article in articles:
            if content_extractor.is_quality_content(article.title, article.content):
                sentiment_score, sentiment_label = sentiment_analyzer.analyze_sentiment_simple(
                    f"{article.title} {article.content}"
                )
                article.sentiment_score = sentiment_score
                article.sentiment_label = sentiment_label
                
                article.summary = summarizer.summarize(article.content)
                article.keywords = content_extractor.extract_keywords(article.content)
                
                if db.add_article(article):
                    processed_count += 1
                    db.update_source_stats(article.source, True)
                else:
                    db.update_source_stats(article.source, False)
        
        return {
            "message": "Scraping completed",
            "scraped_by_source": results,
            "processed_articles": processed_count,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@app.get("/article/{article_id}", response_class=HTMLResponse)
async def view_article(
    request: Request,
    article_id: int,
    db: DatabaseManager = Depends(get_db)
):
    article = db.get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return templates.TemplateResponse("article.html", {
        "request": request,
        "article": article,
        "title": article.title
    })

@app.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: Optional[str] = Query(None),
    db: DatabaseManager = Depends(get_db)
):
    articles = []
    if q:
        articles = db.search_articles(q, limit=50)
    
    return templates.TemplateResponse("search.html", {
        "request": request,
        "articles": articles,
        "query": q,
        "title": f"Search Results for '{q}'" if q else "Search Articles"
    })

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    db: DatabaseManager = Depends(get_db)
):
    sentiment_dist = db.get_sentiment_distribution()
    trending_keywords = db.get_trending_keywords(limit=20)
    total_articles = db.get_article_count()
    
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "sentiment_distribution": sentiment_dist,
        "trending_keywords": trending_keywords,
        "total_articles": total_articles,
        "title": "Analytics Dashboard"
    })

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Email API endpoints
@app.post("/api/email/send-trending")
async def send_trending_email(
    hours_back: int = 24,
    email_service: EmailNotificationService = Depends(get_email_service)
):
    """Send trending topics email immediately"""
    if not email_service:
        raise HTTPException(status_code=503, detail="Email service not configured")
    
    try:
        # Get subscribers
        recipients = email_service.get_subscribers(active_only=True)
        
        if not recipients:
            return {"success": False, "message": "No active subscribers found"}
        
        # Send email
        web_config = config.get_web_config()
        base_url = f"http://{web_config.get('host', '127.0.0.1')}:{web_config.get('port', 8000)}"
        
        result = await email_service.send_trending_topics_email(
            recipients=recipients,
            hours_back=hours_back,
            base_url=base_url
        )
        
        return {
            "success": result['success'],
            "message": f"Email sent to {result['sent_count']} recipients" if result['success'] else result.get('error'),
            "sent_count": result['sent_count'],
            "failed_count": result.get('failed_count', 0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@app.post("/api/email/test")
async def send_test_email(
    test_email: str,
    email_service: EmailNotificationService = Depends(get_email_service)
):
    """Send test email to verify configuration"""
    if not email_service:
        raise HTTPException(status_code=503, detail="Email service not configured")
    
    try:
        result = await email_service.send_test_email(test_email)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test email: {str(e)}")

@app.get("/api/email/status")
async def email_status():
    """Get email service status"""
    email_config = config.get_email_config()
    return {
        "enabled": email_config.get('enabled', False) and email_service is not None,
        "configured": bool(email_service),
        "smtp_server": email_config.get('smtp_server', 'Not configured'),
        "from_email": email_config.get('from_email', 'Not configured'),
        "subscribers_count": len(email_service.get_subscribers()) if email_service else 0
    }

# CSV Export API endpoints

@app.get("/api/export/articles")
async def export_articles_csv(
    include_content: bool = Query(False, description="Include full article content"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    source_filter: Optional[str] = Query(None, description="Filter by source"),
    sentiment_filter: Optional[str] = Query(None, description="Filter by sentiment (positive/negative/neutral)"),
    max_records: Optional[int] = Query(None, ge=1, le=10000, description="Maximum records to export"),
    export_service: CSVExportService = Depends(get_export_service)
):
    """Export articles to CSV format"""
    try:
        # Parse dates if provided
        date_from_dt = None
        date_to_dt = None
        if date_from:
            date_from_dt = datetime.fromisoformat(date_from)
        if date_to:
            date_to_dt = datetime.fromisoformat(date_to)
        
        options = ExportOptions(
            include_content=include_content,
            date_from=date_from_dt,
            date_to=date_to_dt,
            source_filter=source_filter,
            sentiment_filter=sentiment_filter,
            max_records=max_records
        )
        
        csv_content = export_service.export_articles(options)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"daily_digest_articles_{timestamp}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/api/export/analytics")
async def export_analytics_csv(
    days_back: int = Query(30, ge=1, le=365, description="Number of days to include in analysis"),
    export_service: CSVExportService = Depends(get_export_service)
):
    """Export analytics summary to CSV format"""
    try:
        csv_content = export_service.export_analytics_summary(days_back)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"daily_digest_analytics_{timestamp}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics export failed: {str(e)}")

@app.get("/api/export/trending")
async def export_trending_topics_csv(
    hours_back: int = Query(24, ge=1, le=168, description="Hours to look back for trending analysis"),
    export_service: CSVExportService = Depends(get_export_service)
):
    """Export trending topics to CSV format"""
    try:
        csv_content = export_service.export_trending_topics(hours_back)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"daily_digest_trending_{timestamp}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trending topics export failed: {str(e)}")

@app.get("/api/export/stats")
async def get_export_stats(
    export_service: CSVExportService = Depends(get_export_service)
):
    """Get statistics about available data for export"""
    try:
        stats = export_service.get_export_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get export stats: {str(e)}")