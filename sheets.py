"""
sheets.py — Google Sheets Writer (via Apps Script Web App)
Sends product data to a Google Apps Script Web App via HTTP POST.
NO credentials file, NO API key — completely free.
"""

import logging
import json
import requests
from datetime import datetime
from config import APPS_SCRIPT_URL

logger = logging.getLogger(__name__)


def save_to_sheet(product: dict, postal_code: str = "") -> bool:
    """
    Send product data to the Google Apps Script Web App,
    which appends it as a new row in the Google Sheet.

    Expected keys in `product`:
        barcode, asin, name, price, currency, url
    """
    if not APPS_SCRIPT_URL or APPS_SCRIPT_URL == "YOUR_APPS_SCRIPT_WEB_APP_URL_HERE":
        logger.error(
            "[ERROR] Apps Script URL not configured!\n"
            "   Please follow the 2-minute setup in README.md and paste\n"
            "   your Web App URL into config.py -> APPS_SCRIPT_URL"
        )
        return False

    payload = {
        "barcode":     product.get("barcode", ""),
        "asin":        product.get("asin", ""),
        "name":        product.get("name", ""),
        "price":       product.get("price", ""),
        "currency":    product.get("currency", ""),
        "postal_code": postal_code,
        "url":         product.get("url", ""),
        "date":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        response = requests.post(
            APPS_SCRIPT_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=15,
            allow_redirects=True,
        )
        result = response.json()

        if result.get("status") == "success":
            logger.info("[OK] Row appended to Google Sheet successfully.")
            return True
        else:
            logger.error(f"[ERROR] Apps Script returned error: {result.get('message', 'Unknown error')}")
            return False

    except requests.exceptions.Timeout:
        logger.error("[ERROR] Request to Apps Script timed out.")
        return False
    except requests.exceptions.RequestException as exc:
        logger.error(f"[ERROR] Network error sending data to Google Sheet: {exc}")
        return False
    except Exception as exc:
        logger.error(f"[ERROR] Unexpected error: {exc}")
        return False
