from typing import List, Dict, Any
from .base_scraper import BaseScraper
from ..storage.models import Article

class NewsSourceManager:
    def __init__(self, scraping_config: Dict[str, Any]):
        self.scraping_config = scraping_config
        self.scrapers = {}
    
    def add_source(self, source_config: Dict[str, Any]):
        source_name = source_config.get('name')
        if source_name:
            scraper = BaseScraper(source_config, self.scraping_config)
            self.scrapers[source_name] = scraper
    
    def scrape_source(self, source_name: str) -> List[Article]:
        if source_name in self.scrapers:
            return self.scrapers[source_name].fetch_articles()
        return []
    
    def scrape_all_sources(self) -> Dict[str, List[Article]]:
        results = {}
        for source_name, scraper in self.scrapers.items():
            try:
                articles = scraper.fetch_articles()
                results[source_name] = articles
            except Exception as e:
                print(f"Error scraping {source_name}: {e}")
                results[source_name] = []
        return results
    
    def get_source_names(self) -> List[str]:
        return list(self.scrapers.keys())