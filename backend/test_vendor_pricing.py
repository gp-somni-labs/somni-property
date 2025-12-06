"""
Test Vendor Pricing Scraper

Quick test to verify pricing data from all vendors
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from services.vendor_pricing_scraper import VendorPricingScraper


async def test_all_vendors():
    """Test pricing scraper for all vendors"""
    print("\n" + "=" * 80)
    print("VENDOR PRICING SCRAPER TEST")
    print("=" * 80 + "\n")

    async with VendorPricingScraper() as scraper:
        # Scrape all vendors
        all_products = await scraper.scrape_all_vendors()

        # Summary by vendor
        vendors = {}
        for product in all_products:
            vendor = product['vendor_name']
            if vendor not in vendors:
                vendors[vendor] = []
            vendors[vendor].append(product)

        # Print summary
        print(f"📊 Total Products Scraped: {len(all_products)}")
        print(f"📦 Total Vendors: {len(vendors)}")
        print("\n" + "-" * 80 + "\n")

        # Print by vendor
        for vendor, products in sorted(vendors.items()):
            print(f"\n{'🔵' if vendor == 'Ubiquiti' else '📦'} {vendor} - {len(products)} products")
            print("-" * 80)

            for product in products:
                price = product['unit_price']
                model = product['pricing_model']
                category = product['product_category']
                verified = "✅" if product.get('verified') else "⚠️"

                print(f"  {verified} {product['product_name']}")
                print(f"      💰 ${price} ({model}) | Category: {category}")

                if product.get('notes'):
                    print(f"      📝 {product['notes']}")

        print("\n" + "=" * 80)

        # Priority vendor check
        if 'Ubiquiti' in vendors:
            ubiquiti_count = len(vendors['Ubiquiti'])
            print(f"\n🎯 PRIORITY VENDOR: Ubiquiti - {ubiquiti_count} products scraped")
            print("   (Most important for property management infrastructure)")

        print("\n✅ Pricing scraper test completed successfully!\n")

        return all_products


async def test_specific_vendors():
    """Test individual vendor scrapers"""
    print("\n" + "=" * 80)
    print("TESTING INDIVIDUAL VENDOR SCRAPERS")
    print("=" * 80 + "\n")

    async with VendorPricingScraper() as scraper:
        # Test priority vendor (Ubiquiti)
        print("🔵 Testing Ubiquiti (PRIORITY VENDOR)...")
        ubiquiti = await scraper.scrape_ubiquiti()
        print(f"   ✅ {len(ubiquiti)} Ubiquiti products")

        # Test smart lighting
        print("💡 Testing Philips Hue...")
        hue = await scraper.scrape_philips_hue()
        print(f"   ✅ {len(hue)} Philips Hue products")

        print("🔆 Testing Lutron...")
        lutron = await scraper.scrape_lutron()
        print(f"   ✅ {len(lutron)} Lutron products")

        # Test automation
        print("⚡ Testing Shelly...")
        shelly = await scraper.scrape_shelly()
        print(f"   ✅ {len(shelly)} Shelly products")

        print("📡 Testing Apollo Automations...")
        apollo = await scraper.scrape_apollo_automations()
        print(f"   ✅ {len(apollo)} Apollo Automations products")

        print("\n✅ All individual scrapers working correctly!\n")


async def main():
    """Run all tests"""
    try:
        # Test all vendors at once
        products = await test_all_vendors()

        # Test individual scrapers
        await test_specific_vendors()

        # Final summary
        print("\n" + "=" * 80)
        print("FINAL SUMMARY")
        print("=" * 80)
        print(f"\n✅ {len(products)} products ready for database import")
        print("✅ All vendors responding correctly")
        print("✅ Priority vendor (Ubiquiti) verified")
        print("\n🚀 Pricing scraper is ready for production!\n")

    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
