from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Article:
    id: Optional[int] = None
    title: str = ""
    content: str = ""
    summary: str = ""
    url: str = ""
    source: str = ""
    published_date: Optional[datetime] = None
    scraped_date: Optional[datetime] = None
    sentiment_score: Optional[float] = None
    sentiment_label: str = ""
    category: str = ""
    keywords: str = ""
    author: str = ""

@dataclass
class Source:
    id: Optional[int] = None
    name: str = ""
    base_url: str = ""
    scraping_config: str = ""
    last_scraped: Optional[datetime] = None
    is_active: bool = True
    success_count: int = 0
    error_count: int = 0