import requests
from bs4 import BeautifulSoup

def debug_selectors(url, name, selectors):
    print(f"\n=== Debugging {name} ===")
    print(f"URL: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        print(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Failed to fetch {name}")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Test article links selector
        article_selector = selectors.get('article_links', 'a')
        print(f"Testing selector: {article_selector}")
        
        elements = soup.select(article_selector)
        print(f"Found {len(elements)} elements")
        
        # Show first 5 matches
        for i, element in enumerate(elements[:5]):
            href = element.get('href')
            text = element.get_text(strip=True)[:100]
            print(f"  {i+1}. href='{href}' text='{text}...'")
        
        # Try alternative selectors if nothing found
        if len(elements) == 0:
            print("\n🔍 Trying alternative selectors:")
            alternatives = ['a[href*="/"]', 'h2 a', 'h3 a', '.headline a', '.title a', 'article a']
            
            for alt_selector in alternatives:
                alt_elements = soup.select(alt_selector)
                if len(alt_elements) > 0:
                    print(f"  {alt_selector}: {len(alt_elements)} elements")
                    for j, elem in enumerate(alt_elements[:3]):
                        href = elem.get('href')
                        text = elem.get_text(strip=True)[:50]
                        print(f"    {j+1}. {href} - {text}")
                else:
                    print(f"  {alt_selector}: 0 elements")
    
    except Exception as e:
        print(f" Error debugging {name}: {e}")

def main():
    sources = [
        {
            'name': 'WebMD',
            'url': 'https://www.webmd.com/news',
            'selectors': {'article_links': "h2 a, h3 a"}
        },
        {
            'name': 'Healthline',
            'url': 'https://www.healthline.com/health-news',
            'selectors': {'article_links': "h2 a, h3 a"}
        },
        {
            'name': 'Mayo Clinic News',
            'url': 'https://newsnetwork.mayoclinic.org/',
            'selectors': {'article_links': "h2 a, h3 a"}
        }
    ]
    
    for source in sources:
        debug_selectors(source['url'], source['name'], source['selectors'])

if __name__ == "__main__":
    main()