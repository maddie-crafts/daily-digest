"""
CSV Export service for Daily Digest
"""
import csv
import io
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..storage.database import DatabaseManager
from ..processor.trending_analyzer import TrendingAnalyzer


@dataclass
class ExportOptions:
    """Options for CSV export"""
    include_content: bool = False  # Include full article content (makes files large)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    source_filter: Optional[str] = None
    sentiment_filter: Optional[str] = None
    max_records: Optional[int] = None


class CSVExportService:
    """Service for exporting data to CSV format"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger('csv_export')
        self.trending_analyzer = TrendingAnalyzer(db_manager)
    
    def export_articles(self, options: ExportOptions = None) -> str:
        """
        Export articles to CSV format
        
        Args:
            options: Export options for filtering and customization
            
        Returns:
            CSV content as string
        """
        if options is None:
            options = ExportOptions()
        
        try:
            # Build query based on options
            articles = self._get_filtered_articles(options)
            
            if not articles:
                return self._create_empty_csv(['id', 'title', 'source', 'published_date', 'sentiment'])
            
            # Create CSV content
            output = io.StringIO()
            
            # Define column headers
            headers = [
                'id', 'title', 'source', 'url', 'published_date', 'scraped_date',
                'sentiment_score', 'sentiment_label', 'category', 'keywords', 'author'
            ]
            
            if options.include_content:
                headers.extend(['content', 'summary'])
            
            writer = csv.writer(output)
            writer.writerow(headers)
            
            # Write article data
            for article in articles:
                row = [
                    article.get('id', ''),
                    article.get('title', ''),
                    article.get('source', ''),
                    article.get('url', ''),
                    self._format_datetime(article.get('published_date')),
                    self._format_datetime(article.get('scraped_date')),
                    article.get('sentiment_score', ''),
                    article.get('sentiment_label', ''),
                    article.get('category', ''),
                    article.get('keywords', ''),
                    article.get('author', '')
                ]
                
                if options.include_content:
                    row.extend([
                        article.get('content', ''),
                        article.get('summary', '')
                    ])
                
                writer.writerow(row)
            
            return output.getvalue()
            
        except Exception as e:
            self.logger.error(f"Error exporting articles: {e}")
            raise
    
    def export_analytics_summary(self, days_back: int = 30) -> str:
        """
        Export analytics summary to CSV
        
        Args:
            days_back: Number of days to include in analysis
            
        Returns:
            CSV content as string
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            # Get analytics data
            sentiment_dist = self.db_manager.get_sentiment_distribution()
            trending_keywords = self.db_manager.get_trending_keywords(limit=50)
            total_articles = self.db_manager.get_article_count()
            
            # Get articles by source
            articles_by_source = self._get_articles_by_source(cutoff_date)
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write summary section
            writer.writerow(['=== ANALYTICS SUMMARY ==='])
            writer.writerow(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow(['Period', f'Last {days_back} days'])
            writer.writerow(['Total Articles', total_articles])
            writer.writerow([])
            
            # Write sentiment distribution
            writer.writerow(['=== SENTIMENT DISTRIBUTION ==='])
            writer.writerow(['Sentiment', 'Count', 'Percentage'])
            total_sentiment = sum(sentiment_dist.values()) if sentiment_dist else 1
            
            for sentiment, count in sentiment_dist.items():
                percentage = (count / total_sentiment) * 100
                writer.writerow([sentiment.title(), count, f'{percentage:.1f}%'])
            writer.writerow([])
            
            # Write articles by source
            writer.writerow(['=== ARTICLES BY SOURCE ==='])
            writer.writerow(['Source', 'Article Count', 'Avg Sentiment'])
            
            for source_data in articles_by_source:
                writer.writerow([
                    source_data['source'],
                    source_data['count'],
                    f"{source_data['avg_sentiment']:.3f}" if source_data['avg_sentiment'] else 'N/A'
                ])
            writer.writerow([])
            
            # Write trending keywords
            writer.writerow(['=== TRENDING KEYWORDS ==='])
            writer.writerow(['Keyword', 'Frequency'])
            
            for keyword_data in trending_keywords:
                writer.writerow([keyword_data['keyword'], keyword_data['frequency']])
            
            return output.getvalue()
            
        except Exception as e:
            self.logger.error(f"Error exporting analytics: {e}")
            raise
    
    def export_trending_topics(self, hours_back: int = 24) -> str:
        """
        Export trending topics analysis to CSV
        
        Args:
            hours_back: Hours to look back for trending analysis
            
        Returns:
            CSV content as string
        """
        try:
            trending_topics = self.trending_analyzer.get_trending_topics(
                hours_back=hours_back,
                min_articles=2,
                max_topics=50
            )
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            writer.writerow([
                'keyword', 'frequency', 'articles_count', 'avg_sentiment', 'sentiment_label',
                'trend_score', 'sample_article_1', 'sample_article_2', 'sample_article_3'
            ])
            
            # Write trending topics data
            for topic in trending_topics:
                sample_titles = [
                    article.get('title', '')[:100] + ('...' if len(article.get('title', '')) > 100 else '')
                    for article in topic.recent_articles[:3]
                ]
                
                # Pad with empty strings if less than 3 articles
                while len(sample_titles) < 3:
                    sample_titles.append('')
                
                sentiment_label = self._sentiment_score_to_label(topic.avg_sentiment)
                
                writer.writerow([
                    topic.keyword,
                    topic.frequency,
                    topic.articles_count,
                    f"{topic.avg_sentiment:.3f}",
                    sentiment_label,
                    f"{topic.trend_score:.3f}",
                    sample_titles[0],
                    sample_titles[1],
                    sample_titles[2]
                ])
            
            return output.getvalue()
            
        except Exception as e:
            self.logger.error(f"Error exporting trending topics: {e}")
            raise
    
    def _get_filtered_articles(self, options: ExportOptions) -> List[Dict[str, Any]]:
        """Get articles based on filter options"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM articles"
            params = []
            where_clauses = []
            
            # Apply filters
            if options.date_from:
                where_clauses.append("scraped_date >= ?")
                params.append(options.date_from)
            
            if options.date_to:
                where_clauses.append("scraped_date <= ?")
                params.append(options.date_to)
            
            if options.source_filter:
                where_clauses.append("source = ?")
                params.append(options.source_filter)
            
            if options.sentiment_filter:
                where_clauses.append("sentiment_label = ?")
                params.append(options.sentiment_filter)
            
            # Build WHERE clause
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            # Add ordering
            query += " ORDER BY scraped_date DESC"
            
            # Add limit
            if options.max_records:
                query += " LIMIT ?"
                params.append(options.max_records)
            
            cursor.execute(query, params)
            
            # Convert to list of dictionaries
            articles = []
            for row in cursor.fetchall():
                articles.append({
                    'id': row['id'],
                    'title': row['title'],
                    'content': row['content'],
                    'summary': row['summary'],
                    'url': row['url'],
                    'source': row['source'],
                    'published_date': row['published_date'],
                    'scraped_date': row['scraped_date'],
                    'sentiment_score': row['sentiment_score'],
                    'sentiment_label': row['sentiment_label'],
                    'category': row['category'],
                    'keywords': row['keywords'],
                    'author': row['author']
                })
            
            return articles
    
    def _get_articles_by_source(self, cutoff_date: datetime) -> List[Dict[str, Any]]:
        """Get article statistics by source"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    source, 
                    COUNT(*) as count,
                    AVG(sentiment_score) as avg_sentiment
                FROM articles 
                WHERE scraped_date >= ?
                GROUP BY source 
                ORDER BY count DESC
            ''', (cutoff_date,))
            
            return [
                {
                    'source': row['source'],
                    'count': row['count'],
                    'avg_sentiment': row['avg_sentiment']
                }
                for row in cursor.fetchall()
            ]
    
    def _format_datetime(self, dt_str: Optional[str]) -> str:
        """Format datetime string for CSV"""
        if not dt_str:
            return ''
        
        try:
            dt = datetime.fromisoformat(dt_str)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return str(dt_str) if dt_str else ''
    
    def _sentiment_score_to_label(self, score: float) -> str:
        """Convert sentiment score to readable label"""
        if score > 0.1:
            return 'Positive'
        elif score < -0.1:
            return 'Negative'
        else:
            return 'Neutral'
    
    def _create_empty_csv(self, headers: List[str]) -> str:
        """Create empty CSV with headers"""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerow(['No data available for the specified criteria'])
        return output.getvalue()
    
    def get_export_stats(self) -> Dict[str, Any]:
        """Get statistics about available data for export"""
        try:
            total_articles = self.db_manager.get_article_count()
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get date range
                cursor.execute('SELECT MIN(scraped_date), MAX(scraped_date) FROM articles')
                date_range = cursor.fetchone()
                
                # Get sources
                cursor.execute('SELECT DISTINCT source FROM articles')
                sources = [row['source'] for row in cursor.fetchall()]
                
                # Get recent activity (last 7 days)
                week_ago = datetime.now() - timedelta(days=7)
                cursor.execute('SELECT COUNT(*) FROM articles WHERE scraped_date >= ?', (week_ago,))
                recent_articles = cursor.fetchone()[0]
            
            return {
                'total_articles': total_articles,
                'sources': sources,
                'date_range': {
                    'earliest': date_range[0] if date_range[0] else None,
                    'latest': date_range[1] if date_range[1] else None
                },
                'recent_articles_7_days': recent_articles
            }
            
        except Exception as e:
            self.logger.error(f"Error getting export stats: {e}")
            return {
                'total_articles': 0,
                'sources': [],
                'date_range': {'earliest': None, 'latest': None},
                'recent_articles_7_days': 0
            }