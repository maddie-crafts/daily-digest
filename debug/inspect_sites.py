import requests
from bs4 import BeautifulSoup

def inspect_site(url, name):
    print(f"\n=== Inspecting {name} ===")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for article-like links
        for selector in ['article h2 a', 'article h3 a', '.story-headline a', '.entry-title a', 
                        'h1 a', 'h2 a', 'h3 a', 'h4 a', '.post-title a', '.headline a']:
            elements = soup.select(selector)
            if len(elements) > 0:
                print(f"{selector}: {len(elements)} elements")
                # Show a few examples
                for i, elem in enumerate(elements[:3]):
                    href = elem.get('href', 'No href')
                    text = elem.get_text(strip=True)[:60]
                    print(f"   {i+1}. {href} - {text}")
                if len(elements) >= 5:  # Good selector
                    break
    except Exception as e:
        print(f"Error: {e}")

def main():
    sites = [
        ("https://www.healthline.com", "Healthline"),
        ("https://techcrunch.com/", "TechCrunch"),
    ]
    
    for url, name in sites:
        inspect_site(url, name)

if __name__ == "__main__":
    main()