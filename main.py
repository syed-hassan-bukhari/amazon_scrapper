"""
main.py — Amazon Barcode Price Scraper
Entry point. Run from the terminal:

    python main.py                        # interactive mode
    python main.py --zip 10001            # set ZIP, then enter barcodes interactively
    python main.py --zip 10001 840440401650              # one barcode
    python main.py --zip 10001 840440401650 012345678905 # multiple barcodes
"""

import sys
import time
import argparse
import requests
from scraper import scrape_by_barcode, set_delivery_location
from sheets import save_to_sheet

# Fix Unicode output on Windows terminals
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BANNER = """
+----------------------------------------------------+
|    Amazon Barcode -> Price -> Google Sheets        |
|         Free  |  No API Key  |  Python            |
+----------------------------------------------------+
"""


def get_postal_code(cli_zip: str = None) -> str:
    """Prompt the user for a postal/ZIP code if not provided via CLI."""
    if cli_zip:
        return cli_zip.strip()

    print("\n  Enter the delivery postal/ZIP code.")
    print("  This tells Amazon which location's prices to show.")
    print("  Examples:  10001  (New York)  |  90210  (Beverly Hills)  |  75001 (Paris)")
    print("  Press Enter to skip (uses your IP-based location).\n")

    code = input("  Postal / ZIP code: ").strip()
    return code


def process_barcode(barcode: str, session: requests.Session, postal_code: str) -> bool:
    """Scrape Amazon for the barcode and save the result to Google Sheets."""
    barcode = barcode.strip()
    if not barcode:
        return False

    print(f"\n{'='*54}")
    print(f"  Barcode: {barcode}")
    print(f"{'='*54}")

    # 1. Scrape Amazon (session already has location set)
    product = scrape_by_barcode(barcode, session)

    if product is None:
        print(f"  [X]  Could not retrieve product for barcode: {barcode}")
        return False

    # 2. Print summary
    location_label = f" (location: {postal_code})" if postal_code else ""
    print(f"\n  {'Product':<12}: {product['name'][:60]}")
    print(f"  {'ASIN':<12}: {product['asin']}")
    print(f"  {'Price':<12}: {product['currency']}{product['price']}{location_label}")
    print(f"  {'URL':<12}: {product['url']}")

    # 3. Save to Google Sheet (including postal code)
    success = save_to_sheet(product, postal_code=postal_code)
    if success:
        print(f"\n  [OK]  Saved to Google Sheet!")
    else:
        print(f"\n  [!!]  Failed to save to Google Sheet. Check README.md for setup.")

    return success


def main():
    print(BANNER)

    # ── Parse CLI arguments ────────────────────────────────────────────────────
    parser = argparse.ArgumentParser(
        description="Amazon Barcode -> Price -> Google Sheets",
        add_help=True,
    )
    parser.add_argument(
        "--zip", "--postal",
        dest="zip_code",
        metavar="POSTAL_CODE",
        help="Delivery postal/ZIP code (e.g. 10001 for New York)",
        default=None,
    )
    parser.add_argument(
        "barcodes",
        nargs="*",
        help="One or more barcodes to look up",
    )
    args = parser.parse_args()

    # ── Step 1: Get postal code ────────────────────────────────────────────────
    postal_code = get_postal_code(args.zip_code)

    # ── Step 2: Create shared session & set location ───────────────────────────
    session = requests.Session()

    if postal_code:
        print(f"\n  Setting Amazon delivery location to: {postal_code} ...")
        ok = set_delivery_location(session, postal_code)
        if ok:
            print(f"  Location set! Prices will reflect postal code: {postal_code}")
        else:
            print(f"  [WARN] Could not set location — prices may reflect your IP location.")
    else:
        print("  No postal code entered — using your IP-based location.")

    # ── Step 3: Get barcodes ───────────────────────────────────────────────────
    barcodes = args.barcodes

    if not barcodes:
        print("\n  Enter barcode(s) — press Enter after each one.")
        print("  Type 'done' and press Enter when finished.\n")
        while True:
            raw = input("  Barcode: ").strip()
            if raw.lower() in ("done", "exit", "quit", ""):
                break
            barcodes.append(raw)

    if not barcodes:
        print("No barcodes provided. Exiting.")
        return

    # ── Step 4: Process each barcode ──────────────────────────────────────────
    results = {"success": 0, "failed": 0}

    for i, barcode in enumerate(barcodes):
        ok = process_barcode(barcode, session, postal_code)
        if ok:
            results["success"] += 1
        else:
            results["failed"] += 1

        if i < len(barcodes) - 1:
            time.sleep(2)

    print(f"\n{'='*54}")
    print(f"  Done! Saved: {results['success']}  |  Failed: {results['failed']}")
    print(f"{'='*54}\n")


if __name__ == "__main__":
    main()
