#!/usr/bin/env python3
"""
CLI tool to extract VFC providers by California county
"""
import requests
import xml.etree.ElementTree as ET
import json
import sys
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

# The actual endpoint for provider data
BASE_URL = "https://eziz.org/iframes/genxml.php"

# California counties with their approximate coordinates (county seat or major city)
CALIFORNIA_COUNTIES = {
    "Alameda": (37.8044, -122.2712),  # Oakland
    "Alpine": (38.5961, -119.8104),    # Markleeville
    "Amador": (38.3485, -120.7705),    # Jackson
    "Butte": (39.7285, -121.8375),     # Oroville
    "Calaveras": (38.2039, -120.6803), # San Andreas
    "Colusa": (39.2138, -122.0084),    # Colusa
    "Contra Costa": (37.9358, -122.3477), # Martinez
    "Del Norte": (41.7557, -124.2025), # Crescent City
    "El Dorado": (38.6778, -121.1750), # Placerville
    "Fresno": (36.7378, -119.7871),    # Fresno
    "Glenn": (39.5982, -122.3919),     # Willows
    "Humboldt": (40.8665, -124.0828),  # Eureka
    "Imperial": (32.8472, -115.5694),  # El Centro
    "Inyo": (36.5107, -117.0973),      # Independence
    "Kern": (35.3733, -119.0187),      # Bakersfield
    "Kings": (36.3275, -119.6457),     # Hanford
    "Lake": (39.0442, -122.9124),      # Lakeport
    "Lassen": (40.4163, -120.6530),    # Susanville
    "Los Angeles": (34.0522, -118.2437), # Los Angeles
    "Madera": (37.1553, -119.7663),    # Madera
    "Marin": (38.0834, -122.7633),     # San Rafael
    "Mariposa": (37.4849, -119.9663),  # Mariposa
    "Mendocino": (39.1501, -123.2078), # Ukiah
    "Merced": (37.3022, -120.4829),    # Merced
    "Modoc": (41.4479, -120.4677),     # Alturas
    "Mono": (37.9396, -119.0023),      # Bridgeport
    "Monterey": (36.6002, -121.8946),  # Salinas
    "Napa": (38.2975, -122.2869),      # Napa
    "Nevada": (39.2618, -121.0182),    # Nevada City
    "Orange": (33.7879, -117.8531),    # Santa Ana
    "Placer": (38.9544, -121.0972),    # Auburn
    "Plumas": (40.0390, -120.8415),    # Quincy
    "Riverside": (33.9533, -117.3962), # Riverside
    "Sacramento": (38.5816, -121.4944), # Sacramento
    "San Benito": (36.8527, -121.4014), # Hollister
    "San Bernardino": (34.1083, -117.2898), # San Bernardino
    "San Diego": (32.7157, -117.1611), # San Diego
    "San Francisco": (37.7749, -122.4194), # San Francisco
    "San Joaquin": (37.9537, -121.2908), # Stockton
    "San Luis Obispo": (35.2828, -120.6596), # San Luis Obispo
    "San Mateo": (37.5629, -122.3255), # Redwood City
    "Santa Barbara": (34.4208, -119.6982), # Santa Barbara
    "Santa Clara": (37.3541, -121.9552), # San Jose
    "Santa Cruz": (36.9741, -122.0308), # Santa Cruz
    "Shasta": (40.5865, -122.3917),    # Redding
    "Sierra": (39.6240, -120.5170),    # Downieville
    "Siskiyou": (41.7375, -122.6344),  # Yreka
    "Solano": (38.2494, -122.0409),    # Fairfield
    "Sonoma": (38.2919, -122.4580),    # Santa Rosa
    "Stanislaus": (37.6387, -120.9967), # Modesto
    "Sutter": (39.1404, -121.6199),    # Yuba City
    "Tehama": (40.1785, -122.2358),    # Red Bluff
    "Trinity": (40.7381, -123.0203),   # Weaverville
    "Tulare": (36.2077, -119.3471),    # Visalia
    "Tuolumne": (37.9847, -120.3821),  # Sonora
    "Ventura": (34.2746, -119.2290),   # Ventura
    "Yolo": (38.5419, -121.7398),      # Woodland
    "Yuba": (39.1404, -121.6199),      # Marysville
}

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
        
        # Strip PHP warnings that appear before XML (common with this API)
        content = response.text
        # Find the XML start (<?xml)
        xml_start = content.find('<?xml')
        if xml_start > 0:
            content = content[xml_start:]
        
        # Use BeautifulSoup which is more forgiving with malformed XML
        # First, extract all marker tags using regex if XML is malformed
        providers = []
        
        # Try standard XML parsing first
        try:
            root = ET.fromstring(content.encode('utf-8', errors='replace'))
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
        except ET.ParseError:
            # If XML parsing fails, use regex to extract marker data
            # Pattern to match marker tags with all attributes
            marker_pattern = r'<marker\s+([^>]+)/>'
            matches = re.findall(marker_pattern, content)
            
            for match in matches:
                # Extract attributes using regex
                attrs = {}
                # Match name="value" or name='value'
                attr_pattern = r'(\w+)="([^"]*)"'
                attr_matches = re.findall(attr_pattern, match)
                for attr_name, attr_value in attr_matches:
                    attrs[attr_name] = attr_value
                
                # Also try single quotes
                if len(attrs) < 5:  # Not enough attributes found
                    attr_pattern_sq = r"(\w+)='([^']*)'"
                    attr_matches_sq = re.findall(attr_pattern_sq, match)
                    for attr_name, attr_value in attr_matches_sq:
                        attrs[attr_name] = attr_value
                
                if attrs:
                    try:
                        provider = {
                            'name': attrs.get('name', ''),
                            'address': attrs.get('address', ''),
                            'phone': attrs.get('phone', ''),
                            'type': attrs.get('type', ''),
                            'lat': float(attrs.get('lat', 0)),
                            'lng': float(attrs.get('lng', 0)),
                            'distance': float(attrs.get('distance', 0))
                        }
                        providers.append(provider)
                    except (ValueError, KeyError):
                        continue
        
        return providers
    except Exception as e:
        print(f"Error fetching providers: {e}", file=sys.stderr)
        return []

