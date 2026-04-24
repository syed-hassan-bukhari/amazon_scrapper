import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, send_from_directory
import requests as http_requests
from scraper import scrape_by_barcode, set_delivery_location
from sheets import save_to_sheet

app = Flask(__name__)

@app.route("/")
def index():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return send_from_directory(root_dir, "index.html")

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
