#!/usr/bin/env python3
"""
Batch extract VFC providers for all California counties.
Automatically creates JSON_Counties folder and saves one JSON file per county.
"""
import os
import json
import sys
from pathlib import Path
from typing import Dict, List

# Import functions from vfc_cli
from vfc_cli import (
    CALIFORNIA_COUNTIES,
    extract_county_providers,
    fetch_providers
)

def create_output_folder(folder_name: str = "JSON_Counties") -> Path:
    """Create the output folder if it doesn't exist."""
    folder_path = Path(folder_name)
    folder_path.mkdir(exist_ok=True)
    return folder_path

def save_county_json(providers: List[Dict], county_name: str, output_folder: Path):
    """Save providers to a JSON file in the output folder."""
    # Sanitize filename
    filename = county_name.replace(' ', '_').lower() + '.json'
    filepath = output_folder / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(providers, f, indent=2, ensure_ascii=False)
    
    return filepath

def extract_all_counties(radius: int = 200, output_folder: str = "JSON_Counties"):
    """Extract providers for all California counties and save to JSON files."""
    
    print("=" * 80)
    print("VFC Provider Batch Extractor - All California Counties")
    print("=" * 80)
    print(f"\nOutput folder: {output_folder}")
    print(f"Search radius: {radius} miles")
    print(f"Total counties: {len(CALIFORNIA_COUNTIES)}")
    print("\nStarting extraction...\n")
    
    # Create output folder
    output_path = create_output_folder(output_folder)
    print(f"✓ Created/verified output folder: {output_path.absolute()}\n")
    
    # Get sorted list of counties
    counties = sorted(CALIFORNIA_COUNTIES.keys())
    
    # Statistics
    total_providers = 0
    successful_counties = 0
    failed_counties = []
    results_summary = []
    
    # Process each county
    for i, county_name in enumerate(counties, 1):
        print(f"[{i}/{len(counties)}] Processing {county_name} County...")
        print("-" * 80)
        
        try:
            # Extract providers for this county
            providers = extract_county_providers(county_name, radius=radius)
            
            if providers:
                # Save to JSON
                filepath = save_county_json(providers, county_name, output_path)
                
                # Count by type
                types = {}
                for provider in providers:
                    ptype = provider.get('type', 'Unknown')
                    types[ptype] = types.get(ptype, 0) + 1
                
                print(f"✓ Saved {len(providers)} providers to {filepath.name}")
                print(f"  Provider types: {dict(types)}")
                
                total_providers += len(providers)
                successful_counties += 1
                results_summary.append({
                    'county': county_name,
                    'providers': len(providers),
                    'types': types,
                    'file': filepath.name
                })
            else:
                print(f"⚠ No providers found for {county_name} County")
                # Still create an empty JSON file
                filepath = save_county_json([], county_name, output_path)
                results_summary.append({
                    'county': county_name,
                    'providers': 0,
                    'types': {},
                    'file': filepath.name
                })
                failed_counties.append(county_name)
        
        except KeyboardInterrupt:
            print("\n\n⚠ Extraction interrupted by user")
            print(f"Completed {i-1}/{len(counties)} counties")
            sys.exit(1)
        
        except Exception as e:
            print(f"✗ Error processing {county_name}: {e}")
            failed_counties.append(county_name)
            # Create empty JSON file for failed county
            try:
                filepath = save_county_json([], county_name, output_path)
            except:
                pass
        
        print()  # Blank line between counties
    
    # Print summary
    print("=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  Total counties processed: {len(counties)}")
    print(f"  Successful: {successful_counties}")
    print(f"  Failed/No data: {len(failed_counties)}")
    print(f"  Total providers found: {total_providers:,}")
    print(f"\nOutput folder: {output_path.absolute()}")
    
    if failed_counties:
        print(f"\nCounties with no providers:")
        for county in failed_counties:
            print(f"  - {county}")
    
    # Save summary JSON
    summary_file = output_path / "_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_counties': len(counties),
            'successful_counties': successful_counties,
            'failed_counties': len(failed_counties),
            'total_providers': total_providers,
            'search_radius': radius,
            'results': results_summary
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Summary saved to {summary_file.name}")
    
    # Print top counties by provider count
    top_counties = sorted([r for r in results_summary if r['providers'] > 0], 
                         key=lambda x: x['providers'], reverse=True)[:10]
    
    if top_counties:
        print(f"\nTop 10 counties by provider count:")
        for i, result in enumerate(top_counties, 1):
            print(f"  {i:2d}. {result['county']:25s} - {result['providers']:3d} providers")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Batch extract VFC providers for all California counties',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python batch_extract_all_counties.py
  python batch_extract_all_counties.py --radius 300
  python batch_extract_all_counties.py --radius 200 --output my_counties
        """
    )
    
    parser.add_argument(
        '--radius',
        type=int,
        default=200,
        help='Search radius in miles (default: 200)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='JSON_Counties',
        help='Output folder name (default: JSON_Counties)'
    )
    
    args = parser.parse_args()
    
    # Confirm before starting
    print(f"\nThis will extract providers for all {len(CALIFORNIA_COUNTIES)} California counties.")
    print(f"Output folder: {args.output}")
    print(f"Search radius: {args.radius} miles")
    print("\nThis may take a while. Proceed? (y/n): ", end='')
    
    try:
        response = input().strip().lower()
        if response != 'y':
            print("Cancelled.")
            return
    except KeyboardInterrupt:
        print("\nCancelled.")
        return
    
    # Run extraction
    extract_all_counties(radius=args.radius, output_folder=args.output)

if __name__ == "__main__":
    main()

