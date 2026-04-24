"""
app.py — Local Flask development server
Serves the frontend from /public and exposes /api/scrape.
Run with: python app.py
"""

import os
from flask import Flask, request, jsonify, send_from_directory
import requests as http_requests
from scraper import scrape_by_barcode, set_delivery_location
from sheets import save_to_sheet

# Serve static files from the /public folder
app = Flask(__name__, static_folder="public", static_url_path="")


@app.route("/")
def index():
    return send_from_directory("public", "index.html")


@app.route("/api/scrape", methods=["POST"])
def scrape():
    data = request.get_json(force=True)
    barcode     = (data.get("barcode")     or "").strip()
    postal_code = (data.get("postal_code") or "").strip()

    if not barcode:
        return jsonify({"success": False, "error": "Barcode is required."}), 400

    session = http_requests.Session()

    if postal_code:
        set_delivery_location(session, postal_code)

    product = scrape_by_barcode(barcode, session)

    if product is None:
        return jsonify({
            "success": False,
            "error": (
                f"No product found for barcode '{barcode}'. "
                "It may not be listed on Amazon.com, or try again in a moment."
            ),
        }), 404

    saved = save_to_sheet(product, postal_code=postal_code)

    return jsonify({
        "success":        True,
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  Amazon Price Scanner running at http://localhost:{port}\n")
    app.run(debug=True, host="0.0.0.0", port=port)