def filter_by_county(providers: List[Dict], county_name: str) -> List[Dict]:
    """Filter providers by county name/city in address.
    
    Since addresses usually contain city names (e.g., "Fresno, CA" not "Fresno County, CA"),
    we match against the county seat or major city names.
    """
    # Map county names to their primary city names that appear in addresses
    county_to_cities = {
        "Alameda": ["Alameda", "Oakland", "Berkeley", "Fremont"],
        "Contra Costa": ["Contra Costa", "Martinez", "Richmond", "Concord", "Pleasant Hill"],
        "Fresno": ["Fresno", "Clovis", "Sanger"],
        "Kern": ["Kern", "Bakersfield"],
        "Los Angeles": ["Los Angeles", "LA", "L.A.", "Beverly Hills", "Long Beach", "Pasadena"],
        "Orange": ["Orange", "Santa Ana", "Anaheim", "Irvine", "Huntington Beach"],
        "Riverside": ["Riverside", "Palm Springs", "Moreno Valley", "Corona"],
        "Sacramento": ["Sacramento", "Folsom", "Elk Grove"],
        "San Bernardino": ["San Bernardino", "Fontana", "Rancho Cucamonga", "Ontario"],
        "San Diego": ["San Diego", "Chula Vista", "Oceanside"],
        "San Francisco": ["San Francisco", "SF"],
        "San Joaquin": ["San Joaquin", "Stockton", "Lodi", "Tracy"],
        "Santa Clara": ["Santa Clara", "San Jose", "Sunnyvale", "Palo Alto", "Cupertino", "Mountain View"],
        "Stanislaus": ["Stanislaus", "Modesto", "Turlock", "Ceres"],
    }
    
    # Get city keywords for this county
    county_keywords = [county_name]
    if county_name in county_to_cities:
        county_keywords.extend(county_to_cities[county_name])
    else:
        # For counties not in the map, use the county name and try to guess the city
        # (Most county seats share the county name)
        county_keywords.append(county_name.replace(" County", ""))
    
    filtered = []
    for provider in providers:
        address = provider.get('address', '').upper()
        # Check if any county/city keyword appears in the address
        if any(keyword.upper() in address for keyword in county_keywords):
            filtered.append(provider)
    
    return filtered

def display_counties():
    """Display numbered list of counties."""
    counties = sorted(CALIFORNIA_COUNTIES.keys())
    print("\nCalifornia Counties:")
    print("=" * 60)
    for i, county in enumerate(counties, 1):
        print(f"{i:2d}. {county}")
    print("=" * 60)

def get_county_selection() -> Optional[str]:
    """Get county selection from user."""
    counties = sorted(CALIFORNIA_COUNTIES.keys())
    
    while True:
        try:
            user_input = input("\nEnter county number or name (q to quit): ").strip()
            
            if user_input.lower() == 'q':
                return None
            
            # Try as number first
            if user_input.isdigit():
                num = int(user_input)
                if 1 <= num <= len(counties):
                    return counties[num - 1]
                else:
                    print(f"Please enter a number between 1 and {len(counties)}")
                    continue
            
            # Try as name (partial match allowed)
            matches = [c for c in counties if user_input.lower() in c.lower()]
            if len(matches) == 1:
                return matches[0]
            elif len(matches) > 1:
                print(f"Multiple matches found: {', '.join(matches)}")
                print("Please be more specific.")
                continue
            else:
                print(f"County '{user_input}' not found. Please try again.")
                continue
                
        except KeyboardInterrupt:
            print("\n\nExiting...")
            return None
        except Exception as e:
            print(f"Error: {e}")

