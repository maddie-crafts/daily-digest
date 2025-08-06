import requests
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, urlparse
import re

from ..storage.models import Article

class BaseScraper:
    def __init__(self, source_config: Dict[str, Any], scraping_config: Dict[str, Any]):
        self.source_config = source_config
        self.scraping_config = scraping_config
        self.source_name = source_config.get('name', 'Unknown')
        self.base_url = source_config.get('base_url', '')
        self.selectors = source_config.get('selectors', {})
        self.rate_limit = source_config.get('rate_limit', 2)
        self.max_articles = source_config.get('max_articles', 20)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': scraping_config.get('user_agent', 'NewsAggregator/1.0'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        self.timeout = scraping_config.get('timeout', 10)
        self.retry_attempts = scraping_config.get('retry_attempts', 3)
        self.min_content_length = scraping_config.get('min_content_length', 100)
        
        self.logger = logging.getLogger(f'scraper.{self.source_name}')
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        for attempt in range(self.retry_attempts):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                return soup
                
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(2 ** attempt)
                else:
                    self.logger.error(f"Failed to fetch {url} after {self.retry_attempts} attempts")
        
        return None
    
    def extract_article_links(self, soup: BeautifulSoup) -> List[str]:
        links = []
        link_selector = self.selectors.get('article_links', 'a')
        
        try:
            elements = soup.select(link_selector)
            for element in elements[:self.max_articles]:
                href = element.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    if self._is_valid_article_url(full_url):
                        links.append(full_url)
        except Exception as e:
            self.logger.error(f"Error extracting article links: {e}")
        
        return list(set(links))
    
    def _is_valid_article_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Skip external links for news aggregators like HN
            base_domain = urlparse(self.base_url).netloc.lower()
            url_domain = parsed.netloc.lower()
            
            # For sites that have consistent domains - only allow same-domain links
            allowed_domains = [
                'www.bbc.com', 'www.theguardian.com', 'www.npr.org', 'apnews.com',
                'www.sciencedaily.com', 'www.livescience.com',
                'techcrunch.com', 'arstechnica.com', 'www.engadget.com'
            ]
            if base_domain in allowed_domains:
                if url_domain != base_domain:
                    return False
            
            invalid_patterns = [
                r'/video/', r'/gallery/', r'/live/', r'/sport/', r'/podcast/',
                r'#', r'javascript:', r'mailto:', r'tel:', r'/tag/', r'/author/',
                r'/category/', r'/search/', r'/subscribe', r'/newsletter'
            ]
            
            for pattern in invalid_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return False
            
            return True
        except Exception:
            return False
    
    def extract_article_content(self, url: str) -> Optional[Article]:
        soup = self.fetch_page(url)
        if not soup:
            return None
        
        try:
            article = Article()
            article.url = url
            article.source = self.source_name
            article.scraped_date = datetime.now()
            
            article.title = self._extract_title(soup)
            article.content = self._extract_content(soup)
            article.published_date = self._extract_date(soup)
            article.author = self._extract_author(soup)
            
            if not article.title or not article.content:
                self.logger.warning(f"Missing title or content for {url}")
                return None
            
            if len(article.content) < self.min_content_length:
                self.logger.warning(f"Content too short for {url}: {len(article.content)} chars")
                return None
            
            return article
            
        except Exception as e:
            self.logger.error(f"Error extracting content from {url}: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        title_selector = self.selectors.get('title', 'h1')
        try:
            title_element = soup.select_one(title_selector)
            if title_element:
                return title_element.get_text(strip=True)
            
            title_tag = soup.find('title')
            if title_tag:
                return title_tag.get_text(strip=True)
        except Exception as e:
            self.logger.warning(f"Error extracting title: {e}")
        
        return ""
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        content_selector = self.selectors.get('content', 'p')
        content_parts = []
        
        try:
            elements = soup.select(content_selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 20:
                    content_parts.append(text)
            
            if not content_parts:
                paragraphs = soup.find_all('p')
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        content_parts.append(text)
        except Exception as e:
            self.logger.warning(f"Error extracting content: {e}")
        
        content = ' '.join(content_parts)
        return self._clean_content(content)
    
    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        date_selector = self.selectors.get('date', 'time')
        
        try:
            date_element = soup.select_one(date_selector)
            if date_element:
                datetime_attr = date_element.get('datetime')
                if datetime_attr:
                    return self._parse_date(datetime_attr)
                
                date_text = date_element.get_text(strip=True)
                if date_text:
                    return self._parse_date(date_text)
        except Exception as e:
            self.logger.warning(f"Error extracting date: {e}")
        
        return None
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        author_selectors = [
            '.author', '.byline', '[rel="author"]',
            '.article-author', '.post-author'
        ]
        
        try:
            for selector in author_selectors:
                author_element = soup.select_one(selector)
                if author_element:
                    return author_element.get_text(strip=True)
        except Exception as e:
            self.logger.warning(f"Error extracting author: {e}")
        
        return ""
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        date_formats = [
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d %B %Y',
            '%B %d, %Y',
        ]
        
        date_str = re.sub(r'[^\w\s:+-]', ' ', date_str).strip()
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def _clean_content(self, content: str) -> str:
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'^\s*Advertisement\s*', '', content, flags=re.IGNORECASE)
        content = re.sub(r'^\s*Share this.*?\s*', '', content, flags=re.IGNORECASE)
        content = content.strip()
        return content
    
    def fetch_articles(self) -> List[Article]:
        self.logger.info(f"Starting to fetch articles from {self.source_name}")
        
        soup = self.fetch_page(self.base_url)
        if not soup:
            self.logger.error(f"Failed to fetch main page for {self.source_name}")
            return []
        
        article_links = self.extract_article_links(soup)
        self.logger.info(f"Found {len(article_links)} article links")
        
        articles = []
        for i, link in enumerate(article_links):
            if i > 0:
                time.sleep(self.rate_limit)
            
            article = self.extract_article_content(link)
            if article:
                articles.append(article)
                self.logger.debug(f"Successfully extracted article: {article.title[:50]}...")
            else:
                self.logger.warning(f"Failed to extract article from {link}")
        
        self.logger.info(f"Successfully extracted {len(articles)} articles from {self.source_name}")
        return articles