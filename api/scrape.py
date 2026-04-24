"""
api/scrape.py — Vercel Python Serverless Function
Handles POST /api/scrape requests from the web frontend.
Imports scraper + sheets logic from the project root.
"""

import json
import sys
import os

# Allow importing scraper.py / sheets.py / config.py from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests as http_requests
from scraper import scrape_by_barcode, set_delivery_location
from sheets import save_to_sheet
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):

    # ── CORS preflight ────────────────────────────────────────────────────────
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    # ── Main POST handler ─────────────────────────────────────────────────────
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
        except Exception:
            self._respond(400, {"success": False, "error": "Invalid JSON body."})
            return

        barcode = (data.get("barcode") or "").strip()
        postal_code = (data.get("postal_code") or "").strip()

        if not barcode:
            self._respond(400, {"success": False, "error": "Barcode is required."})
            return

        # Fresh session per request
        session = http_requests.Session()

        # Set delivery location (fast mode — skip homepage visit)
        if postal_code:
            set_delivery_location(session, postal_code)

        # Scrape Amazon
        product = scrape_by_barcode(barcode, session)

        if product is None:
            self._respond(404, {
                "success": False,
                "error": (
                    f"No product found for barcode '{barcode}'. "
                    "It may not be listed on Amazon.com, or try again in a moment."
                ),
            })
            return

        # Save to Google Sheet
        saved = save_to_sheet(product, postal_code=postal_code)

        self._respond(200, {
            "success": True,
            "saved_to_sheet": saved,
            "product": {
                "barcode":     product["barcode"],
                "asin":        product["asin"],
                "name":        product["name"],
                "price":       product["price"],
                "currency":    product["currency"],
                "url":         product["url"],
                "postal_code": postal_code,
            },
        })

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _respond(self, status: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # Silence default request logs
