import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from .models import Article, Source

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    base_url TEXT NOT NULL,
                    scraping_config TEXT,
                    last_scraped TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    success_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT,
                    url TEXT UNIQUE NOT NULL,
                    source TEXT NOT NULL,
                    published_date TIMESTAMP,
                    scraped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sentiment_score REAL,
                    sentiment_label TEXT,
                    category TEXT,
                    keywords TEXT,
                    author TEXT,
                    FOREIGN KEY (source) REFERENCES sources (name)
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_scraped ON articles(scraped_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)')
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def add_source(self, source: Source) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO sources 
                (name, base_url, scraping_config, is_active)
                VALUES (?, ?, ?, ?)
            ''', (source.name, source.base_url, source.scraping_config, source.is_active))
            conn.commit()
            return cursor.lastrowid
    
    def get_sources(self, active_only: bool = True) -> List[Source]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM sources"
            if active_only:
                query += " WHERE is_active = TRUE"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            return [Source(
                id=row['id'],
                name=row['name'],
                base_url=row['base_url'],
                scraping_config=row['scraping_config'],
                last_scraped=datetime.fromisoformat(row['last_scraped']) if row['last_scraped'] else None,
                is_active=bool(row['is_active']),
                success_count=row['success_count'],
                error_count=row['error_count']
            ) for row in rows]
    
    def update_source_stats(self, source_name: str, success: bool):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if success:
                cursor.execute('''
                    UPDATE sources 
                    SET success_count = success_count + 1, last_scraped = ?
                    WHERE name = ?
                ''', (datetime.now(), source_name))
            else:
                cursor.execute('''
                    UPDATE sources 
                    SET error_count = error_count + 1
                    WHERE name = ?
                ''', (source_name,))
            conn.commit()
    
    def add_article(self, article: Article) -> Optional[int]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO articles 
                    (title, content, summary, url, source, published_date, 
                     sentiment_score, sentiment_label, category, keywords, author)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    article.title, article.content, article.summary, article.url,
                    article.source, article.published_date, article.sentiment_score,
                    article.sentiment_label, article.category, article.keywords, article.author
                ))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
    
    def get_articles(self, limit: int = 50, offset: int = 0, source: Optional[str] = None) -> List[Article]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM articles"
            params = []
            
            if source:
                query += " WHERE source = ?"
                params.append(source)
            
            query += " ORDER BY scraped_date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [Article(
                id=row['id'],
                title=row['title'],
                content=row['content'],
                summary=row['summary'],
                url=row['url'],
                source=row['source'],
                published_date=datetime.fromisoformat(row['published_date']) if row['published_date'] else None,
                scraped_date=datetime.fromisoformat(row['scraped_date']) if row['scraped_date'] else None,
                sentiment_score=row['sentiment_score'],
                sentiment_label=row['sentiment_label'],
                category=row['category'],
                keywords=row['keywords'],
                author=row['author']
            ) for row in rows]
    
    def get_article_by_id(self, article_id: int) -> Optional[Article]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
            row = cursor.fetchone()
            
            if row:
                return Article(
                    id=row['id'],
                    title=row['title'],
                    content=row['content'],
                    summary=row['summary'],
                    url=row['url'],
                    source=row['source'],
                    published_date=datetime.fromisoformat(row['published_date']) if row['published_date'] else None,
                    scraped_date=datetime.fromisoformat(row['scraped_date']) if row['scraped_date'] else None,
                    sentiment_score=row['sentiment_score'],
                    sentiment_label=row['sentiment_label'],
                    category=row['category'],
                    keywords=row['keywords'],
                    author=row['author']
                )
            return None
    
    def search_articles(self, query: str, limit: int = 50) -> List[Article]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            search_query = f"%{query}%"
            cursor.execute('''
                SELECT * FROM articles 
                WHERE title LIKE ? OR content LIKE ? OR keywords LIKE ?
                ORDER BY scraped_date DESC LIMIT ?
            ''', (search_query, search_query, search_query, limit))
            
            rows = cursor.fetchall()
            return [Article(
                id=row['id'],
                title=row['title'],
                content=row['content'],
                summary=row['summary'],
                url=row['url'],
                source=row['source'],
                published_date=datetime.fromisoformat(row['published_date']) if row['published_date'] else None,
                scraped_date=datetime.fromisoformat(row['scraped_date']) if row['scraped_date'] else None,
                sentiment_score=row['sentiment_score'],
                sentiment_label=row['sentiment_label'],
                category=row['category'],
                keywords=row['keywords'],
                author=row['author']
            ) for row in rows]
    
    def cleanup_old_articles(self, retention_days: int):
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM articles WHERE scraped_date < ?', (cutoff_date,))
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
    
    def get_article_count(self) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM articles')
            return cursor.fetchone()[0]
    
    def get_sentiment_distribution(self) -> Dict[str, int]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT sentiment_label, COUNT(*) as count 
                FROM articles 
                WHERE sentiment_label IS NOT NULL 
                GROUP BY sentiment_label
            ''')
            return dict(cursor.fetchall())
    
    def get_trending_keywords(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT keywords, COUNT(*) as frequency
                FROM articles 
                WHERE keywords IS NOT NULL AND keywords != ''
                AND scraped_date >= datetime('now', '-7 days')
                GROUP BY keywords
                ORDER BY frequency DESC
                LIMIT ?
            ''', (limit,))
            return [{'keyword': row[0], 'frequency': row[1]} for row in cursor.fetchall()]