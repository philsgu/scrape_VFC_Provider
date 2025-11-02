import requests
import re
import json
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse

class VFCProviderScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.base_url = "https://eziz.org"
        self.providers = []

    def get_provider_locations_page(self):
        """Get the main provider locations page and analyze its structure"""
        url = "https://eziz.org/vfc/provider-locations/"
        print(f"Fetching: {url}")
        
        response = self.session.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch page: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup

    def find_search_form(self, soup):
        """Look for search forms or API endpoints"""
        print("\n=== Analyzing page structure ===")
        
        # Look for forms
        forms = soup.find_all('form')
        print(f"Found {len(forms)} forms")
        
        for i, form in enumerate(forms):
            print(f"\nForm {i+1}:")
            print(f"  Action: {form.get('action', 'No action')}")
            print(f"  Method: {form.get('method', 'GET')}")
            
            inputs = form.find_all(['input', 'select', 'textarea'])
            for inp in inputs:
                print(f"  Input: {inp.get('name', 'unnamed')} ({inp.get('type', inp.name)})")
        
        # Look for JavaScript that might handle provider search
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and any(keyword in script.string.lower() for keyword in ['provider', 'search', 'api', 'ajax', 'fetch']):
                print(f"\n=== Relevant JavaScript found ===")
                print(script.string[:500] + "..." if len(script.string) > 500 else script.string)

    def search_for_api_endpoints(self, soup):
        """Look for AJAX endpoints or API calls in the JavaScript"""
        scripts = soup.find_all('script')
        api_patterns = [
            r'url\s*:\s*[\'"]([^\'"]+)[\'"]',
            r'fetch\s*\(\s*[\'"]([^\'"]+)[\'"]',
            r'ajax\s*\(\s*[\'"]([^\'"]+)[\'"]',
            r'get\s*\(\s*[\'"]([^\'"]+)[\'"]',
            r'post\s*\(\s*[\'"]([^\'"]+)[\'"]'
        ]
        
        endpoints = set()
        for script in scripts:
            if script.string:
                for pattern in api_patterns:
                    matches = re.findall(pattern, script.string, re.IGNORECASE)
                    for match in matches:
                        if 'provider' in match.lower() or 'search' in match.lower():
                            endpoints.add(match)
        
        return list(endpoints)

    def try_common_api_endpoints(self):
        """Try common API endpoint patterns for provider data"""
        common_endpoints = [
            "/api/providers",
            "/api/vfc/providers", 
            "/vfc/api/providers",
            "/providers.json",
            "/data/providers.json",
            "/vfc/providers.json"
        ]
        
        print("\n=== Trying common API endpoints ===")
        for endpoint in common_endpoints:
            full_url = urljoin(self.base_url, endpoint)
            try:
                response = self.session.get(full_url, timeout=10)
                if response.status_code == 200:
                    print(f"✓ Found endpoint: {full_url}")
                    try:
                        data = response.json()
                        print(f"  JSON data with {len(data)} items" if isinstance(data, list) else f"  JSON object with {len(data)} keys" if isinstance(data, dict) else "  Valid JSON response")
                        return full_url, data
                    except:
                        print(f"  Response is not JSON: {response.text[:100]}")
                else:
                    print(f"✗ {endpoint}: {response.status_code}")
            except Exception as e:
                print(f"✗ {endpoint}: {str(e)}")
        
        return None, None

    def scrape_providers(self):
        """Main method to scrape VFC providers"""
        print("Starting VFC Provider Scraper...")
        
        # Get the main page
        soup = self.get_provider_locations_page()
        if not soup:
            return
        
        # Analyze the page structure
        self.find_search_form(soup)
        
        # Look for API endpoints
        endpoints = self.search_for_api_endpoints(soup)
        if endpoints:
            print(f"\n=== Found potential API endpoints ===")
            for endpoint in endpoints:
                print(f"  {endpoint}")
        
        # Try common API patterns
        api_url, data = self.try_common_api_endpoints()
        
        if data:
            self.providers = data if isinstance(data, list) else [data]
            print(f"\n✓ Successfully found {len(self.providers)} providers!")
            return self.providers
        
        # If no API found, try to extract from HTML
        print("\n=== Searching for embedded data in HTML ===")
        return self.extract_from_html(soup)

    def extract_from_html(self, soup):
        """Try to extract provider data from HTML"""
        # Look for data in script tags
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Try to find JSON data
                json_patterns = [
                    r'var\s+\w+\s*=\s*(\[.*?\]);',
                    r'const\s+\w+\s*=\s*(\[.*?\]);',
                    r'let\s+\w+\s*=\s*(\[.*?\]);',
                    r'=\s*(\[.*?\]);'
                ]
                
                for pattern in json_patterns:
                    matches = re.findall(pattern, script.string, re.DOTALL)
                    for match in matches:
                        try:
                            data = json.loads(match)
                            if isinstance(data, list) and len(data) > 0:
                                print(f"Found JSON array with {len(data)} items")
                                self.providers.extend(data)
                        except:
                            continue
        
        # Look for structured data in HTML
        provider_containers = soup.find_all(['div', 'section', 'article'], 
                                          class_=re.compile(r'provider|location|clinic', re.I))
        
        for container in provider_containers:
            provider_info = {}
            
            # Try to extract name
            name_elem = container.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b'])
            if name_elem:
                provider_info['name'] = name_elem.get_text(strip=True)
            
            # Try to extract address
            address_elem = container.find(text=re.compile(r'\d+.*\w+.*,.*\w+'))
            if address_elem:
                provider_info['address'] = address_elem.strip()
            
            # Try to extract phone
            phone_elem = container.find(text=re.compile(r'\(\d{3}\)\s*\d{3}-\d{4}'))
            if phone_elem:
                provider_info['phone'] = phone_elem.strip()
            
            if provider_info:
                self.providers.append(provider_info)
        
        return self.providers

    def save_results(self):
        """Save the scraped provider data"""
        if self.providers:
            filename = 'vfc_providers.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.providers, f, indent=2, ensure_ascii=False)
            print(f"\n✓ Saved {len(self.providers)} providers to {filename}")
            
            # Also save a summary
            summary_filename = 'vfc_providers_summary.txt'
            with open(summary_filename, 'w', encoding='utf-8') as f:
                f.write(f"VFC Provider Scraping Results\n")
                f.write(f"============================\n\n")
                f.write(f"Total providers found: {len(self.providers)}\n\n")
                
                for i, provider in enumerate(self.providers[:10], 1):
                    f.write(f"{i}. {provider}\n\n")
                
                if len(self.providers) > 10:
                    f.write(f"... and {len(self.providers) - 10} more providers\n")
            
            print(f"✓ Saved summary to {summary_filename}")
        else:
            print("No providers found to save.")

# Run the scraper
if __name__ == "__main__":
    scraper = VFCProviderScraper()
    providers = scraper.scrape_providers()
    scraper.save_results()
    
    print(f"\n=== Final Results ===")
    print(f"Total providers found: {len(providers) if providers else 0}")
    
    if providers:
        print("\nFirst few providers:")
        for i, provider in enumerate(providers[:3], 1):
            print(f"{i}. {provider}")
    else:
        print("\nThe VFC provider search appears to be form-based.")
        print("You may need to:")
        print("1. Check if there's a search form that requires specific parameters")
        print("2. Look for AJAX endpoints that load provider data dynamically")
        print("3. Consider using browser automation (Selenium) if JavaScript is required")
