"""
scraper.py — Amazon Price Scraper
Looks up a product by barcode on Amazon, extracts ASIN, name, and price.
Supports setting delivery location via postal/ZIP code before searching.
Uses requests + BeautifulSoup (no paid API required).
"""

import time
import random
import re
import logging
import requests
from bs4 import BeautifulSoup
from config import AMAZON_BASE_URL, REQUEST_DELAY, MAX_RETRIES

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Realistic browser-like User-Agent pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]


def _get_headers(extra: dict = None) -> dict:
    """Return randomised browser-like headers, with optional extra headers."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }
    if extra:
        headers.update(extra)
    return headers


def _fetch(url: str, session: requests.Session) -> BeautifulSoup | None:
    """Fetch a URL with retries and return a BeautifulSoup object."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"  Fetching (attempt {attempt}): {url}")
            resp = session.get(url, headers=_get_headers(), timeout=15)
            resp.raise_for_status()

            # Detect CAPTCHA / bot-check page
            if "captcha" in resp.url.lower() or "robot" in resp.text.lower()[:500]:
                logger.warning("  [WARN] Amazon returned a CAPTCHA/bot-check page.")
                if attempt < MAX_RETRIES:
                    wait = REQUEST_DELAY * attempt * 2
                    logger.info(f"  Waiting {wait}s before retry...")
                    time.sleep(wait)
                    continue
                return None

            return BeautifulSoup(resp.text, "html.parser")

        except requests.RequestException as exc:
            logger.warning(f"  Request error on attempt {attempt}: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(REQUEST_DELAY * attempt)

    return None


# ── Delivery Location ──────────────────────────────────────────────────────────

def set_delivery_location(session: requests.Session, postal_code: str) -> bool:
    """
    Set the Amazon delivery location to the given postal/ZIP code.
    This ensures search results and prices reflect the correct region.

    Returns True if location was set successfully, False otherwise.
    """
    logger.info(f"[LOCATION] Setting delivery location to: {postal_code}")

    # Step 1 — Visit homepage to initialise session cookies
    try:
        home_resp = session.get(
            AMAZON_BASE_URL,
            headers=_get_headers(),
            timeout=15,
        )
        home_resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning(f"  [WARN] Could not load Amazon homepage: {exc}")
        return False

    # Step 2 — Extract the CSRF token Amazon embeds in the page
    home_soup = BeautifulSoup(home_resp.text, "html.parser")
    csrf_token = ""
    csrf_input = home_soup.find("input", {"name": "anti-csrftoken-a2z"})
    if csrf_input:
        csrf_token = csrf_input.get("value", "")
    else:
        # Try to find it in a script tag
        scripts = home_soup.find_all("script")
        for script in scripts:
            m = re.search(r'"csrfToken"\s*:\s*"([^"]+)"', script.get_text())
            if m:
                csrf_token = m.group(1)
                break

    time.sleep(1 + random.uniform(0.2, 0.8))

    # Step 3 — POST the postal code to Amazon's location-change endpoint
    location_url = f"{AMAZON_BASE_URL}/gp/delivery/ajax/address-change.html"
    payload = {
        "locationType":  "LOCATION_INPUT",
        "zipCode":       postal_code,
        "storeContext":  "generic",
        "deviceType":    "web",
        "pageType":      "Gateway",
        "actionSource":  "gw",
    }
    post_headers = _get_headers({
        "x-requested-with": "XMLHttpRequest",
        "Referer":          AMAZON_BASE_URL,
        "Origin":           AMAZON_BASE_URL,
        "Content-Type":     "application/x-www-form-urlencoded",
    })
    if csrf_token:
        post_headers["anti-csrftoken-a2z"] = csrf_token

    try:
        loc_resp = session.post(
            location_url,
            data=payload,
            headers=post_headers,
            timeout=15,
        )
        if loc_resp.status_code in (200, 302):
            logger.info(f"[LOCATION] Location set to postal code: {postal_code}")
            return True
        else:
            logger.warning(
                f"  [WARN] Location endpoint returned status {loc_resp.status_code}. "
                "Continuing anyway — prices may reflect your IP location."
            )
            return False
    except requests.RequestException as exc:
        logger.warning(f"  [WARN] Could not set location: {exc}. Continuing anyway.")
        return False


# ── Price extraction helpers ───────────────────────────────────────────────────

def _extract_price(soup: BeautifulSoup) -> tuple[str, str]:
    """
    Return (price_string, currency_symbol) from a product page soup.
    Tries several selectors Amazon has used over the years.
    """
    # Strategy 1 - aria-hidden offscreen price (most reliable in 2024)
    for el in soup.select("span.a-price span.a-offscreen"):
        text = el.get_text(strip=True)
        if text:
            currency, amount = _split_currency(text)
            return amount, currency

    # Strategy 2 - priceblock_ourprice / dealprice (older pages)
    for selector in ("#priceblock_ourprice", "#priceblock_dealprice", "#price_inside_buybox"):
        el = soup.select_one(selector)
        if el:
            text = el.get_text(strip=True)
            currency, amount = _split_currency(text)
            return amount, currency

    # Strategy 3 - whole + fraction
    whole = soup.select_one("span.a-price-whole")
    frac = soup.select_one("span.a-price-fraction")
    symbol = soup.select_one("span.a-price-symbol")
    if whole:
        price_str = whole.get_text(strip=True).replace(",", "").rstrip(".")
        if frac:
            price_str += f".{frac.get_text(strip=True)}"
        currency = symbol.get_text(strip=True) if symbol else "$"
        return price_str, currency

    return "N/A", "N/A"


def _split_currency(text: str) -> tuple[str, str]:
    """Split '$12.99' into ('$', '12.99')."""
    match = re.match(r"^([^\d]+)([\d,]+\.?\d*)$", text.strip())
    if match:
        return match.group(1).strip(), match.group(2).replace(",", "")
    return "", text.strip()


def _asin_from_url(url: str) -> str | None:
    """Extract ASIN from a /dp/XXXXXXXXXX style URL."""
    match = re.search(r"/dp/([A-Z0-9]{10})", url)
    return match.group(1) if match else None


def _normalize_barcodes(barcode: str) -> list[str]:
    """
    Return barcode variants to try:
    - Original as-is
    - Zero-padded to 12 digits (UPC-A standard)
    - Zero-padded to 13 digits (EAN-13 standard)
    """
    variants = [barcode]
    barcode_clean = barcode.strip()

    if len(barcode_clean) < 12:
        padded_12 = barcode_clean.zfill(12)
        if padded_12 not in variants:
            variants.append(padded_12)

    if len(barcode_clean) < 13:
        padded_13 = barcode_clean.zfill(13)
        if padded_13 not in variants:
            variants.append(padded_13)

    return variants


def _find_product_card(soup: BeautifulSoup):
    """
    Try multiple strategies to find the first product card with an ASIN
    in Amazon search results.
    """
    # Strategy 1 - Standard search result component (most common)
    card = soup.select_one("div[data-asin][data-component-type='s-search-result']")
    if card and card.get("data-asin"):
        return card

    # Strategy 2 - Any div with a valid 10-char ASIN
    for tag in soup.find_all("div", attrs={"data-asin": True}):
        asin = tag.get("data-asin", "")
        if len(asin) == 10:
            return tag

    # Strategy 3 - Any element with a valid ASIN attribute
    card = soup.find(attrs={"data-asin": re.compile(r"^[A-Z0-9]{10}$")})
    if card:
        return card

    # Strategy 4 - Extract ASIN directly from product link href
    for a_tag in soup.select("a[href*='/dp/']"):
        asin = _asin_from_url(a_tag.get("href", ""))
        if asin:
            a_tag["data-asin"] = asin
            return a_tag

    return None


# ── Main public function ───────────────────────────────────────────────────────

def scrape_by_barcode(barcode: str, session: requests.Session) -> dict | None:
    """
    Given a barcode (UPC / EAN / ISBN) and an active requests Session
    (optionally pre-configured with a delivery location), search Amazon,
    extract the first product's ASIN, name, and price.

    Returns a dict with keys: barcode, asin, name, price, currency, url
    or None if the product could not be found/scraped.
    """
    barcode_variants = _normalize_barcodes(barcode)
    product_card = None

    for variant in barcode_variants:
        search_urls = [
            f"{AMAZON_BASE_URL}/s?k={variant}&ref=nb_sb_noss",
            f"{AMAZON_BASE_URL}/s?field-keywords={variant}",
        ]

        for search_url in search_urls:
            logger.info(f"\n[SEARCH] Trying: {search_url}")
            soup = _fetch(search_url, session)
            if soup is None:
                continue

            card = _find_product_card(soup)
            if card:
                product_card = card
                logger.info(f"[MATCH] Found result using barcode variant: {variant}")
                break

        if product_card:
            break

        if variant != barcode_variants[-1]:
            time.sleep(REQUEST_DELAY)

    if not product_card:
        tried = barcode_variants[1:] if len(barcode_variants) > 1 else []
        extra = f" (also tried zero-padded: {tried})" if tried else ""
        logger.error(
            f"No products found for barcode '{barcode}'{extra}.\n"
            "  This barcode may not exist on Amazon.com, or Amazon blocked the request."
        )
        return None

    asin = product_card.get("data-asin")
    logger.info(f"[FOUND] ASIN: {asin}")

    product_url = f"{AMAZON_BASE_URL}/dp/{asin}"

    time.sleep(REQUEST_DELAY + random.uniform(0.3, 1.0))

    logger.info(f"[PRODUCT] Loading product page: {product_url}")
    product_soup = _fetch(product_url, session)
    if product_soup is None:
        logger.error("Failed to load product page.")
        return None

    title_el = product_soup.select_one("#productTitle")
    name = title_el.get_text(strip=True) if title_el else "Unknown"

    price, currency = _extract_price(product_soup)

    logger.info(f"Name    : {name[:80]}")
    logger.info(f"Price   : {currency}{price}")

    return {
        "barcode":  barcode,
        "asin":     asin,
        "name":     name,
        "price":    price,
        "currency": currency,
        "url":      product_url,
    }
