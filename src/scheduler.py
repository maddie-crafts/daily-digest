import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from typing import Dict, Any

from .storage.database import DatabaseManager
from .scraper.news_sources import NewsSourceManager
from .processor.sentiment_analyzer import SentimentAnalyzer
from .processor.summarizer import TextSummarizer
from .scraper.content_extractor import ContentExtractor
from .utils.config import Config
from .utils.email_service import EmailNotificationService, EmailConfig, EmailRecipient

class NewsScheduler:
    def __init__(self, config: Config):
        self.config = config
        self.scheduler = AsyncIOScheduler()
        self.logger = logging.getLogger('scheduler')
        
        db_config = config.get_database_config()
        self.db_manager = DatabaseManager(db_config.get('path', 'data/daily-digest.db'))
        
        scraping_config = config.get_scraping_config()
        self.news_manager = NewsSourceManager(scraping_config)
        
        for source_config in config.get_sources():
            self.news_manager.add_source(source_config)
        
        self.sentiment_analyzer = SentimentAnalyzer()
        self.summarizer = TextSummarizer()
        self.content_extractor = ContentExtractor()
        
        # Initialize email service if enabled
        self.email_service = None
        self._setup_email_service()
        
        self._setup_jobs()
    
    def _setup_email_service(self):
        """Setup email service if enabled in configuration"""
        try:
            email_config = self.config.get_email_config()
            
            if not email_config or not email_config.get('enabled', False):
                self.logger.info("Email notifications disabled in configuration")
                return
            
            # Create email configuration
            email_settings = EmailConfig(
                smtp_server=email_config['smtp_server'],
                smtp_port=email_config['smtp_port'],
                username=email_config['username'],
                password=email_config['password'],
                from_email=email_config['from_email'],
                from_name=email_config['from_name'],
                use_tls=email_config.get('use_tls', True)
            )
            
            self.email_service = EmailNotificationService(
                email_config=email_settings,
                db_manager=self.db_manager
            )
            
            # Create subscribers table
            self.email_service.create_subscribers_table()
            
            # Add default recipients
            default_recipients = email_config.get('default_recipients', [])
            for recipient in default_recipients:
                self.email_service.add_recipient(
                    email=recipient['email'],
                    name=recipient.get('name', '')
                )
            
            self.logger.info("Email service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error setting up email service: {e}")
            self.email_service = None
    
    def _setup_jobs(self):
        scheduling_config = self.config.get_scheduling_config()
        
        scrape_interval = scheduling_config.get('scrape_interval_hours', 4)
        cleanup_interval = scheduling_config.get('cleanup_interval_hours', 24)
        
        self.scheduler.add_job(
            self.scrape_all_sources,
            IntervalTrigger(hours=scrape_interval),
            id='scrape_news',
            name='Scrape news from all sources',
            replace_existing=True
        )
        
        self.scheduler.add_job(
            self.cleanup_old_articles,
            IntervalTrigger(hours=cleanup_interval),
            id='cleanup_articles',
            name='Clean up old articles',
            replace_existing=True
        )
        
        # Schedule email notifications if enabled
        if self.email_service:
            email_config = self.config.get_email_config()
            if email_config.get('trending_topics_enabled', True):
                send_hour = email_config.get('send_time_hour', 9)
                send_minute = email_config.get('send_time_minute', 0)
                
                # Schedule daily trending topics email
                from apscheduler.triggers.cron import CronTrigger
                self.scheduler.add_job(
                    self.send_trending_topics_email,
                    CronTrigger(hour=send_hour, minute=send_minute),
                    id='trending_topics_email',
                    name='Send trending topics email',
                    replace_existing=True
                )
                
                self.logger.info(f"Scheduled trending topics email at {send_hour:02d}:{send_minute:02d} daily")
        
        self.logger.info(f"Scheduled scraping every {scrape_interval} hours")
        self.logger.info(f"Scheduled cleanup every {cleanup_interval} hours")
    
    async def scrape_all_sources(self):
        self.logger.info("Starting scheduled scraping of all sources")
        try:
            start_time = datetime.now()
            
            all_results = self.news_manager.scrape_all_sources()
            
            total_scraped = 0
            total_processed = 0
            
            for source_name, articles in all_results.items():
                total_scraped += len(articles)
    
                for article in articles:
                    try:
                        if self.content_extractor.is_quality_content(article.title, article.content):
                            sentiment_score, sentiment_label = self.sentiment_analyzer.analyze_sentiment_simple(
                                f"{article.title} {article.content}"
                            )
                            article.sentiment_score = sentiment_score
                            article.sentiment_label = sentiment_label
                            
                            article.summary = self.summarizer.summarize(article.content)
                            article.keywords = self.content_extractor.extract_keywords(article.content)
                            
                            if self.db_manager.add_article(article):
                                total_processed += 1
                                self.db_manager.update_source_stats(source_name, True)
                            else:
                                self.db_manager.update_source_stats(source_name, False)
                    except Exception as e:
                        self.logger.error(f"Error processing article from {source_name}: {e}")
                        self.db_manager.update_source_stats(source_name, False)
            
            duration = datetime.now() - start_time
            self.logger.info(
                f"Scraping completed in {duration.total_seconds():.1f}s. "
                f"Scraped: {total_scraped}, Processed: {total_processed}"
            )
            
        except Exception as e:
            self.logger.error(f"Error during scheduled scraping: {e}")
    
    async def cleanup_old_articles(self):
        self.logger.info("Starting scheduled cleanup of old articles")
        try:
            db_config = self.config.get_database_config()
            retention_days = db_config.get('retention_days', 30)
            
            deleted_count = self.db_manager.cleanup_old_articles(retention_days)
            self.logger.info(f"Cleaned up {deleted_count} old articles (older than {retention_days} days)")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    async def send_trending_topics_email(self):
        """Send trending topics email to subscribers"""
        if not self.email_service:
            self.logger.warning("Email service not available")
            return
        
        try:
            self.logger.info("Starting to send trending topics email")
            
            # Get email configuration
            email_config = self.config.get_email_config()
            hours_back = email_config.get('hours_back_for_trends', 24)
            
            # Get subscribers
            recipients = self.email_service.get_subscribers(active_only=True)
            
            if not recipients:
                self.logger.info("No active email subscribers found")
                return
            
            # Send the email
            web_config = self.config.get_web_config()
            base_url = f"http://{web_config.get('host', '127.0.0.1')}:{web_config.get('port', 8000)}"
            
            result = await self.email_service.send_trending_topics_email(
                recipients=recipients,
                hours_back=hours_back,
                base_url=base_url
            )
            
            if result['success']:
                self.logger.info(
                    f"Trending topics email sent successfully to {result['sent_count']} recipients"
                )
            else:
                self.logger.error(f"Failed to send trending topics email: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.logger.error(f"Error sending trending topics email: {e}")
    
    def start(self):
        self.logger.info("Starting news scheduler")
        self.scheduler.start()
    
    def shutdown(self):
        self.logger.info("Shutting down news scheduler")
        self.scheduler.shutdown()
    
    def get_job_status(self) -> Dict[str, Any]:
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return {
            'running': self.scheduler.running,
            'jobs': jobs,
            'status_time': datetime.now().isoformat()
        }