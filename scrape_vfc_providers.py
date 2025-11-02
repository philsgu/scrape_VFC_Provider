import requests
import xml.etree.ElementTree as ET
import json
from typing import Set, Dict, List

# The actual endpoint for provider data
BASE_URL = "https://eziz.org/iframes/genxml.php"

# California coordinates to cover the state
# Using major cities/regions to ensure we get all providers
CALIFORNIA_LOCATIONS = [
    (37.4419, -121.5419),   # San Jose (center)
    (34.0522, -118.2437),   # Los Angeles
    (32.7157, -117.1611),   # San Diego
    (38.5816, -121.4944),   # Sacramento
    (37.7749, -122.4194),   # San Francisco
    (36.1699, -115.1398),   # Las Vegas area (border)
    (35.3733, -119.0187),   # Bakersfield
    (38.5407, -121.7584),   # Davis
    (36.9750, -122.0306),   # Santa Cruz
    (33.9533, -117.3962),   # Riverside
    (34.0689, -118.4452),   # Beverly Hills
    (37.3382, -121.8863),   # Santa Clara
    (40.5865, -122.3917),   # Redding
    (35.2828, -120.6596),   # San Luis Obispo
    (36.7372, -119.7871),   # Fresno
    (33.6846, -117.8265),   # Orange County
]

def fetch_providers(lat: float, lng: float, radius: int = 500) -> List[Dict]:
    """Fetch providers for a given location and radius."""
    params = {
        'lat': lat,
        'lng': lng,
        'radius': radius
    }
    
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        providers = []
        
        for marker in root.findall('marker'):
            provider = {
                'name': marker.get('name', ''),
                'address': marker.get('address', ''),
                'phone': marker.get('phone', ''),
                'type': marker.get('type', ''),
                'lat': float(marker.get('lat', 0)),
                'lng': float(marker.get('lng', 0)),
                'distance': float(marker.get('distance', 0))
            }
            providers.append(provider)
        
        return providers
    except Exception as e:
        print(f"Error fetching providers for {lat},{lng}: {e}")
        return []

def get_all_providers() -> List[Dict]:
    """Fetch all providers by querying multiple locations."""
    all_providers = {}
    
    # Use name+address as unique key to avoid duplicates
    for lat, lng in CALIFORNIA_LOCATIONS:
        print(f"Fetching providers near {lat}, {lng}...")
        providers = fetch_providers(lat, lng, radius=500)
        
        for provider in providers:
            # Create unique key from name and address
            key = f"{provider['name']}|{provider['address']}"
            if key not in all_providers:
                all_providers[key] = provider
        
        print(f"  Found {len(providers)} providers (total unique: {len(all_providers)})")
    
    # Also try with a very large radius from the center of California
    print("\nFetching with large radius from state center...")
    center_providers = fetch_providers(36.7783, -119.4179, radius=1000)  # Center of CA
    for provider in center_providers:
        key = f"{provider['name']}|{provider['address']}"
        if key not in all_providers:
            all_providers[key] = provider
    
    return list(all_providers.values())

if __name__ == "__main__":
    print("Starting VFC provider scraping...")
    print("=" * 60)
    
    providers = get_all_providers()
    
    print("\n" + "=" * 60)
    print(f"Total unique providers found: {len(providers)}")
    
    # Save to JSON
    output_file = 'vfc_providers.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(providers, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved {len(providers)} providers to {output_file}")
    
    # Print sample
    if providers:
        print("\nSample providers:")
        for i, provider in enumerate(providers[:5]):
            print(f"\n{i+1}. {provider['name']}")
            print(f"   Address: {provider['address']}")
            print(f"   Phone: {provider['phone']}")
            print(f"   Type: {provider['type']}")

