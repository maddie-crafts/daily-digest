import sys
sys.path.append('src')

from src.utils.config import get_config
from src.scraper.base_scraper import BaseScraper
import logging

logging.basicConfig(level=logging.INFO)

def test_scrapers():
    config = get_config()
    scraping_config = config.get_scraping_config()
    
    print("Testing scrapers...")
    
    for source_config in config.get_sources():
        source_name = source_config['name']
        print(f"\n--- Testing {source_name} ---")
        
        try:
            # Create scraper directly using BaseScraper
            scraper = BaseScraper(source_config, scraping_config)
            articles = scraper.fetch_articles()
            
            print(f"{source_name}: Found {len(articles)} articles")
            
            if articles:
                article = articles[0]
                print(f"Sample article: {article.title[:100]}...")
                print(f"Content length: {len(article.content)} chars")
                print(f"URL: {article.url}")
            else:
                print(f"No articles found for {source_name}")
            
        except Exception as e:
            print(f"{source_name}: Error - {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_scrapers()