def get_county_search_locations(county_name: str) -> List[tuple]:
    """Get multiple search locations for a county to ensure complete coverage.
    
    The API limits results to ~50 providers per request, so we search multiple
    locations within each county to get all providers.
    """
    if county_name not in CALIFORNIA_COUNTIES:
        return []
    
    base_lat, base_lng = CALIFORNIA_COUNTIES[county_name]
    
    # Create a grid of locations around the base location
    # This ensures we capture all providers even if they're spread out
    locations = [(base_lat, base_lng)]  # Center
    
    # Add points in a grid pattern
    offsets = [
        (0.05, 0),      # North
        (-0.05, 0),    # South
        (0, 0.05),     # East
        (0, -0.05),    # West
        (0.05, 0.05),  # Northeast
        (0.05, -0.05), # Northwest
        (-0.05, 0.05), # Southeast
        (-0.05, -0.05), # Southwest
    ]
    
    for lat_offset, lng_offset in offsets:
        locations.append((base_lat + lat_offset, base_lng + lng_offset))
    
    return locations

def extract_county_providers(county_name: str, radius: int = 100) -> List[Dict]:
    """Extract providers for a specific county by searching multiple locations.
    
    Since the API limits results to ~50 providers per request, we search
    multiple locations within the county to ensure we get all providers.
    """
    if county_name not in CALIFORNIA_COUNTIES:
        print(f"Error: County '{county_name}' not found in database.", file=sys.stderr)
        return []
    
    base_lat, base_lng = CALIFORNIA_COUNTIES[county_name]
    
    print(f"\nFetching providers for {county_name} County...")
    print(f"Base coordinates: {base_lat}, {base_lng}")
    print(f"Search radius: {radius} miles")
    print("\nSearching multiple locations to ensure complete coverage...")
    print("(The API limits results, so we search multiple points)\n")
    
    # Get multiple search locations
    search_locations = get_county_search_locations(county_name)
    
    # Collect all unique providers
    all_providers = {}
    total_fetched = 0
    
    for i, (lat, lng) in enumerate(search_locations, 1):
        print(f"  Location {i}/{len(search_locations)}: {lat:.4f}, {lng:.4f}...", end=' ', flush=True)
        providers = fetch_providers(lat, lng, radius=radius)
        total_fetched += len(providers)
        
        # Use name+address as unique key to avoid duplicates
        new_count = 0
        for provider in providers:
            key = f"{provider['name']}|{provider['address']}"
            if key not in all_providers:
                all_providers[key] = provider
                new_count += 1
        
        print(f"Found {len(providers)} (new: {new_count}, total unique: {len(all_providers)})")
        
        # If we got fewer than 50, we've likely reached the edges
        # Continue searching other locations but note this
        if len(providers) < 30:
            pass  # Still continue to other locations
    
    providers_list = list(all_providers.values())
    
    if not providers_list:
        print(f"\nNo providers found for {county_name} County.")
        return []
    
    print(f"\n✓ Found {len(providers_list)} unique providers from {total_fetched} total results")
    
    # Optional filtering by county name (but don't be too strict)
    if len(providers_list) > 0:
        filtered = filter_by_county(providers_list, county_name)
        if len(filtered) >= len(providers_list) * 0.5:
            print(f"  (Filtered to {len(filtered)} providers matching county keywords)")
            return filtered
        else:
            # Return all if filtering removes too many
            print(f"  (Keeping all {len(providers_list)} providers - geographic filtering is sufficient)")
            return providers_list
    
    return providers_list

def save_results(providers: List[Dict], county_name: str):
    """Save results to JSON file."""
    filename = f"vfc_providers_{county_name.replace(' ', '_').lower()}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(providers, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved {len(providers)} providers to {filename}")
    return filename

def print_summary(providers: List[Dict], county_name: str):
    """Print summary of results."""
    print(f"\n{'='*60}")
    print(f"Results for {county_name} County")
    print(f"{'='*60}")
    print(f"Total providers: {len(providers)}")
    
    if providers:
        # Group by type
        types = {}
        for provider in providers:
            ptype = provider.get('type', 'Unknown')
            types[ptype] = types.get(ptype, 0) + 1
        
        print(f"\nProviders by type:")
        for ptype, count in sorted(types.items()):
            print(f"  {ptype}: {count}")
        
        print(f"\nFirst 5 providers:")
        for i, provider in enumerate(providers[:5], 1):
            print(f"\n{i}. {provider['name']}")
            print(f"   Address: {provider['address']}")
            print(f"   Phone: {provider['phone']}")
            print(f"   Type: {provider['type']}")
        
        if len(providers) > 5:
            print(f"\n... and {len(providers) - 5} more providers")

def main():
    """Main CLI loop."""
    print("=" * 60)
    print("VFC Provider Extractor by County")
    print("=" * 60)
    
    while True:
        display_counties()
        county_name = get_county_selection()
        
        if not county_name:
            print("\nGoodbye!")
            break
        
        # Get radius if user wants to customize
        radius_input = input(f"\nEnter search radius in miles (default 100, press Enter for default): ").strip()
        radius = int(radius_input) if radius_input.isdigit() else 100
        
        # Extract providers
        providers = extract_county_providers(county_name, radius=radius)
        
        if providers:
            print_summary(providers, county_name)
            save_results(providers, county_name)
        else:
            print(f"\nNo providers found for {county_name} County.")
            print("You may want to try a larger search radius.")
        
        # Ask if user wants to continue
        continue_choice = input("\nExtract another county? (y/n): ").strip().lower()
        if continue_choice != 'y':
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    main()

